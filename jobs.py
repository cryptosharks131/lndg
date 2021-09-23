import os, codecs, django, grpc
from django.conf import settings
from django.db.models import Max
from pathlib import Path
from datetime import datetime
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc

BASE_DIR = Path(__file__).resolve().parent
settings.configure(
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3'
        }
    }
)
django.setup()
from lndg import settings
from gui.models import Payments, PaymentHops, Invoices, Forwards, Channels, Peers

def update_payments(stub):
    #Remove anything in-flight so we can get most up to date status
    Payments.objects.filter(status=1).delete()
    #Get the number of records in the database currently
    last_index = 0 if Payments.objects.aggregate(Max('index'))['index__max'] == None else Payments.objects.aggregate(Max('index'))['index__max']
    payments = stub.ListPayments(ln.ListPaymentsRequest(include_incomplete=True, index_offset=last_index, max_payments=100)).payments
    for payment in payments:
        try:
            new_payment = Payments(creation_date=datetime.fromtimestamp(payment.creation_date), payment_hash=payment.payment_hash, value=round(payment.value_msat/1000, 3), fee=round(payment.fee_msat/1000, 3), status=payment.status, index=payment.payment_index)
            new_payment.save()
            if payment.status == 2:
                for attempt in payment.htlcs:
                    if attempt.status == 1:
                        hops = attempt.route.hops
                        hop_count = 0
                        total_hops = len(hops)
                        for hop in hops:
                            hop_count += 1
                            alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=hop.pub_key)).node.alias
                            PaymentHops(payment_hash=new_payment, attempt_id=attempt.attempt_id, step=hop_count, chan_id=hop.chan_id, alias=alias, chan_capacity=hop.chan_capacity, node_pubkey=hop.pub_key, amt=round(hop.amt_to_forward_msat/1000, 3), fee=round(hop.fee_msat/1000, 3)).save()
                            if hop_count == 1:
                                new_payment.chan_out = hop.chan_id
                                new_payment.chan_out_alias = alias
                                new_payment.save()
                            if hop_count == total_hops and 5482373484 in hop.custom_records:
                                records = hop.custom_records
                                message = records[34349334].decode('utf-8', errors='ignore')[:200] if 34349334 in records else None
                                new_payment.keysend_preimage = records[5482373484].hex()
                                new_payment.message = message
                                new_payment.save()
                        break
        except:
            #Error inserting, try to update instead
            db_payment = Payments.objects.filter(payment_hash=payment.payment_hash)[0]
            db_payment.creation_date = datetime.fromtimestamp(payment.creation_date)
            db_payment.value = round(payment.value_msat/1000, 3)
            db_payment.fee = round(payment.fee_msat/1000, 3)
            db_payment.status = payment.status
            db_payment.index = payment.payment_index
            db_payment.save()
            if payment.status == 2:
                for attempt in payment.htlcs:
                    if attempt.status == 1:
                        hops = attempt.route.hops
                        hop_count = 0
                        total_hops = len(hops)
                        for hop in hops:
                            hop_count += 1
                            alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=hop.pub_key)).node.alias
                            PaymentHops(payment_hash=db_payment, attempt_id=attempt.attempt_id, step=hop_count, chan_id=hop.chan_id, alias=alias, chan_capacity=hop.chan_capacity, node_pubkey=hop.pub_key, amt=round(hop.amt_to_forward_msat/1000, 3), fee=round(hop.fee_msat/1000, 3)).save()
                            if hop_count == 1:
                                db_payment.chan_out = hop.chan_id
                                db_payment.chan_out_alias = alias
                                db_payment.save()
                            if hop_count == total_hops and 5482373484 in hop.custom_records:
                                records = hop.custom_records
                                message = records[34349334].decode('utf-8', errors='ignore')[:200] if 34349334 in records else None
                                db_payment.keysend_preimage = records[5482373484].hex()
                                db_payment.message = message
                                db_payment.save()
                        break

def update_invoices(stub):
    #Remove anything open so we can get most up to date status
    Invoices.objects.filter(state=0).delete()
    records = Invoices.objects.count()
    invoices = stub.ListInvoices(ln.ListInvoiceRequest(index_offset=records, num_max_invoices=100)).invoices
    for invoice in invoices:
        if invoice.state == 1:
            alias = Channels.objects.filter(chan_id=invoice.htlcs[0].chan_id)[0].alias
            records = invoice.htlcs[0].custom_records
            keysend_preimage = records[5482373484].hex() if 5482373484 in records else None
            message = records[34349334].decode('utf-8', errors='ignore')[:200] if 34349334 in records else None
            Invoices(creation_date=datetime.fromtimestamp(invoice.creation_date), settle_date=datetime.fromtimestamp(invoice.settle_date), r_hash=invoice.r_hash.hex(), value=round(invoice.value_msat/1000, 3), amt_paid=invoice.amt_paid_sat, state=invoice.state, chan_in=invoice.htlcs[0].chan_id, chan_in_alias=alias, keysend_preimage=keysend_preimage, message=message).save()
        else:
            Invoices(creation_date=datetime.fromtimestamp(invoice.creation_date), settle_date=datetime.fromtimestamp(invoice.settle_date), r_hash=invoice.r_hash.hex(), value=round(invoice.value_msat/1000, 3), amt_paid=invoice.amt_paid_sat, state=invoice.state).save()

def update_forwards(stub):
    records = Forwards.objects.count()
    forwards = stub.ForwardingHistory(ln.ForwardingHistoryRequest(start_time=1420070400, index_offset=records, num_max_events=100)).forwarding_events
    for forward in forwards:
        incoming_peer_alias = Channels.objects.filter(chan_id=forward.chan_id_in)[0].alias
        outgoing_peer_alias = Channels.objects.filter(chan_id=forward.chan_id_out)[0].alias
        Forwards(forward_date=datetime.fromtimestamp(forward.timestamp), chan_id_in=forward.chan_id_in, chan_id_out=forward.chan_id_out, chan_in_alias=incoming_peer_alias, chan_out_alias=outgoing_peer_alias, amt_in_msat=forward.amt_in_msat, amt_out_msat=forward.amt_out_msat, fee=round(forward.fee_msat/1000, 3)).save()

def update_channels(stub):
    counter = 0
    chan_list = []
    channels = stub.ListChannels(ln.ListChannelsRequest()).channels
    for channel in channels:
        exists = 1 if Channels.objects.filter(chan_id=channel.chan_id).count() == 1 else 0
        if exists == 1:
            #Update the channel record with the most current data
            chan_data = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=channel.chan_id))
            policy = chan_data.node2_policy if chan_data.node1_pub == channel.remote_pubkey else chan_data.node1_policy
            db_channel = Channels.objects.filter(chan_id=channel.chan_id)[0]
            db_channel.capacity = channel.capacity
            db_channel.local_balance = channel.local_balance
            db_channel.remote_balance = channel.remote_balance
            db_channel.unsettled_balance = channel.unsettled_balance
            db_channel.base_fee = policy.fee_base_msat
            db_channel.fee_rate = policy.fee_rate_milli_msat
            db_channel.is_active = channel.active
            db_channel.is_open = True
            db_channel.save()
        elif exists == 0:
            #Create a record for this new channel
            alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=channel.remote_pubkey)).node.alias
            chan_data = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=channel.chan_id))
            policy = chan_data.node2_policy if chan_data.node1_pub == channel.remote_pubkey else chan_data.node1_policy
            channel_point = channel.channel_point
            txid, index = channel_point.split(':')
            Channels(remote_pubkey=channel.remote_pubkey, chan_id=channel.chan_id, funding_txid=txid, output_index=index, capacity=channel.capacity, local_balance=channel.local_balance, remote_balance=channel.remote_balance, unsettled_balance=channel.unsettled_balance, initiator=channel.initiator, alias=alias, base_fee=policy.fee_base_msat, fee_rate=policy.fee_rate_milli_msat, is_active=channel.active, is_open=True).save()
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

def update_peers(stub):
    counter = 0
    peer_list = []
    peers = stub.ListPeers(ln.ListPeersRequest(latest_error=True)).peers
    for peer in peers:
        exists = 1 if Peers.objects.filter(pubkey=peer.pub_key).count() == 1 else 0
        if exists == 1:
            db_peer = Peers.objects.filter(pubkey=peer.pub_key)[0]
            db_peer.pubkey = peer.pub_key
            db_peer.address = peer.address
            db_peer.sat_sent = peer.sat_sent
            db_peer.sat_recv = peer.sat_recv
            db_peer.inbound = peer.inbound
            db_peer.connected = True
            db_peer.save()
        elif exists == 0:
            Peers(pubkey = peer.pub_key, address = peer.address, sat_sent = peer.sat_sent, sat_recv = peer.sat_recv, inbound = peer.inbound, connected = True).save()
        counter += 1
        peer_list.append(peer.pub_key)
    records = Peers.objects.filter(connected=True).count()
    if records > counter:
        disconnected = Peers.objects.filter(connected=True).exclude(pubkey__in=peer_list)
        for peer in disconnected:
            peer.connected = False
            peer.save()

def reconnect_peers(stub):
    inactive_peers = Channels.objects.filter(is_open=True, is_active=False).values_list('remote_pubkey', flat=True).distinct()
    if len(inactive_peers) > 0:
        peers = Peers.objects.all()
        for inactive_peer in inactive_peers:
            if peers.filter(pubkey=inactive_peer).exists():
                peer = peers.filter(pubkey=inactive_peer)[0] 
                if peer.last_reconnected == None or (int((datetime.now() - peer.last_reconnected).total_seconds() / 60) > 2):
                    if peer.connected == True:
                        print('Inactive channel is still connected to peer, disconnecting peer...')
                        stub.DisconnectPeer(ln.DisconnectPeerRequest(pub_key=inactive_peer))
                        peer.connected = False
                        peer.save()
                    print('Attempting connection to:', inactive_peer)
                    node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=inactive_peer, include_channels=False)).node
                    host = node.addresses[-1].addr
                    host = node.addresses[0].addr if host[0] == '[' else host
                    address = ln.LightningAddress(pubkey=inactive_peer, host=host)
                    stub.ConnectPeer(request = ln.ConnectPeerRequest(addr=address, perm=True, timeout=5))
                    peer.last_reconnected = datetime.now()
                    peer.save()

def lnd_connect():
    #Open connection with lnd via grpc
    with open(os.path.expanduser(settings.LND_DIR_PATH + '/data/chain/bitcoin/mainnet/admin.macaroon'), 'rb') as f:
        macaroon_bytes = f.read()
        macaroon = codecs.encode(macaroon_bytes, 'hex')
    def metadata_callback(context, callback):
        callback([('macaroon', macaroon)], None)
    os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'
    cert = open(os.path.expanduser(settings.LND_DIR_PATH + '/tls.cert'), 'rb').read()
    cert_creds = grpc.ssl_channel_credentials(cert)
    auth_creds = grpc.metadata_call_credentials(metadata_callback)
    creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
    channel = grpc.secure_channel('localhost:10009', creds)
    return channel

def main():
    stub = lnrpc.LightningStub(lnd_connect())
    #Update data
    update_channels(stub)
    update_peers(stub)
    update_payments(stub)
    update_invoices(stub)
    update_forwards(stub)
    reconnect_peers(stub)

if __name__ == '__main__':
    main()