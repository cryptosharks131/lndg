import os, codecs, django, grpc
from django.conf import settings
from django.db.models import Max
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
from models import Payments, Invoices, Forwards, Channels

def update_payments(stub):
    #Get the number of records in the database currently
    last_index = 0 if Payments.objects.aggregate(Max('index'))['index__max'] == None else Payments.objects.aggregate(Max('index'))['index__max']
    payments = stub.ListPayments(ln.ListPaymentsRequest(include_incomplete=True, index_offset=last_index)).payments
    for payment in payments:
        Payments(creation_date=datetime.fromtimestamp(payment.creation_date), payment_hash=payment.payment_hash, value=payment.value, fee=round(payment.fee_msat/1000, 3), status=payment.status, index=payment.payment_index).save()

def update_invoices(stub):
    records = Invoices.objects.count()
    invoices = stub.ListInvoices(ln.ListInvoiceRequest(index_offset=records)).invoices
    for invoice in invoices:
        Invoices(creation_date=datetime.fromtimestamp(invoice.creation_date), settle_date=datetime.fromtimestamp(invoice.settle_date), r_hash=invoice.r_hash, value=invoice.value, amt_paid=invoice.amt_paid_sat, state=invoice.state).save()

def update_forwards(stub):
    records = Forwards.objects.count()
    forwards = stub.ForwardingHistory(ln.ForwardingHistoryRequest(start_time=1420070400, index_offset=records)).forwarding_events
    for forward in forwards:
        incoming_peer_alias = Channels.objects.filter(chan_id=forward.chan_id_in)[0].alias
        outgoing_peer_alias = Channels.objects.filter(chan_id=forward.chan_id_out)[0].alias
        Forwards(forward_date=datetime.fromtimestamp(forward.timestamp), chan_id_in=forward.chan_id_in, chan_id_out=forward.chan_id_out, chan_in_alias=incoming_peer_alias, chan_out_alias=outgoing_peer_alias, amt_in=forward.amt_in, amt_out=forward.amt_out, fee=round(forward.fee_msat/1000, 3)).save()

def update_channels(stub):
    counter = 0
    chan_list = []
    channels = stub.ListChannels(ln.ListChannelsRequest()).channels
    for channel in channels:
        exists = 1 if Channels.objects.filter(chan_id=channel.chan_id).count() == 1 else 0
        if exists == 1:
            #Update the channel record with the most current data
            db_channel = Channels.objects.filter(chan_id=channel.chan_id)[0]
            db_channel.capacity = channel.capacity
            db_channel.local_balance = channel.local_balance
            db_channel.remote_balance = channel.remote_balance
            db_channel.base_fee = channel.base_fee
            db_channel.fee_rate = channel.fee_rate
            db_channel.is_active = channel.is_active
            db_channel.is_open = True
            db_channel.save()
        elif exists == 0:
            #Create a record for this new channel
            alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=channel.remote_pubkey)).node.alias
            chan_data = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=channel.chan_id))
            policy = chan_data.node2_policy if chan_data.node1_pub == channel.remote_pubkey else chan_data.node1_policy
            Channels(remote_pubkey=channel.remote_pubkey, chan_id=channel.chan_id, capacity=channel.capacity, local_balance=channel.local_balance, remote_balance=channel.remote_balance, initiator=channel.initiator, alias=alias, base_fee=policy.fee_base_msat, fee_rate=policy.fee_rate_milli_msat, is_active=channel.active, is_open=True).save()
        counter += 1
        chan_list.append(channel.chan_id)
    records = Channels.objects.filter(is_open=True).count()
    if records > counter:
        #A channel must have been closed, mark it as closed
        channels = Channels.objects.filter(is_open=True).exclude(chan_id__in=chan_list)
        for channel in channels:
            channel.is_active = False
            channel.is_open = False
            channel.save()

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
    update_channels(stub)
    update_payments(stub)
    update_invoices(stub)
    update_forwards(stub)

if __name__ == '__main__':
    main()