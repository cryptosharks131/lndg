import os, codecs, grpc, secrets
from hashlib import sha256
from lndg import settings
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps.lnd_connect import lnd_connect

def keysend(target_pubkey, msg, amount, fee_limit, timeout):
    #Construct and send
    routerstub = lnrouter.RouterStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
    secret = secrets.token_bytes(32)
    hashed_secret = sha256(secret).hexdigest()
    custom_records = [(5482373484, secret),]
    msg = str(msg)
    if len(msg) > 0:
        custom_records.append((34349334, bytes.fromhex(msg.encode('utf-8').hex())))
    for response in routerstub.SendPaymentV2(lnr.SendPaymentRequest(dest=bytes.fromhex(target_pubkey), dest_custom_records=custom_records, fee_limit_sat=fee_limit, timeout_seconds=timeout, amt=amount, payment_hash=bytes.fromhex(hashed_secret))):
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
    #Ask user for variables
    try:
        target_pubkey = input('Enter the pubkey of the node you want to send a keysend payment to: ')
        amount = int(input('Enter an amount in sats to be sent with the keysend payment (defaults to 1 sat): ') or '1')
        fee_limit = int(input('Enter an amount in sats to be used as a max fee limit for sending (defaults to 1 sat): ') or '1')
        msg = input('Enter an optional message to be included (leave this blank for no message): ')
    except:
        print('Invalid data entered, please try again.')
    timeout = 10
    print('Sending keysend payment of %s to: %s' % (amount, target_pubkey))
    if len(msg) > 0:
        print('Attaching this message to the keysend payment:', msg)
    keysend(target_pubkey, msg, amount, fee_limit, timeout)

if __name__ == '__main__':
    main()