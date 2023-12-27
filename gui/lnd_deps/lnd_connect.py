import os, codecs, grpc
from lndg import settings

def get_creds():
    #Open connection with lnd via grpc
    with open(os.path.expanduser(settings.LND_MACAROON_PATH), 'rb') as f:
        macaroon_bytes = f.read()
        macaroon = codecs.encode(macaroon_bytes, 'hex')
    def metadata_callback(context, callback):
        callback([('macaroon', macaroon)], None)
    os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'
    cert = open(os.path.expanduser(settings.LND_TLS_PATH), 'rb').read()
    cert_creds = grpc.ssl_channel_credentials(cert)
    auth_creds = grpc.metadata_call_credentials(metadata_callback)
    creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
    return creds

creds = get_creds()
def lnd_connect():
    return grpc.secure_channel(settings.LND_RPC_SERVER, creds, options=[('grpc.max_send_message_length', int(settings.LND_MAX_MESSAGE)*1000000), ('grpc.max_receive_message_length', int(settings.LND_MAX_MESSAGE)*1000000),])

def async_lnd_connect():
    return grpc.aio.secure_channel(settings.LND_RPC_SERVER, creds, options=[('grpc.max_send_message_length', int(settings.LND_MAX_MESSAGE)*1000000), ('grpc.max_receive_message_length', int(settings.LND_MAX_MESSAGE)*1000000),])

def main():
    pass

if __name__ == '__main__':
    main()