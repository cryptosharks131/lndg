import os, codecs, django, grpc, secrets
from django.conf import settings
from pathlib import Path
from hashlib import sha256
import router_pb2 as lnr
import router_pb2_grpc as lnrouter

BASE_DIR = Path(__file__).resolve().parent.parent
settings.configure(
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3'
        }
    }
)
django.setup()
#from models import Payments, PaymentHops, Invoices, Forwards, Channels, Peers

def lnd_connect():
    #Open connection with lnd via grpc
    with open(os.path.expanduser('~/.lnd/data/chain/bitcoin/mainnet/admin.macaroon'), 'rb') as f:
        macaroon_bytes = f.read()
        macaroon = codecs.encode(macaroon_bytes, 'hex')
    def metadata_callback(context, callback):
        callback([('macaroon', macaroon)], None)
    os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'
    cert = open(os.path.expanduser('~/.lnd/tls.cert'), 'rb').read()
    cert_creds = grpc.ssl_channel_credentials(cert)
    auth_creds = grpc.metadata_call_credentials(metadata_callback)
    creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
    channel = grpc.secure_channel('localhost:10009', creds)
    return channel

def keysend(target_pubkey, msg, amount, fee_limit, timeout):
    #Construct and send
    routerstub = lnrouter.RouterStub(lnd_connect())
    secret = secrets.token_bytes(32)
    hashed_secret = sha256(secret).hexdigest()
    hex_msg = msg.encode('utf-8').hex()
    for response in routerstub.SendPaymentV2(lnr.SendPaymentRequest(dest=bytes.fromhex(target_pubkey), dest_custom_records=[(34349334, bytes.fromhex(hex_msg)),(5482373484, secret),], fee_limit_sat=fee_limit, timeout_seconds=timeout, amt=amount, payment_hash=bytes.fromhex(hashed_secret))):
        if response.status == 1:
            print('In-flight')
        if response.status == 2:
            print('Succeeded')
        if response.status == 3:
            if response.failure_reason == 1:
                print('Failure - Timeout')
            elif response.failure_reason == 2:
                print('Failure - No Route')
            elif response.failure_reason == 3:
                print('Failure - Error')
            elif response.failure_reason == 4:
                print('Failure - Incorrect Payment Details')
            elif response.failure_reason == 5:
                print('Failure Insufficient Balance')
        if response.status == 0:
            print('Unknown Error')

def main():
    #User defined variables
    target_pubkey = '<fill_target_pubkey_here>'
    msg = '<fill_message_here>'
    amount = 10
    fee_limit = 10
    timeout = 10
    keysend(target_pubkey, msg, amount, fee_limit, timeout)

if __name__ == '__main__':
    main()