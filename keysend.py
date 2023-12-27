import argparse
import secrets, time, struct
from hashlib import sha256
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
        routerstub = lnrouter.RouterStub(lnd_connect())
        secret = secrets.token_bytes(32)
        hashed_secret = sha256(secret).hexdigest()
        custom_records = [(5482373484, secret),]
        msg = str(msg)
        if len(msg) > 0:
            custom_records.append((34349334, bytes.fromhex(msg.encode('utf-8').hex())))
            if sign == True:
                stub = lnrpc.LightningStub(lnd_connect())
                signerstub = lnsigner.SignerStub(lnd_connect())
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

def main(pubkey, amount, fee, msg, sign):
    print('Sending a %s sats payment to: %s with %s sats max-fee' % (amount, pubkey, fee))
    if len(msg) > 0:
        print('MESSAGE: %s' % msg) 
    timeout = 10
    keysend(pubkey, msg, amount, fee, timeout, sign)

if __name__ == '__main__':
    argParser = argparse.ArgumentParser(prog="python keysend.py")
    argParser.add_argument("-pk", "--pubkey", help='Target public key', required=True)
    argParser.add_argument("-a", "--amount", help='Amount in sats (default: 1)', nargs='?', default=1, type=int) 
    argParser.add_argument("-f", "--fee", help='Max fee to send this keysend (default: 1)', nargs='?', default=1, type=int)
    argParser.add_argument("-m", "--msg", help='Message to be sent (default: "")', nargs='?', default='', type=str)
    argParser.add_argument("--sign", help='Sign this message (default: send anonymously) - if [MSG] is provided', action='store_true')
    args = vars(argParser.parse_args())
    main(**args)