import django
from django.db.models import Max
from datetime import datetime, timedelta
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import signer_pb2 as lns
from gui.lnd_deps import signer_pb2_grpc as lnsigner
from gui.lnd_deps.lnd_connect import lnd_connect
from lndg import settings
from os import environ
environ['DJANGO_SETTINGS_MODULE'] = 'lndg.settings'
django.setup()
from gui.models import Payments, PaymentHops, Invoices, Forwards, Channels, Peers, Onchain, Closures, Resolutions, PendingHTLCs, LocalSettings

def update_payments(stub):
    #Remove anything in-flight so we can get most up to date status
    Payments.objects.filter(status=1).delete()
    #Get the number of records in the database currently
    last_index = 0 if Payments.objects.aggregate(Max('index'))['index__max'] == None else Payments.objects.aggregate(Max('index'))['index__max']
    payments = stub.ListPayments(ln.ListPaymentsRequest(include_incomplete=True, index_offset=last_index, max_payments=100)).payments
    self_pubkey = stub.GetInfo(ln.GetInfoRequest()).identity_pubkey
    for payment in payments:
        try:
            new_payment = Payments(creation_date=datetime.fromtimestamp(payment.creation_date), payment_hash=payment.payment_hash, value=round(payment.value_msat/1000, 3), fee=round(payment.fee_msat/1000, 3), status=payment.status, index=payment.payment_index)
            new_payment.save()
            if payment.status == 2:
                for attempt in payment.htlcs:
                    if attempt.status == 1:
                        hops = attempt.route.hops
                        hop_count = 0
                        cost_to = 0
                        total_hops = len(hops)
                        for hop in hops:
                            hop_count += 1
                            try:
                                alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=hop.pub_key, include_channels=False)).node.alias
                            except:
                                alias = ''
                            fee = hop.fee_msat/1000
                            PaymentHops(payment_hash=new_payment, attempt_id=attempt.attempt_id, step=hop_count, chan_id=hop.chan_id, alias=alias, chan_capacity=hop.chan_capacity, node_pubkey=hop.pub_key, amt=round(hop.amt_to_forward_msat/1000, 3), fee=round(fee, 3), cost_to=round(cost_to, 3)).save()
                            cost_to += fee
                            if hop_count == 1:
                                new_payment.chan_out = hop.chan_id
                                new_payment.chan_out_alias = alias
                            if hop_count == total_hops and 5482373484 in hop.custom_records:
                                records = hop.custom_records
                                message = records[34349334].decode('utf-8', errors='ignore')[:1000] if 34349334 in records else None
                                new_payment.keysend_preimage = records[5482373484].hex()
                                new_payment.message = message
                            if hop_count == total_hops and hop.pub_key == self_pubkey:
                                new_payment.rebal_chan = hop.chan_id
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
                        PaymentHops.objects.filter(payment_hash=db_payment).delete()
                        hops = attempt.route.hops
                        hop_count = 0
                        cost_to = 0
                        total_hops = len(hops)
                        for hop in hops:
                            hop_count += 1
                            try:
                                alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=hop.pub_key, include_channels=False)).node.alias
                            except:
                                alias = ''
                            fee = hop.fee_msat/1000
                            PaymentHops(payment_hash=db_payment, attempt_id=attempt.attempt_id, step=hop_count, chan_id=hop.chan_id, alias=alias, chan_capacity=hop.chan_capacity, node_pubkey=hop.pub_key, amt=round(hop.amt_to_forward_msat/1000, 3), fee=round(fee, 3), cost_to=round(cost_to, 3)).save()
                            cost_to += fee
                            if hop_count == 1:
                                db_payment.chan_out = hop.chan_id
                                db_payment.chan_out_alias = alias
                                db_payment.save()
                            if hop_count == total_hops and 5482373484 in hop.custom_records:
                                records = hop.custom_records
                                message = records[34349334].decode('utf-8', errors='ignore')[:1000] if 34349334 in records else None
                                db_payment.keysend_preimage = records[5482373484].hex()
                                db_payment.message = message
                                db_payment.save()
                        break

def update_invoices(stub):
    #Remove anything open so we can get most up to date status
    Invoices.objects.filter(state=0).delete()
    last_index = 0 if Invoices.objects.aggregate(Max('index'))['index__max'] == None else Invoices.objects.aggregate(Max('index'))['index__max']
    invoices = stub.ListInvoices(ln.ListInvoiceRequest(index_offset=last_index, num_max_invoices=100)).invoices
    for invoice in invoices:
        if invoice.state == 1:
            if len(invoice.htlcs) > 0:
                chan_in_id = invoice.htlcs[0].chan_id
                alias = Channels.objects.filter(chan_id=chan_in_id)[0].alias if Channels.objects.filter(chan_id=chan_in_id).exists() else None
                records = invoice.htlcs[0].custom_records
                keysend_preimage = records[5482373484].hex() if 5482373484 in records else None
                message = records[34349334].decode('utf-8', errors='ignore')[:1000] if 34349334 in records else None
                if 34349337 in records and 34349339 in records and 34349343 in records and 34349334 in records:
                    signerstub = lnsigner.SignerStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                    self_pubkey = stub.GetInfo(ln.GetInfoRequest()).identity_pubkey
                    try:
                        valid = signerstub.VerifyMessage(lns.VerifyMessageReq(msg=(records[34349339]+bytes.fromhex(self_pubkey)+records[34349343]+records[34349334]), signature=records[34349337], pubkey=records[34349339])).valid
                    except:
                        print('Unable to validate signature on invoice: ' + invoice.r_hash.hex())
                        valid = False
                    sender = records[34349339].hex() if valid == True else None
                    try:
                        sender_alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=sender, include_channels=False)).node.alias if sender != None else None
                    except:
                        sender_alias = None
                else:
                    sender = None
                    sender_alias = None
            else:
                chan_in_id = None
                alias = None
                keysend_preimage = None
                message = None
                sender = None
                sender_alias = None
            Invoices(creation_date=datetime.fromtimestamp(invoice.creation_date), settle_date=datetime.fromtimestamp(invoice.settle_date), r_hash=invoice.r_hash.hex(), value=round(invoice.value_msat/1000, 3), amt_paid=invoice.amt_paid_sat, state=invoice.state, chan_in=chan_in_id, chan_in_alias=alias, keysend_preimage=keysend_preimage, message=message, sender=sender, sender_alias=sender_alias, index=invoice.add_index).save()
        else:
            Invoices(creation_date=datetime.fromtimestamp(invoice.creation_date), r_hash=invoice.r_hash.hex(), value=round(invoice.value_msat/1000, 3), amt_paid=invoice.amt_paid_sat, state=invoice.state, index=invoice.add_index).save()

def update_forwards(stub):
    records = Forwards.objects.count()
    forwards = stub.ForwardingHistory(ln.ForwardingHistoryRequest(start_time=1420070400, index_offset=records, num_max_events=100)).forwarding_events
    for forward in forwards:
        incoming_peer_alias = Channels.objects.filter(chan_id=forward.chan_id_in)[0].alias if Channels.objects.filter(chan_id=forward.chan_id_in).exists() else None
        outgoing_peer_alias = Channels.objects.filter(chan_id=forward.chan_id_out)[0].alias if Channels.objects.filter(chan_id=forward.chan_id_out).exists() else None
        Forwards(forward_date=datetime.fromtimestamp(forward.timestamp), chan_id_in=forward.chan_id_in, chan_id_out=forward.chan_id_out, chan_in_alias=incoming_peer_alias, chan_out_alias=outgoing_peer_alias, amt_in_msat=forward.amt_in_msat, amt_out_msat=forward.amt_out_msat, fee=round(forward.fee_msat/1000, 3)).save()

def update_channels(stub):
    counter = 0
    chan_list = []
    channels = stub.ListChannels(ln.ListChannelsRequest()).channels
    PendingHTLCs.objects.all().delete()
    for channel in channels:
        if Channels.objects.filter(chan_id=channel.chan_id).exists():
            #Update the channel record with the most current data
            db_channel = Channels.objects.filter(chan_id=channel.chan_id)[0]
        else:
            #Create a record for this new channel
            try:
                alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=channel.remote_pubkey, include_channels=False)).node.alias
            except:
                alias = ''
            channel_point = channel.channel_point
            txid, index = channel_point.split(':')
            db_channel = Channels()
            db_channel.remote_pubkey = channel.remote_pubkey
            db_channel.chan_id = channel.chan_id
            db_channel.initiator = channel.initiator
            db_channel.alias = alias
            db_channel.funding_txid = txid
            db_channel.output_index = index
            db_channel.capacity = channel.capacity
            db_channel.private = channel.private
        try:
            chan_data = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=channel.chan_id))
            if chan_data.node1_pub == channel.remote_pubkey:
                db_channel.local_base_fee = chan_data.node2_policy.fee_base_msat
                db_channel.local_fee_rate = chan_data.node2_policy.fee_rate_milli_msat
                db_channel.local_disabled = chan_data.node2_policy.disabled
                db_channel.remote_base_fee = chan_data.node1_policy.fee_base_msat
                db_channel.remote_fee_rate = chan_data.node1_policy.fee_rate_milli_msat
                db_channel.remote_disabled = chan_data.node1_policy.disabled
            else:
                db_channel.local_base_fee = chan_data.node1_policy.fee_base_msat
                db_channel.local_fee_rate = chan_data.node1_policy.fee_rate_milli_msat
                db_channel.local_disabled = chan_data.node1_policy.disabled
                db_channel.remote_base_fee = chan_data.node2_policy.fee_base_msat
                db_channel.remote_fee_rate = chan_data.node2_policy.fee_rate_milli_msat
                db_channel.remote_disabled = chan_data.node2_policy.disabled
        except:
            db_channel.local_base_fee = 0
            db_channel.local_fee_rate = 0
            db_channel.local_disabled = False
            db_channel.remote_base_fee = 0
            db_channel.remote_fee_rate = 0
            db_channel.remote_disabled = False
        db_channel.local_balance = channel.local_balance
        db_channel.remote_balance = channel.remote_balance
        db_channel.unsettled_balance = channel.unsettled_balance
        db_channel.local_commit = channel.commit_fee
        db_channel.local_chan_reserve = channel.local_chan_reserve_sat
        db_channel.num_updates = channel.num_updates
        db_channel.last_update = datetime.now() if db_channel.is_active != channel.active else db_channel.last_update
        db_channel.is_active = channel.active
        db_channel.is_open = True
        db_channel.total_sent = channel.total_satoshis_sent
        db_channel.total_received = channel.total_satoshis_received
        pending_out = 0
        pending_in = 0
        htlc_counter = 0
        if len(channel.pending_htlcs) > 0:
            for htlc in channel.pending_htlcs:
                pending_htlc = PendingHTLCs()
                pending_htlc.chan_id = db_channel.chan_id
                pending_htlc.alias = db_channel.alias
                pending_htlc.incoming = htlc.incoming
                pending_htlc.amount = htlc.amount
                pending_htlc.hash_lock = htlc.hash_lock.hex()
                pending_htlc.expiration_height = htlc.expiration_height
                pending_htlc.forwarding_channel = htlc.forwarding_channel
                pending_htlc.forwarding_alias = Channels.objects.filter(chan_id=htlc.forwarding_channel)[0].alias if Channels.objects.filter(chan_id=htlc.forwarding_channel).exists() else '---'
                pending_htlc.save()
                if htlc.incoming == True:
                    pending_in += htlc.amount
                else:
                    pending_out += htlc.amount
                htlc_counter += 1
        db_channel.pending_outbound = pending_out
        db_channel.pending_inbound = pending_in
        db_channel.htlc_count = htlc_counter
        db_channel.save()
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
            if db_peer.connected == False:
                try:
                    db_peer.alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer.pub_key, include_channels=False)).node.alias
                except:
                    db_peer.alias = ''
            db_peer.connected = True
            db_peer.save()
        elif exists == 0:
            try:
                alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer.pub_key, include_channels=False)).node.alias
            except:
                alias = ''
            Peers(pubkey = peer.pub_key, address = peer.address, sat_sent = peer.sat_sent, sat_recv = peer.sat_recv, inbound = peer.inbound, alias=alias, connected = True).save()
        counter += 1
        peer_list.append(peer.pub_key)
    records = Peers.objects.filter(connected=True).count()
    if records > counter:
        disconnected = Peers.objects.filter(connected=True).exclude(pubkey__in=peer_list)
        for peer in disconnected:
            peer.connected = False
            peer.save()

def update_onchain(stub):
    Onchain.objects.filter(block_height=0).delete()
    last_block = 0 if Onchain.objects.aggregate(Max('block_height'))['block_height__max'] == None else Onchain.objects.aggregate(Max('block_height'))['block_height__max'] + 1
    onchain_txs = stub.GetTransactions(ln.GetTransactionsRequest(start_height=last_block)).transactions
    for tx in onchain_txs:
        Onchain(tx_hash=tx.tx_hash, time_stamp=datetime.fromtimestamp(tx.time_stamp), amount=tx.amount, fee=tx.total_fees, block_hash=tx.block_hash, block_height=tx.block_height, label=tx.label[:100]).save()

def update_closures(stub):
    closures = stub.ClosedChannels(ln.ClosedChannelsRequest()).channels
    if len(closures) > Closures.objects.all().count():
        counter = 0
        skip = Closures.objects.all().count()
        for closure in closures:
            counter += 1
            if counter > skip:
                resolution_count = len(closure.resolutions)
                db_closure = Closures(chan_id=closure.chan_id, closing_tx=closure.closing_tx_hash, remote_pubkey=closure.remote_pubkey, capacity=closure.capacity, close_height=closure.close_height, settled_balance=closure.settled_balance, time_locked_balance=closure.time_locked_balance, close_type=closure.close_type, open_initiator=closure.open_initiator, close_initiator=closure.close_initiator, resolution_count=resolution_count)
                db_closure.save()
                if resolution_count > 0:
                    Resolutions.objects.filter(chan_id=closure.chan_id).delete()
                    for resolution in closure.resolutions:
                        Resolutions(chan_id=db_closure, resolution_type=resolution.resolution_type, outcome=resolution.outcome, outpoint_tx=resolution.outpoint.txid_str, outpoint_index=resolution.outpoint.output_index, amount_sat=resolution.amount_sat, sweep_txid=resolution.sweep_txid).save()

def reconnect_peers(stub):
    inactive_peers = Channels.objects.filter(is_open=True, is_active=False, private=False).values_list('remote_pubkey', flat=True).distinct()
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
                    try:
                        node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=inactive_peer, include_channels=False)).node
                        host = node.addresses[0].addr
                    except:
                        print('Unable to find node info on graph, using last known value')
                        host = peer.address
                    address = ln.LightningAddress(pubkey=inactive_peer, host=host)
                    stub.ConnectPeer(request = ln.ConnectPeerRequest(addr=address, perm=True, timeout=5))
                    peer.last_reconnected = datetime.now()
                    peer.save()

def clean_payments(stub):
    if LocalSettings.objects.filter(key='LND-CleanPayments').exists():
        enabled = int(LocalSettings.objects.filter(key='LND-CleanPayments')[0].value)
    else:
        LocalSettings(key='LND-CleanPayments', value='0').save()
        LocalSettings(key='LND-RetentionDays', value='30').save()
        enabled = 0
    if enabled == 1:
        if LocalSettings.objects.filter(key='LND-RetentionDays').exists():
            retention_days = int(LocalSettings.objects.filter(key='LND-RetentionDays')[0].value)
        else:
            LocalSettings(key='LND-RetentionDays', value='30').save()
            retention_days = 30
        time_filter = datetime.now() - timedelta(days=retention_days)
        target_payments = Payments.objects.exclude(status=1).filter(cleaned=False).filter(creation_date__lte=time_filter).order_by('index')[:10]
        for payment in target_payments:
            payment_hash = bytes.fromhex(payment.payment_hash)
            htlcs_only = True if payment.status == 2 else False
            try:
                stub.DeletePayment(ln.DeletePaymentRequest(payment_hash=payment_hash, failed_htlcs_only=htlcs_only))
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                print('Error occured when cleaning payment: ' + payment.payment_hash)
                print('Error: ' + error_msg)
            finally:
                payment.cleaned = True
                payment.save()

def main():
    try:
        stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        #Update data
        update_channels(stub)
        update_peers(stub)
        update_invoices(stub)
        update_payments(stub)
        update_forwards(stub)
        update_onchain(stub)
        update_closures(stub)
        reconnect_peers(stub)
        clean_payments(stub)
    except Exception as e:
        print('Error processing background data: ' + str(e))

if __name__ == '__main__':
    main()
