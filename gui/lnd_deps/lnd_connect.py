import os, codecs, grpc

def lnd_connect(LND_DIR_PATH, LND_NETWORK,LND_RPC_SERVER):
    #Open connection with lnd via grpc
    with open(os.path.expanduser(LND_DIR_PATH + '/data/chain/bitcoin/' + LND_NETWORK + '/admin.macaroon'), 'rb') as f:
        macaroon_bytes = f.read()
        macaroon = codecs.encode(macaroon_bytes, 'hex')
    def metadata_callback(context, callback):
        callback([('macaroon', macaroon)], None)
    os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'
    cert = open(os.path.expanduser(LND_DIR_PATH + '/tls.cert'), 'rb').read()
    cert_creds = grpc.ssl_channel_credentials(cert)
    auth_creds = grpc.metadata_call_credentials(metadata_callback)
    creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
    channel = grpc.secure_channel(LND_RPC_SERVER, creds)
    return channel

def main():
    pass

if __name__ == '__main__':
    main()