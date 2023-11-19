import django, base64, secrets, re, asyncio, json
from django.db.models import Sum, IntegerField, Count, F, Q
from django.db.models.functions import Round
from time import time
from bech32 import bech32_decode, bech32_encode, convertbits
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from decimal import Decimal
from lndg import settings
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import signer_pb2 as lns
from gui.lnd_deps import signer_pb2_grpc as lnsigner
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps.lnd_connect import lnd_connect, async_lnd_connect
from os import environ
environ['DJANGO_SETTINGS_MODULE'] = 'lndg.settings'
django.setup()
from gui.models import TradeSales, Payments, PaymentHops, Forwards, Peers

def is_hex(n):
    return len(n) % 2 == 0 and all(c in '0123456789ABCDEFabcdef' for c in n)

def hex_as_utf8(hex_str):
    return bytes.fromhex(hex_str).decode('utf-8')

def utf8_as_hex(utf8_str):
    return bytes(utf8_str, 'utf-8').hex()

def decode_basic_trade(records):
    if not isinstance(records, list):
        raise ValueError('ExpectedArrayOfRecordsToDecodeBasicTrade')

    description_record = next((record for record in records if record['type'] == '2'), None)

    if not description_record:
        raise ValueError('ExpectedDescriptionRecordToDecodeBasicTrade')

    id_record = next((record for record in records if record['type'] == '1'), None)

    if not id_record:
        raise ValueError('ExpectedIdRecordToDecodeBasicTradeDetails')

    return {
        'description': hex_as_utf8(description_record['value']),
        'id': id_record['value']
    }

def encode_as_bigsize(number: int):
    max_8_bit_number = 252
    max_16_bit_number = 65535
    max_32_bit_number = 4294967295
    
    def tag_as_uint8(n):
        return format(n, '02x')
    
    def tag_as_uint16(n):
        return 'fd' + format(n, '04x')
    
    def tag_as_uint32(n):
        return 'fe' + format(n, '08x')
    
    def tag_as_uint64(n):
        return 'ff' + format(n, '016x')
   
    number = int(number) 
    
    if number <= max_8_bit_number:
        return tag_as_uint8(number)
    elif number <= max_16_bit_number:
        return tag_as_uint16(number)
    elif number <= max_32_bit_number:
        return tag_as_uint32(number)
    else:
        return tag_as_uint64(number)

def decode_as_bigsize(encoded_string: str):
    def read_uint8(encoded_string):
        return int(encoded_string[:2], 16), encoded_string[2:]

    def read_uint16(encoded_string):
        return int(encoded_string[2:6], 16), encoded_string[6:]

    def read_uint32(encoded_string):
        return int(encoded_string[2:10], 16), encoded_string[10:]

    def read_uint64(encoded_string):
        return int(encoded_string[2:18], 16), encoded_string[18:]

    if encoded_string.startswith('ff'):
        value, remaining = read_uint64(encoded_string)
    elif encoded_string.startswith('fe'):
        value, remaining = read_uint32(encoded_string)
    elif encoded_string.startswith('fd'):
        value, remaining = read_uint16(encoded_string)
    else:
        value, remaining = read_uint8(encoded_string)

    return value

def decode_big_size(encoded):
    max_8bit_number = 0xfc
    max_16bit_number = 0xffff
    max_32bit_number = 0xffffffff
    uint8_length = 1
    uint16 = 0xfd
    uint16_length = 3
    uint32 = 0xfe
    uint32_length = 5
    uint64_length = 9

    if not bool(encoded) and is_hex(encoded):
        raise ValueError('ExpectedHexEncodedBigSizeValueToDecode')

    bytes_data = bytes.fromhex(encoded)

    size = bytes_data[0]

    if size <= max_8bit_number:
        return {'decoded': str(size), 'length': uint8_length}

    byte_length = len(bytes_data)

    if size == uint16:
        if byte_length < uint16_length:
            raise ValueError('ExpectedMoreBytesToDecodeUint16BigSize')

        uint16_number = int.from_bytes(bytes_data[1:3], 'big')

        if uint16_number <= max_8bit_number:
            raise ValueError('ExpectedLargerNumberToDecodeUint16BigSize')

        return {'decoded': str(uint16_number), 'length': uint16_length}
    elif size == uint32:
        if byte_length < uint32_length:
            raise ValueError('ExpectedMoreBytesToDecodeUint32BigSize')

        uint32_number = int.from_bytes(bytes_data[1:5], 'big')

        if uint32_number <= max_16bit_number:
            raise ValueError('ExpectedLargerNumberToDecodeUint32BigSize')

        return {'decoded': str(uint32_number), 'length': uint32_length}
    else:
        if byte_length < uint64_length:
            raise ValueError('ExpectedMoreBytesToDecodeUint64BigSize')

        uint64_number = int.from_bytes(bytes_data[1:9], 'big')

        if uint64_number <= max_32bit_number:
            raise ValueError('ExpectedLargerNumberToDecodeUint64BigSize')

        return {'decoded': str(uint64_number), 'length': uint64_length}

def decode_tlv_record(data):
    def hex_len(byte_length):
        return 0 if not byte_length else byte_length * 2

    def read(from_pos, hex_str, to_pos=None):
        if to_pos is None:
            return hex_str[from_pos:]
        else:
            return hex_str[from_pos:to_pos + from_pos]
    encoded = data['encoded']
    offset = data.get('offset', 0)

    start = hex_len(offset)

    type_record = decode_big_size(read(start, encoded))

    size_start = start + hex_len(type_record['length'])

    bytes_record = decode_big_size(read(size_start, encoded))

    meta_bytes = type_record['length'] + bytes_record['length']

    if not int(bytes_record['decoded']):
        return {'length': meta_bytes, 'type': type_record['decoded'], 'value': ''}

    value_start = start + hex_len(meta_bytes)
    total_bytes = meta_bytes + int(bytes_record['decoded'])

    if start + hex_len(total_bytes) > len(encoded):
        raise ValueError('ExpectedAdditionalValueBytesInTlvRecord')

    return {
        'length': total_bytes,
        'type': type_record['decoded'],
        'value': read(value_start, encoded, hex_len(int(bytes_record['decoded'])))
    }

def decode_tlv_stream(encoded):

    if not is_hex(encoded):
        raise ValueError('ExpectedHexEncodedTlvStreamToDecode')

    if not encoded:
        return []

    total_bytes = len(encoded) // 2
    stream = {'offset': 0, 'records': []}

    while stream['offset'] < total_bytes:
        stream['record'] = decode_tlv_record({'encoded': encoded, 'offset': stream['offset']})

        stream['offset'] += stream['record']['length']
        stream['records'].append(stream['record'])

    return stream['records']

def parse_response_code(data):
    encoded = data['encoded']

    if not encoded:
        raise ValueError('ExpectedResponseCodeValueToParseResponseCode')

    records = decode_tlv_stream(encoded)
    code_record = next((record for record in records if record['type'] == '0'), None)

    if not code_record:
        raise ValueError('ExpectedCodeRecordToParseResponseCode')

    code = int(decode_big_size(code_record['value'])['decoded'])
    if code > 2 ** 53 - 1:
        raise ValueError('UnexpectedlyLargeResponseCodeInResponse')

    if code < 100:
        raise ValueError('UnexpectedlySmallResponseCodeInResponse')

    if not code > 400:
        return {}

    message_record = next((record for record in records if record['type'] == '1'), None) or {'value': ''}

    return {'failure': [code, hex_as_utf8(message_record['value'])]}

def parse_peer_request_message(message):
    records = decode_tlv_stream(message[len('626f73ff'):])
    version = next((record for record in records if record['type'] == '0'), None)

    if version is not None:
        raise ValueError('UnexpectedVersionNumberOfRequestMessage')

    id_record = next((record for record in records if record['type'] == '1'), None)

    if id_record is None or len(id_record['value']) != 64:
        raise ValueError('ExpectedRequestIdInRequestMessage')

    records_record = next((record for record in records if record['type'] == '5'), None) or {'value':''}

    response_code_record = next((record for record in records if record['type'] == '2'), None)
    type_record = next((record for record in records if record['type'] == '3'), None)

    if not type_record and not response_code_record:
        raise ValueError('ExpectedEitherRequestParametersOrResponseCode')

    if response_code_record is not None:
        response_code = parse_response_code({'encoded': response_code_record['value']})
        failure = response_code['failure'] if 'failure' in response_code else None

        return {
            'response': {
                'failure': failure,
                'id': id_record['value'],
                'records': [{'type': record['type'], 'value': record['value']} for record in decode_tlv_stream(records_record['value'])],
            },
        }
    else:
        return {
            'request': {
                'id': id_record['value'],
                'records': [{'type': record['type'], 'value': record['value']} for record in decode_tlv_stream(records_record['value'])],
                'type': decode_big_size(type_record['value'])['decoded'],
            },
        }

def decode_basic_trade(records):
    if not isinstance(records, list):
        raise ValueError('ExpectedArrayOfRecordsToDecodeBasicTrade')

    description_record = next((record for record in records if record['type'] == '2'), None)

    if not description_record:
        raise ValueError('ExpectedDescriptionRecordToDecodeBasicTrade')

    id_record = next((record for record in records if record['type'] == '1'), None)

    if not id_record:
        raise ValueError('ExpectedIdRecordToDecodeBasicTradeDetails')

    return {
        'description': hex_as_utf8(description_record['value']),
        'id': id_record['value']
    }

def decode_anchored_trade_data(encoded):
    anchor_prefix = 'anchor-trade-secret:'

    if not encoded.startswith(anchor_prefix):
        return {}

    encoded_data = encoded[len(anchor_prefix):]

    try:
        decoded_data = decode_tlv_stream(base64.b64decode(encoded_data).hex())
    except Exception as e:
        return {}

    records = decoded_data
    channel_record = next((record for record in records if record['type'] == '3'), None)
    description_record = next((record for record in records if record['type'] == '1'), None)
    secret_record = next((record for record in records if record['type'] == '0'), None)
    price_record = next((record for record in records if record['type'] == '2'), None)

    if channel_record:
        try:
            channel_value = int(decode_big_size({'encoded': channel_record['value']})['decoded'])
        except ValueError:
            return {}

        return {
            'channel': channel_value,
            'price': hex_as_utf8(price_record['value']) if price_record else None,
        }

    if description_record and secret_record:
        return {
            'description': hex_as_utf8(description_record['value']),
            'price': hex_as_utf8(price_record['value']) if price_record else None,
            'secret': hex_as_utf8(secret_record['value']),
        }
    return None

def encode_tlv_record(data):
    def byte_length_of(hex_string):
        return len(hex_string) // 2

    def encode(type, length, val):
        return f"{type}{length}{val}"

    type_number = data["type"]
    value_hex = data["value"]

    data_length = encode_as_bigsize(byte_length_of(value_hex))
    encoded_tlv_record = encode(encode_as_bigsize(type_number), data_length, value_hex)

    return encoded_tlv_record

def encode_peer_request(data):
    id = data['id']
    records = data.get('records')
    request_type = data['type']
    if not id:
        raise ValueError('ExpectedRequestIdHexStringToEncodePeerRequest')

    if records is not None and not isinstance(records, list):
        raise ValueError('ExpectedRecordsArrayToEncodePeerRequest')

    if not request_type:
        raise ValueError('ExpectedRequestTypeToEncodePeerRequest')

    peer_response = [{'type': '1', 'value': id},{'type': '3', 'value': encode_as_bigsize(request_type)},{'type': '5', 'value': records}]

    peer_response = [
        {'type': item['type'], 'value': item['value']} if not isinstance(item['value'], list) else {'type': item['type'], 'value': ''.join([encode_tlv_record(record) for record in item['value']])}
        for item in peer_response
    ]

    peer_response = [{'type': item['type'], 'value': str(item['value'])} for item in peer_response]

    return '626f73ff' + ''.join([encode_tlv_record(record) for record in peer_response])

def encode_response_code(data):
    code_for_success = 200
    failure = data.get('failure')

    if not failure:
        return ''.join([encode_tlv_record(record) for record in [{'type': '0', 'value': encode_as_bigsize(code_for_success)}]])

    if not isinstance(failure, list):
        raise ValueError('ExpectedFailureArrayToEncodeResponseCode')

    code, message = failure

    if not code:
        raise ValueError('ExpectedErrorCodeToEncodeResponseCode')

    records = [{'value': encode_as_bigsize(code), 'type': '0'}, {'value': utf8_as_hex(message), 'type': '1'}]

    return ''.join([encode_tlv_record(record) for record in records])

def encode_peer_response(data):
    failure = data.get('failure')
    id = data['id']
    records = data.get('records')

    code = encode_response_code({'failure': failure})
    encoded = ''.join([encode_tlv_record(record) for record in records]) if records is not None else None

    peer_response = [{'type': '1', 'value': id}, {'type': '2', 'value': code}, {'type': '5', 'value': encoded}]
    
    return '626f73ff' + ''.join([encode_tlv_record(record) for record in peer_response])

def get_legacy_trades(stub):
    trades = []
    for invoice in stub.ListInvoices(ln.ListInvoiceRequest(pending_only=True)).invoices:
        if invoice.is_keysend == False:
            trade = decode_anchored_trade_data(invoice.memo)
            if trade:
                trade['price'] = invoice.value
                trade['id'] = invoice.r_hash.hex()
                trade['expiry'] = invoice.expiry
                trade['creation_date'] = invoice.creation_date
                trades.append(trade)
    return trades

def get_trades(trade_id=None):
    trades = TradeSales.objects.filter(Q(expiry__isnull=True) | Q(expiry__gt=datetime.now())).filter(Q(sale_limit__isnull=True) | Q(sale_count__lt=F('sale_limit')))
    if trade_id:
        trades = trades.filter(id=trade_id)
    return trades

def decodePrefix(prefix):
    bech32CurrencyCodes={"bc": "bitcoin","bcrt": "regtest","ltc": "litecoin","tb": "testnet","tbs": "signet","sb": "simnet"}
    matches = re.compile(r'^ln(\S+?)(\d*)([a-zA-Z]?)$').match(prefix)

    if not matches or not matches.groups():
        raise ValueError('InvalidPaymentRequestPrefix')

    _, _, type = matches.groups()

    prefixElements = re.compile(r'^ln(\S+)$').match(prefix) if not type else matches

    currency, amount, units = prefixElements.groups()

    network = bech32CurrencyCodes.get(currency)

    if not network:
        raise ValueError('UnknownCurrencyCodeInPaymentRequest')

    return amount, network, units

def parseHumanReadableValue(data):
    amountMultiplierPattern = r'^[^munp0-9]$'
    divisibilityMarkerLen = 1
    divisibilityPattern = r'^[munp]$'

    amount = data.get('amount')
    units = data.get('units')

    hrp = f"{amount}{units}"

    if re.match(divisibilityPattern, hrp[-divisibilityMarkerLen:]):
        return {
            'divisor': hrp[-divisibilityMarkerLen:],
            'value': hrp[:-(divisibilityMarkerLen)],
        }

    if re.match(amountMultiplierPattern, hrp[-divisibilityMarkerLen:]):
        raise ValueError('InvalidAmountMultiplier')

    return {'value': hrp}

def hrpAsMtokens(amount, units):
    divisors ={"m": "1000","n": "1000000000","p": "1000000000000","u": "1000000"}

    if not amount:
        return {}

    result = parseHumanReadableValue({'amount': amount, 'units': units})
    divisor = result['divisor']
    value = result['value']

    if not bool(re.match(r'^\d+$', value)):
        raise ValueError('ExpectedValidNumericAmountToParseHrpAsMtokens')

    val = Decimal(value)

    if not divisor:
        return {'mtokens': str(int(val * Decimal(1e11)))}

    div = Decimal(divisors.get(divisor, 1))

    return str(int(val * Decimal(1e11) / div))

def mtokensAsHrp(mtokens):
    amount = int(mtokens)
    hrp = None

    multipliers = {
        'n': 100,
        'u': 100000,
        'm': 100000000,
        '': 100000000000,
    }

    for letter, value in multipliers.items():
        value = int(value)
        if amount % value == 0:
            if letter == 'u':
                hrp = f"{amount // value}u"
            elif letter == 'm':
                hrp = f"{amount // value}m"
            elif letter == 'n':
                hrp = f"{amount // value}n"
            elif letter == '':
                hrp = f"{amount // value}"

    if not hrp:
        return str(amount * 10) + 'p'
    return hrp

def decodeBech32Words(words):
    inBits = 5
    outBits = 8

    bits = 0
    maxV = (1 << outBits) - 1
    result = []
    value = 0

    for word in words:
        value = (value << inBits) | word
        bits += inBits
        while bits >= outBits:
            bits -= outBits
            result.append((value >> bits) & maxV)

    if bits:
        result.append((value << (outBits - bits)) & maxV)

    return bytes(result)

def byteEncodeRequest(request):
    if not request:
        raise ValueError('ExpectedPaymentRequestToByteEncode')

    if request[:2].lower() != 'ln':
        raise ValueError('ExpectedLnPrefixToByteEncodePaymentRequest')

    (prefix, words) = bech32_decode(request)

    (amount, network, units) = decodePrefix(prefix)

    mtokens = hrpAsMtokens(amount, units)

    encoded = decodeBech32Words(words).hex()

    return {'encoded': encoded, 'network': network, 'mtokens': mtokens, 'words': len(words)}

def byteDecodeRequest(encoded, mtokens, network, words):
    if not is_hex(encoded):
        raise ValueError('ExpectedHexEncodedPaymentRequestDataToDecodeRequest')
    if not network:
        raise ValueError('ExpectedNetworkToDecodeByteEncodedRequest')
    if not words:
        raise ValueError('ExpectedWordsCountToDecodeByteEncodedRequest')

    if network == 'bitcoin':
        prefix = 'bc'
    elif network == 'testnet':
        prefix = 'tb'
    elif network == 'regtest':
        prefix = 'bcrt'
    elif network == 'signet':
        prefix = 'tbs'
    else:
        raise ValueError('ExpectedKnownNetworkToDecodeByteEncodedRequest')

    prefix = 'ln' + prefix + mtokensAsHrp(mtokens)
    five_bit = convertbits(bytes.fromhex(encoded), 8, 5)[:words]      
    return bech32_encode(prefix, five_bit)

def encode_request_as_records(request):
    if not request:
        raise ValueError('ExpectedRequestToEncodeAsRequestRecords')

    records = []

    result = byteEncodeRequest(request)
    encoded = result['encoded']
    mtokens = result['mtokens']
    words = result['words']

    records.append({'type': '1', 'value': encoded})
    records.append({'type': '0', 'value': encode_as_bigsize(words)})

    if mtokens:
        records.append({'type': '2', 'value': encode_as_bigsize(mtokens)})

    return ''.join([encode_tlv_record(record) for record in records]), result['network']

def decode_records_as_request(encoded, network):
    if not encoded:
        raise ValueError('ExpectectedEncodedPaymentRequestRecordsToDecode')
    
    if not network:
        raise ValueError('ExpectedNetworkNameToDeriveRequestFromRequestRecords')

    records = decode_tlv_stream(encoded)
    word_count = next((record for record in records if record['type'] == '0'), None)
    if not word_count:
        raise ValueError('ExpectedWordCountRecordInPaymentTlvRecord')
    try:
        words = int(decode_as_bigsize(word_count['value']))
    except:
        raise ValueError('ExpectedPaymentRequestWordCountInRequestRecords')
    
    details = next((record for record in records if record['type'] == '1'), None)
    if not details:
        raise ValueError('ExpectedEncodedPaymentDetailsInPaymentTlvRecord')
    
    amount = next((record for record in records if record['type'] == '2'), None)
    if not amount:
        raise ValueError('ExpectedPaymentRequestTokensInPaymentRecords')
    mtokens = decode_as_bigsize(amount['value'])

    try:
        request = byteDecodeRequest(details['value'], mtokens, network, words)
    except:
        raise ValueError('ExpectedValidPaymentRequestDetailsToDecodeRecords')
    
    return request

def encode_final_trade(auth, payload, request):
    if not request:
        raise ValueError('ExpectedPaymentRequestToDeriveNetworkRecord')
    
    encoded_request, network = encode_request_as_records(request)
    trade_records = [{'type': '2', 'value': encoded_request}]

    if settings.LND_NETWORK != 'mainnet':
        network_value = '02' if network == 'regtest' else '01'
        trade_records.append({'type': '1','value': network_value})

    encryption_records = ''.join([encode_tlv_record(record) for record in [{'type': '0', 'value': payload}, {'type': '1', 'value': auth}]])
    details_records = ''.join([encode_tlv_record(record) for record in [{'type': '0', 'value': encryption_records}]])
    trade_records.append({'type': '3', 'value': details_records})

    return '626f73ff' + ''.join([encode_tlv_record(record) for record in trade_records])

def decode_final_trade(network, request, details):
    details = decode_tlv_stream(details['value'])

    encrypted = next((record for record in details if record['type'] == '0'), None)
    if not encrypted:
        raise ValueError('ExpectedEncryptedRecordToDecodeTrade')
    encrypted_records = decode_tlv_stream(encrypted['value'])

    encrypted_data = next((record for record in encrypted_records if record['type'] == '0'), None)
    if not encrypted_data:
        raise ValueError('ExpectedEncryptedDataRecordToDecodeTrade')
    
    auth = next((record for record in encrypted_records if record['type'] == '1'), None)
    if not auth:
        raise ValueError('ExpectedAuthDataRecordToDecodeTrade')

    return decode_records_as_request(request['value'], network), auth['value'], encrypted_data['value']

def getSecret(stub, sale_type):
    if sale_type == 1: # routing data
        try:
            filter_30day = datetime.now() - timedelta(days=30)
            incoming_nodes = Forwards.objects.filter(forward_date__gte=filter_30day).values('chan_id_in').annotate(ppm=Round((Sum('fee')/Sum('amt_in_msat'))*1000000000, output_field=IntegerField()), score=Round((Round(Count('id')/1, output_field=IntegerField())+Round(Sum('amt_in_msat')/100000, output_field=IntegerField()))/10, output_field=IntegerField())).exclude(score=0).order_by('-score', '-ppm')[:5]
            outgoing_nodes = Forwards.objects.filter(forward_date__gte=filter_30day).values('chan_id_out').annotate(ppm=Round((Sum('fee')/Sum('amt_out_msat'))*1000000000, output_field=IntegerField()), score=Round((Round(Count('id')/1, output_field=IntegerField())+Round(Sum('amt_out_msat')/100000, output_field=IntegerField()))/10, output_field=IntegerField())).exclude(score=0).order_by('-score', '-ppm')[:5]
            secret = json.dumps({"incoming_nodes":list(incoming_nodes.values('chan_id_in', 'score', 'ppm')), "outgoing_nodes":list(outgoing_nodes.values('chan_id_out', 'score', 'ppm'))})
        except Exception as e:
            print(f"{datetime.now().strftime('%c')} : [P2P] : Error getting secret: {str(e)}")
            secret = None
        finally:
            return secret
    elif sale_type == 2: # payment data
        try:
            self_pubkey = stub.GetInfo(ln.GetInfoRequest()).identity_pubkey
            filter_30day = datetime.now() - timedelta(days=30)
            # exlcude_list = AvoidNodes.objects.values_list('pubkey')
            payments_30day = Payments.objects.filter(creation_date__gte=filter_30day, status=2).values_list('payment_hash')
            payment_nodes = PaymentHops.objects.filter(payment_hash__in=payments_30day).exclude(node_pubkey=self_pubkey).values('node_pubkey').annotate(ppm=Round((Sum('fee')/Sum('amt'))*1000000, output_field=IntegerField()), score=Round((Round(Count('id')/1, output_field=IntegerField())+Round(Sum('amt')/100000, output_field=IntegerField()))/10, output_field=IntegerField())).exclude(score=0).order_by('-score', 'ppm')[:10]
            secret = json.dumps({"payment_nodes": list(payment_nodes.values('node_pubkey', 'score', 'ppm'))})
        except Exception as e:
            print(f"{datetime.now().strftime('%c')} : [P2P] : Error getting secret: {str(e)}")
            secret = None
        finally:
            return secret
    else:
        return None

def serve_trades(stub):
    print(f"{datetime.now().strftime('%c')} : [P2P] : Serving trades...")
    for trade in get_trades():
        print(f"{datetime.now().strftime('%c')} : [P2P] : Serving trade: {trade.id}")
    for response in stub.SubscribeCustomMessages(ln.SubscribeCustomMessagesRequest()):
        if response.type == 32768:
            from_peer = response.peer
            msg_type = response.type
            message = response.data.hex()
            if msg_type == 32768 and message.lower().startswith('626f73ff'):
                msg_response = parse_peer_request_message(message)
                if 'request' in msg_response:
                    request = msg_response['request']
                    if 'type' in request:
                        req_type = request['type']
                        if req_type == '8050005': # request a seller to finalize a trade or give all open trades
                            print(f"{datetime.now().strftime('%c')} : [P2P] : SELLER ACTION", '|', 'ID:', request['id'], '|', 'Records:', request['records'])
                            select_trade = next((record for record in request['records'] if record['type'] == '0'), None)
                            request_trade = next((record for record in request['records'] if record['type'] == '1'), None)
                            if request_trade:
                                trades = get_trades()
                                for trade in trades:
                                    trade_data = encode_peer_request({'id':secrets.token_bytes(32).hex(), 'type':'8050006', 'records':[{'type': '1', 'value': trade.id}, {'type': '2', 'value': utf8_as_hex(trade.description)}, {'type': '0', 'value': request_trade['value']}]})
                                    stub.SendCustomMessage(ln.SendCustomMessageRequest(peer=from_peer, type=32768, data=bytes.fromhex(trade_data)))
                                ack_data = encode_peer_response({'failure':None, 'id':request['id'], 'records':[]})
                                for trade in trades:
                                    stub.SendCustomMessage(ln.SendCustomMessageRequest(peer=from_peer, type=32768, data=bytes.fromhex(ack_data)))
                            if select_trade:
                                selected_trade = get_trades(trade.id)
                                if selected_trade:
                                    trade_details = selected_trade[0]
                                    if not trade_details.secret:
                                        secret = getSecret(stub, trade_details.sale_type)
                                    else:
                                        secret = trade_details.secret
                                    if not secret:
                                        print(f"{datetime.now().strftime('%c')} : [P2P] : Failed to get secret for:", trade_details.id)
                                        continue
                                    signerstub = lnsigner.SignerStub(lnd_connect())
                                    shared_key = signerstub.DeriveSharedKey(lns.SharedKeyRequest(ephemeral_pubkey=from_peer)).shared_key
                                    preimage = secrets.token_bytes(32)
                                    shared_secret = bytes(x ^ y for x, y in zip(shared_key, preimage))
                                    cipher = Cipher(algorithms.AES(shared_secret), modes.GCM(bytes(16)), backend=default_backend())
                                    encryptor = cipher.encryptor()
                                    ciphertext = (encryptor.update(secret.encode('utf-8')) + encryptor.finalize()).hex()
                                    auth_tag = encryptor.tag.hex()
                                    time_to_expiry = (trade_details.expiry-datetime.now()).seconds if trade_details.expiry else None
                                    default_expiry = 30*60
                                    inv_expiry = default_expiry if time_to_expiry is None or time_to_expiry > default_expiry else time_to_expiry
                                    if inv_expiry > 0:
                                        final_invoice = stub.AddInvoice(ln.Invoice(memo=trade_details.description, value=trade_details.price, expiry=inv_expiry, r_preimage=preimage))
                                        trade_data = encode_peer_response({'failure': None, 'id':request['id'], 'records': [{'type':'1', 'value':encode_final_trade(auth_tag, ciphertext, final_invoice.payment_request)}]})
                                        trade_details.sale_count = F('sale_count') + 1
                                        trade_details.save()
                                        stub.SendCustomMessage(ln.SendCustomMessageRequest(peer=from_peer, type=32768, data=bytes.fromhex(trade_data)))
                    else:
                        print(f"{datetime.now().strftime('%c')} : [P2P] : Expected request type in message:", request['id'])
                if 'response' in msg_response:
                    request = msg_response['response']
                    if 'failure' in request and request['failure'] != None:
                        # failure message returned
                        print(f"{datetime.now().strftime('%c')} : [P2P] : Failure:", request['failure'])
                    else:
                        if len(request['records']) == 0:
                            # message acknowledgements
                            print(f"{datetime.now().strftime('%c')} : [P2P] : ACK", '|', 'ID:', request['id'])

async def get_open_trades(astub, results):
    try:
        async for response in astub.SubscribeCustomMessages(ln.SubscribeCustomMessagesRequest()):
            if response.type == 32768:
                # from_peer = response.peer
                msg_type = response.type
                message = response.data.hex()
                if msg_type == 32768 and message.lower().startswith('626f73ff'):
                    msg_response = parse_peer_request_message(message)
                    if 'request' in msg_response:
                        request = msg_response['request']
                        if 'type' in request:
                            req_type = request['type']
                            if req_type == '8050006': # request a buyer to select the trade provided
                                # select a trade from the records
                                trade = decode_basic_trade(request['records'])
                                print('BUYER ACTION', '|', 'ID:', request['id'], '|', 'Trade:', trade)
                                results.append({'id': request['id'], 'trade': trade})
                        else:
                            raise ValueError('ExpectedRequestTypeInRequestMessage')
                    if 'response' in msg_response:
                        request = msg_response['response']
                        if 'failure' in request and request['failure'] != None:
                            # failure message returned
                            print('Failure:', request['failure'])
                            return
                        else:
                            if len(request['records']) == 0:
                                # message acknowledgements
                                print('ACK', '|', 'ID:', request['id'])
                            else:
                                # buyer to pay invoice and get secret their secret from preimage
                                print('BUYER FINALIZE', '|', 'ID:', request['id'], '|', 'Records:', request['records'])
                                return request['records']
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print('Error runnig task:', str(e))

def encode_nodes_data(data, network_value):
    records = [{'type': '0', 'value': '01'}]
    if network_value:
        records.append({'type': '1', 'value': network_value})

    node_records = []
    for idx, node in enumerate(data):
        node_record = [{ 'type': '2', 'value': node['id'] }]
        encoded_node_record = ''.join([encode_tlv_record(record) for record in node_record])
        node_records.append({'type': str(idx), 'value': encoded_node_record})
    records.append({'type': '4', 'value': ''.join([encode_tlv_record(record) for record in node_records])})
    nodes_encoded = '626f73ff' + ''.join([encode_tlv_record(record) for record in records])
    return nodes_encoded

def decode_node_record(encoded):
    channel_hex_length = 16
    if not encoded:
        raise ValueError('ExpectedEncodedNodeRecordToGetNodePointer')

    records = decode_tlv_stream(encoded['value'])
    high_key_record = next((n for n in records if n['type'] == '1'), None)

    if high_key_record and len(high_key_record['value']) != channel_hex_length:
        raise ValueError('ExpectedChannelIdInHighKeyRecord')
    if high_key_record:
        return {'high_channel': high_key_record['value']}

    low_key_record = next((n for n in records if n['type'] == '0'), None)
    if low_key_record and len(low_key_record['value']) != channel_hex_length:
        raise ValueError('ExpectedChannelIdInLowKeyRecord')
    if low_key_record:
        return {'low_channel': low_key_record['value']}

    id_record = next((n for n in records if n['type'] == '2'), None)
    if not id_record:
        raise ValueError('ExpectedNodeIdRecordToMapNodeRecordToNodePointer')

    if not (bool(id_record['value']) and re.match(r'^0[2-3][0-9A-F]{64}$', id_record['value'], re.I)):
        raise ValueError('ExpectedNodeIdPublicKeyToMapNodeRecordToNodePointer')

    return {'node': {'id': id_record['value']}}

def decode_open_trade(network, records):
    if not network:
        raise ValueError('ExpectedNetworkNameToDecodeOpenTrade')
    if not isinstance(records, list):
        raise ValueError('ExpectedArrayOfRecordsToDecodeOpenTrade')

    nodes_record = next((n for n in records if n['type'] == '4'), None)
    id_record = next((n for n in records if n['type'] == '5'), None)
    if not nodes_record:
        raise ValueError('ExpectedNodesRecordToDecodeOpenTradeDetails')

    try:
        decode_tlv_stream(nodes_record['value'])
    except:
        raise ValueError('ExpectedValidNodesTlvStreamToDecodeOpenTradeDetails')

    node_records = decode_tlv_stream(nodes_record['value'])
    if not node_records:
        raise ValueError('ExpectedNodeRecordsForOpenTrade')

    return network, id_record['value'] if id_record else None, [decode_node_record(value) for value in node_records]

def decode_trade_data(encoded):
    if not encoded.lower().startswith('626f73ff'):
        raise ValueError('UnexpectedFormatOfTradeToDecode')
    try:
        decoded_trade = decode_tlv_stream(encoded[8:])
    except:
        raise ValueError('ExpectedValidTlvStreamForTradeData')
    records = decoded_trade
   
    network_value = next((record for record in records if record['type'] == '1'), None)
    if network_value:
        if network_value['value'] == '01':
            if settings.LND_NETWORK == 'testnet':
                network = 'testnet'
            else:
                raise ValueError('TradeRequestForAnotherNetwork')
        elif network_value['value'] =='02':
            if settings.LND_NETWORK == 'regtest':
                network = 'regtest'
            else:
                raise ValueError('TradeRequestForAnotherNetwork')
        else:
            raise ValueError('UnknownNetworkNameToDeriveNetworkRecordFor')
    else:
        if settings.LND_NETWORK == 'mainnet':
            network = 'bitcoin'
        else:
            raise ValueError('TradeRequestForAnotherNetwork')

    request = next((record for record in records if record['type'] == '2'), None)
    details = next((record for record in records if record['type'] == '3'), None)
    swap = next((record for record in records if record['type'] == '6'), None)

    if request and details:
        return {'secret': decode_final_trade(network, request, details)}
    elif request:
        pass # just a payment
    elif swap:
        pass # swap offer
    else:
        return {'connect': decode_open_trade(network, records)}

def encode_trade(description, price, secret):
    anchorPrefix = 'anchor-trade-secret:'
    elements = [
        {'value': secret, 'type': '0'},
        {'value': description, 'type': '1'},
        {'value': price, 'type': '2'},
    ]

    records = [
        {'type': record['type'], 'value': bytes(record['value'], 'utf-8').hex()}
        for record in elements if record
    ]
    encoded_data = ''.join([encode_tlv_record(record) for record in records])
    encoded = anchorPrefix + base64.b64encode(bytes.fromhex(encoded_data)).decode()

    return encoded

def create_trade_details(stub):
    nodes = [{'id':stub.GetInfo(ln.GetInfoRequest()).identity_pubkey}]
    lnd_network = settings.LND_NETWORK
    if lnd_network == 'mainnet':
        network_value = None
    elif lnd_network == 'testnet':
        network_value = '01'
    elif lnd_network == 'regtest':
        network_value = '02'
    else:
        raise ValueError('UnsupportedNetworkForTrades')
    return encode_nodes_data(nodes, network_value)

def create_trade_anchor(stub, description, price, secret, expiry):
    try:
        encoded_trade = encode_trade(description, price, secret)
        stub.AddInvoice(ln.Invoice(value=int(price), expiry=int(expiry)*60*60*24, memo=encoded_trade))
    except Exception as e:
        print('Error creating trade:', str(e))
    print('Trade Anchor:', encoded_trade)

async def request_trades(to_peer):
    results = []
    start_time = time()
    astub = lnrpc.LightningStub(async_lnd_connect())
    task = asyncio.create_task(get_open_trades(astub, results))
    asyncio.gather(task)
    trade_data = encode_peer_request({'id':secrets.token_bytes(32).hex(), 'type':'8050005', 'records':[{'type': '1', 'value': secrets.token_bytes(32).hex()}]})
    astub.SendCustomMessage(ln.SendCustomMessageRequest(peer=bytes.fromhex(to_peer), type=32768, data=bytes.fromhex(trade_data)))
    while len(results) == 0:
        if (time() - start_time) < 30:
            await asyncio.sleep(1)
        else:
            print('Timeout waiting for trade records from peer.')
            task.cancel()
            return None
    await asyncio.sleep(1)
    if len(results) == 1:
        ack_data = encode_peer_response({'failure':None, 'id': results[0]['id'], 'records':[]})
        astub.SendCustomMessage(ln.SendCustomMessageRequest(peer=bytes.fromhex(to_peer), type=32768, data=bytes.fromhex(ack_data)))
        choice = 1
    else:
        print('Select a trade to buy:')
        for idx, trade in enumerate(results, start=1):
            ack_data = encode_peer_response({'failure':None, 'id': trade['id'], 'records':[]})
            astub.SendCustomMessage(ln.SendCustomMessageRequest(peer=bytes.fromhex(to_peer), type=32768, data=bytes.fromhex(ack_data)))
            print(f"{idx}. {trade['trade']['description']}")
        while True:
            try:
                choice = int(input("Enter the number of your choice: "))
                if 1 <= choice <= len(results):
                    break
                else:
                    print("Invalid input. Please enter a valid option.")
            except ValueError:
                print("Invalid input. Please enter a number for your selection.")
    selected_trade = results[choice - 1]
    trade_data = encode_peer_request({'id':secrets.token_bytes(32).hex(), 'type':'8050005', 'records':[{'type': '0', 'value': selected_trade['trade']['id']}]})
    astub.SendCustomMessage(ln.SendCustomMessageRequest(peer=bytes.fromhex(to_peer), type=32768, data=bytes.fromhex(trade_data)))
    return await task

def decrypt_secret(stub, decoded_trade):
    invoice, auth, payload = decoded_trade['secret']
    decoded_invoice = stub.DecodePayReq(ln.PayReqString(pay_req=invoice))
    print('Invoice for secret decoded.')
    print('Destination:', decoded_invoice.destination)
    print('Amount:', decoded_invoice.num_satoshis)
    print('Description:', decoded_invoice.description)
    ask_pay = input('Pay the invoice and decrypt the secret? [y/N]: ')
    if ask_pay.lower() == 'y':
        routerstub = lnrouter.RouterStub(lnd_connect())
        for response in routerstub.SendPaymentV2(lnr.SendPaymentRequest(payment_request=invoice, timeout_seconds=60)):
            if response.status == 2:
                print('Payment paid!')
                preimage =  bytes.fromhex(response.payment_preimage)
            if response.status > 2:
                print('Payment failed. Please try again.')
                return
        signerstub = lnsigner.SignerStub(lnd_connect())
        shared_key = signerstub.DeriveSharedKey(lns.SharedKeyRequest(ephemeral_pubkey=bytes.fromhex(decoded_invoice.destination))).shared_key
        shared_secret = bytes(x ^ y for x, y in zip(shared_key, preimage))
        cipher = Cipher(algorithms.AES(shared_secret), modes.GCM(bytes(16), bytes.fromhex(auth)), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(bytes.fromhex(payload)) + decryptor.finalize()
        print('Successfully decrypted the secret:', decrypted.decode('utf-8'))

def main():
    options = ["Buy A Trade", "Setup A Sale", "Serve Trades"]
    print("Select an option:")
    for idx, option in enumerate(options, start=1):
        print(f"{idx}. {option}")
    while True:
        try:
            choice = int(input("Enter the number of your choice: "))
            if 1 <= choice <= len(options):
                break
            else:
                print("Invalid input. Please enter a valid option.")
        except ValueError:
            print("Invalid input. Please enter a number for your selection.")
    selected_option = options[choice - 1]
    stub = lnrpc.LightningStub(lnd_connect())
    if selected_option == 'Setup A Sale':
        description = input('Enter a description for the trade: ')
        price = input('Enter the price to charge in sats: ')
        expiry = input('Enter desired days until trade expiry: ')
        secret = input('Enter the secret you want to sell: ')
        create_trade_anchor(stub, description, price, secret, expiry)
        ask_serve = input('Start serving trades? y/N: ')
        if ask_serve.lower() == 'y':
            print('Generic Trade Link:', create_trade_details(stub))
            serve_trades(stub)
    if selected_option == 'Serve Trades':
        print('Generic Trade Link:', create_trade_details(stub))
        serve_trades(stub)
    if selected_option == 'Buy A Trade':
        trade = input('Enter an encoded trade: ')
        decoded_trade = decode_trade_data(trade)
        if 'secret' in decoded_trade:
            decrypt_secret(stub, decoded_trade)
        if 'connect' in decoded_trade:
            network, id, connection = decoded_trade['connect']
            if 'node' in connection[0]:
                try:
                    to_peer = connection[0]['node']['id']
                    if not (Peers.objects.filter(pubkey=to_peer).exists() and Peers.objects.filter(pubkey=to_peer)[0].connected == True):
                        host = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=to_peer, include_channels=False)).node.addresses[0].addr
                        stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln.LightningAddress(pubkey=to_peer, host=host), timeout=60))
                except:
                    raise ValueError('PeerConnectionError')
            else:
                raise ValueError('NoPeerFoundInConnectionData')
            trade = asyncio.run(request_trades(to_peer))
            if trade:
                trade_data = next((record for record in trade if record['type'] == '1'), None)
                if trade_data:
                    decoded_trade = decode_trade_data(trade_data['value'])
                    decrypt_secret(stub, decoded_trade)

if __name__ == '__main__':
    main()