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

def get_channel_options():
    return [
        ('grpc.max_send_message_length', int(settings.LND_MAX_MESSAGE) * 1000000),
        ('grpc.max_receive_message_length', int(settings.LND_MAX_MESSAGE) * 1000000),
        ('grpc.keepalive_time_ms', 30000),
        ('grpc.keepalive_timeout_ms', 10000),
        ('grpc.keepalive_permit_without_calls', 1),
        ('grpc.http2.max_pings_without_data', 0),
        ('grpc.http2.min_time_between_pings_ms', 10000),
        ('grpc.http2.min_ping_interval_without_data_ms', 10000),
    ]

try:
    creds = get_creds()
except Exception:
    creds = None

def lnd_connect():
    global creds
    if creds is None:
        creds = get_creds()
    return grpc.secure_channel(settings.LND_RPC_SERVER, creds, options=get_channel_options())

def async_lnd_connect():
    global creds
    if creds is None:
        creds = get_creds()
    return grpc.aio.secure_channel(settings.LND_RPC_SERVER, creds, options=get_channel_options())

def main():
    pass

if __name__ == '__main__':
    main()