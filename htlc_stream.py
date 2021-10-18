import django, datetime
from django.conf import settings
from pathlib import Path
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps.lnd_connect import lnd_connect

BASE_DIR = Path(__file__).resolve().parent
settings.configure(
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3'
        }
    }
)
django.setup()
from lndg import settings
from gui.models import Channels

def main():
    try:
        connection = lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER)
        routerstub = lnrouter.RouterStub(connection)
        lndg_path = str(Path(__file__).resolve().parent)
        f = open(lndg_path + '/failed-htlc-stream.txt', 'a')
        for response in routerstub.SubscribeHtlcEvents(lnr.SubscribeHtlcEventsRequest()):
            if response.event_type == 3 and str(response.link_fail_event) != '':
                output = {}
                in_chan_id = response.incoming_channel_id
                out_chan_id = response.outgoing_channel_id
                in_chan_alias = Channels.objects.filter(chan_id=in_chan_id)[0].alias
                out_chan_alias = Channels.objects.filter(chan_id=out_chan_id)[0].alias
                amount = response.link_fail_event.info.outgoing_amt_msat/1000
                wire_failure = response.link_fail_event.wire_failure
                if wire_failure == 0:
                    wire_failure_str = 'RESERVED'
                elif wire_failure == 1:
                    wire_failure_str = 'INCORRECT_OR_UNKNOWN_PAYMENT_DETAILS'
                elif wire_failure == 2:
                    wire_failure_str = 'INCORRECT_PAYMENT_AMOUNT'
                elif wire_failure == 3:
                    wire_failure_str = 'FINAL_INCORRECT_CLTV_EXPIRY'
                elif wire_failure == 4:
                    wire_failure_str = 'FINAL_INCORRECT_HTLC_AMOUNT'
                elif wire_failure == 5:
                    wire_failure_str = 'FINAL_EXPIRY_TOO_SOON'
                elif wire_failure == 6:
                    wire_failure_str = 'INVALID_REALM'
                elif wire_failure == 7:
                    wire_failure_str = 'EXPIRY_TOO_SOON'
                elif wire_failure == 8:
                    wire_failure_str = 'INVALID_ONION_VERSION'
                elif wire_failure == 9:
                    wire_failure_str = 'INVALID_ONION_HMAC'
                elif wire_failure == 10:
                    wire_failure_str = 'INVALID_ONION_KEY'
                elif wire_failure == 11:
                    wire_failure_str = 'AMOUNT_BELOW_MINIMUM'
                elif wire_failure == 12:
                    wire_failure_str = 'FEE_INSUFFICIENT'
                elif wire_failure == 13:
                    wire_failure_str = 'INCORRECT_CLTV_EXPIRY'
                elif wire_failure == 14:
                    wire_failure_str = 'CHANNEL_DISABLED'
                elif wire_failure == 15:
                    wire_failure_str = 'TEMPORARY_CHANNEL_FAILURE'
                elif wire_failure == 16:
                    wire_failure_str = 'REQUIRED_NODE_FEATURE_MISSING'
                elif wire_failure == 17:
                    wire_failure_str = 'REQUIRED_CHANNEL_FEATURE_MISSING'
                elif wire_failure == 18:
                    wire_failure_str = 'UNKNOWN_NEXT_PEER'
                elif wire_failure == 19:
                    wire_failure_str = 'TEMPORARY_NODE_FAILURE'
                elif wire_failure == 20:
                    wire_failure_str = 'PERMANENT_NODE_FAILURE'
                elif wire_failure == 21:
                    wire_failure_str = 'PERMANENT_CHANNEL_FAILURE'
                elif wire_failure == 22:
                    wire_failure_str = 'EXPIRY_TOO_FAR'
                elif wire_failure == 23:
                    wire_failure_str = 'MPP_TIMEOUT'
                elif wire_failure == 24:
                    wire_failure_str = 'INVALID_ONION_PAYLOAD'
                elif wire_failure == 997:
                    wire_failure_str = 'INTERNAL_FAILURE'
                elif wire_failure == 998:
                    wire_failure_str = 'UNKNOWN_FAILURE'
                elif wire_failure == 999:
                    wire_failure_str = 'UNREADABLE_FAILURE'
                failure_detail = response.link_fail_event.failure_detail
                if failure_detail == 0:
                    failure_detail_str = 'UNKNOWN'
                elif failure_detail == 1:
                    failure_detail_str = 'NO_DETAIL'
                elif failure_detail == 2:
                    failure_detail_str = 'ONION_DECODE'
                elif failure_detail == 3:
                    failure_detail_str = 'LINK_NOT_ELIGIBLE'
                elif failure_detail == 4:
                    failure_detail_str = 'ON_CHAIN_TIMEOUT'
                elif failure_detail == 5:
                    failure_detail_str = 'HTLC_EXCEEDS_MAX'
                elif failure_detail == 6:
                    failure_detail_str = 'INSUFFICIENT_BALANCE'
                elif failure_detail == 7:
                    failure_detail_str = 'INCOMPLETE_FORWARD'
                elif failure_detail == 8:
                    failure_detail_str = 'HTLC_ADD_FAILED'
                elif failure_detail == 9:
                    failure_detail_str = 'FORWARDS_DISABLED'
                elif failure_detail == 10:
                    failure_detail_str = 'INVOICE_CANCELED'
                elif failure_detail == 11:
                    failure_detail_str = 'INVOICE_UNDERPAID '
                elif failure_detail == 12:
                    failure_detail_str = 'INVOICE_EXPIRY_TOO_SOON'
                elif failure_detail == 13:
                    failure_detail_str = 'INVOICE_NOT_OPEN'
                elif failure_detail == 14:
                    failure_detail_str = 'MPP_INVOICE_TIMEOUT'
                elif failure_detail == 15:
                    failure_detail_str = 'ADDRESS_MISMATCH'
                elif failure_detail == 16:
                    failure_detail_str = 'SET_TOTAL_MISMATCH'
                elif failure_detail == 17:
                    failure_detail_str = 'SET_TOTAL_TOO_LOW'
                elif failure_detail == 18:
                    failure_detail_str = 'SET_OVERPAID'
                elif failure_detail == 19:
                    failure_detail_str = 'UNKNOWN_INVOICE'
                elif failure_detail == 20:
                    failure_detail_str = 'INVALID_KEYSEND'
                elif failure_detail == 21:
                    failure_detail_str = 'MPP_IN_PROGRESS'
                elif failure_detail == 22:
                    failure_detail_str = 'CIRCULAR_ROUTE'
                failure_string = response.link_fail_event.failure_string
                output.update({'timestamp':datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S%z')})
                output.update({'amount':amount})
                output.update({'incoming_channel_alias':in_chan_alias})
                output.update({'outgoing_channel_alias':out_chan_alias})
                output.update({'incoming_channel_id':in_chan_id})
                output.update({'outgoing_channel_id':out_chan_id})
                output.update({'wire_failure':wire_failure_str})
                output.update({'failure_detail':failure_detail_str})
                output.update({'failure_string':failure_string})
                f.write(str(output) + '\n')
    except Exception as e:
        print(str(e))
    finally:
        f.close()

if __name__ == '__main__':
    main()