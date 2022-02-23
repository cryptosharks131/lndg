import secrets, time, struct
from hashlib import sha256
from lndg import settings
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps import signer_pb2 as lns
from gui.lnd_deps import signer_pb2_grpc as lnsigner
from gui.lnd_deps.lnd_connect import lnd_connect

def keysend(target_pubkey, msg, amount, fee_limit, timeout, sign):
    #Construct and send
    try:
        routerstub = lnrouter.RouterStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        secret = secrets.token_bytes(32)
        hashed_secret = sha256(secret).hexdigest()
        custom_records = [(5482373484, secret),]
        msg = str(msg)
        if len(msg) > 0:
            custom_records.append((34349334, bytes.fromhex(msg.encode('utf-8').hex())))
            if sign == True:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                signerstub = lnsigner.SignerStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                self_pubkey = stub.GetInfo(ln.GetInfoRequest()).identity_pubkey
                timestamp = struct.pack(">i", int(time.time()))
                signature = signerstub.SignMessage(lns.SignMessageReq(msg=(bytes.fromhex(self_pubkey)+bytes.fromhex(target_pubkey)+timestamp+bytes.fromhex(msg.encode('utf-8').hex())), key_loc=lns.KeyLocator(key_family=6, key_index=0))).signature
                custom_records.append((34349337, signature))
                custom_records.append((34349339, bytes.fromhex(self_pubkey)))
                custom_records.append((34349343, timestamp))
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
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_error_index = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_error_index]
        print('Error while sending keysend payment! Error: ' + error_msg)

def main():
    #Ask user for variables
    try:
        target_pubkey = input('Enter the pubkey of the node you want to send a keysend payment to: ')
        amount = int(input('Enter an amount in sats to be sent with the keysend payment (defaults to 1 sat): ') or '1')
        fee_limit = int(input('Enter an amount in sats to be used as a max fee limit for sending (defaults to 1 sat): ') or '1')
        msg = input('Enter an optional message to be included (leave this blank for no message): ')
        if len(msg) > 0:
            sign = input('Self sign the message? (defaults to sending anonymously) [y/N]: ')
            sign = True if sign.lower() == 'yes' or sign.lower() == 'y' else False
        else:
            sign = False        
    except:
        print('Invalid data entered, please try again.')
    timeout = 10
    print('Sending keysend payment of %s to: %s' % (amount, target_pubkey))
    if len(msg) > 0:
        print('Attaching this message to the keysend payment:', msg)
    keysend(target_pubkey, msg, amount, fee_limit, timeout, sign)

if __name__ == '__main__':
    main()