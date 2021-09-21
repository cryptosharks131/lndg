import os, codecs, grpc
from lnd_deps import lightning_pb2 as ln
from lnd_deps import lightning_pb2_grpc as lnrpc

#Define lnd connection for repeated use
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

def main():
    stub = lnrpc.LightningStub(lnd_connect())
    try:
        stub.DeleteAllPayments(ln.DeleteAllPaymentsRequest(failed_payments_only=False, failed_htlcs_only=True))
        stub.DeleteAllPayments(ln.DeleteAllPaymentsRequest(failed_payments_only=True, failed_htlcs_only=False))
    except Exception as e:
        print('Exception occured: ', e)
    finally:
        print('Delete All Payments Completed')

if __name__ == '__main__':
    main()
