from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps.lnd_connect import lnd_connect

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
