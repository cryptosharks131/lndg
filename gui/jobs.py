import os, codecs, django, grpc
from django.conf import settings
from pathlib import Path
from datetime import datetime
import rpc_pb2 as ln
import rpc_pb2_grpc_jobs as lnrpc

BASE_DIR = Path(__file__).resolve().parent.parent
settings.configure(
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3'
        }
    },
    TIME_ZONE = 'America/New_York'
)
django.setup()
from models import Payments, Invoices, Forwards

def update_payments(stub):
    #Get the number of records in the database currently
    records = Payments.objects.count()
    payments = stub.ListPayments(ln.ListPaymentsRequest(include_incomplete=True, reversed=False, index_offset=records)).payments
    print(payments)
    for payment in payments:
        Payments(creation_date=datetime.fromtimestamp(payment.creation_date), payment_hash=payment.payment_hash, value=payment.value, fee=payment.fee, status=payment.status).save()

def update_invoices(stub):
    records = Invoices.objects.count()
    invoices = stub.ListInvoices(ln.ListInvoiceRequest(index_offset=records)).invoices
    for invoice in invoices:
        Invoices(creation_date=datetime.fromtimestamp(invoice.creation_date), settle_date=datetime.fromtimestamp(invoice.settle_date), r_hash=invoice.r_hash, value=invoice.value, amt_paid=invoice.amt_paid_sat, state=invoice.state).save()

def update_forwards(stub):
    local_node = stub.GetInfo(ln.GetInfoRequest()).identity_pubkey
    records = Forwards.objects.count()
    forwards = stub.ForwardingHistory(ln.ForwardingHistoryRequest(start_time=1420070400, index_offset=records)).forwarding_events
    for forward in forwards:
        chan_in_data = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=forward.chan_id_in))
        incoming_peer_pubkey = chan_in_data.node2_pub if chan_in_data.node1_pub == local_node else chan_in_data.node1_pub
        chan_out_data = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=forward.chan_id_out))
        outgoing_peer_pubkey = chan_out_data.node2_pub if chan_out_data.node1_pub == local_node else chan_out_data.node1_pub
        incoming_peer_alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=incoming_peer_pubkey)).node.alias
        outgoing_peer_alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=outgoing_peer_pubkey)).node.alias
        Forwards(forward_date=datetime.fromtimestamp(forward.timestamp), chan_id_in=forward.chan_id_in, chan_id_out=forward.chan_id_out, chan_in_alias=incoming_peer_alias, chan_out_alias=outgoing_peer_alias, amt_in=forward.amt_in, amt_out=forward.amt_out, fee=round(forward.fee_msat/1000, 3)).save()

def main():
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
    stub = lnrpc.LightningStub(channel)
    #Update data
    update_payments(stub)
    update_invoices(stub)
    update_forwards(stub)

if __name__ == '__main__':
    main()