import django
from django.db.models import Max, Min
from datetime import datetime, timedelta
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import signer_pb2 as lns
from gui.lnd_deps import signer_pb2_grpc as lnsigner
from gui.lnd_deps.lnd_connect import lnd_connect
from lndg import settings
from os import environ
from pandas import DataFrame
from requests import get
environ['DJANGO_SETTINGS_MODULE'] = 'lndg.settings'
django.setup()
from gui.models import Payments, PaymentHops, Invoices, Forwards, Channels, Peers, Onchain, Closures, Resolutions, PendingHTLCs, LocalSettings, FailedHTLCs, Autofees, PendingChannels
from lndg.settings import LND_NETWORK

def update_payments(stub):
    #Remove anything in-flight so we can get most up to date status
    #in_flight_index = Payments.objects.filter(status=1).aggregate(Min('index'))['index__min'] if Payments.objects.filter(status=1).exists() else 0
    self_pubkey = stub.GetInfo(ln.GetInfoRequest()).identity_pubkey
    inflight_payments = Payments.objects.filter(status=1).order_by('index')
    for payment in inflight_payments:
        payment = stub.ListPayments(ln.ListPaymentsRequest(include_incomplete=True, index_offset=payment.index, max_payments=1)).payments
        update_payment(stub, payment, self_pubkey)
    #Get the number of records in the database currently
    last_index = Payments.objects.exclude(status=1).aggregate(Max('index'))['index__max'] if Payments.objects.exists() else 0
    #print (f"{datetime.now().strftime('%c')} : {in_flight_index=} {last_index=} {min(in_flight_index - 1, last_index) if in_flight_index > 0 else last_index=}")
    #We delete all inflight index in each cycle to we should start with one less so that inflight payment with index=in_flight_index comes back.
    #last_index = min(in_flight_index - 1, last_index) if in_flight_index > 0 else last_index
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
                                if new_payment.chan_out is None:
                                    new_payment.chan_out = hop.chan_id
                                    new_payment.chan_out_alias = alias
                                else:
                                    new_payment.chan_out = 'MPP'
                                    new_payment.chan_out_alias = 'MPP'
                            if hop_count == total_hops and 5482373484 in hop.custom_records and new_payment.keysend_preimage is None:
                                records = hop.custom_records
                                message = records[34349334].decode('utf-8', errors='ignore')[:1000] if 34349334 in records else None
                                new_payment.keysend_preimage = records[5482373484].hex()
                                new_payment.message = message
                            if hop_count == total_hops and hop.pub_key == self_pubkey and new_payment.rebal_chan is None:
                                new_payment.rebal_chan = hop.chan_id
                        new_payment.save()
        except:
            #Error inserting, try to update instead
            update_payment(stub, payment, self_pubkey)

def update_payment(stub, payment, self_pubkey):
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
                        if db_payment.chan_out is None:
                            db_payment.chan_out = hop.chan_id
                            db_payment.chan_out_alias = alias
                        else:
                            db_payment.chan_out = 'MPP'
                            db_payment.chan_out_alias = 'MPP'
                    if hop_count == total_hops and 5482373484 in hop.custom_records and db_payment.keysend_preimage is None:
                        records = hop.custom_records
                        message = records[34349334].decode('utf-8', errors='ignore')[:1000] if 34349334 in records else None
                        db_payment.keysend_preimage = records[5482373484].hex()
                        db_payment.message = message
                    if hop_count == total_hops and hop.pub_key == self_pubkey and db_payment.rebal_chan is None:
                        db_payment.rebal_chan = hop.chan_id
                db_payment.save()

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
        incoming_peer_alias = Channels.objects.filter(chan_id=forward.chan_id_in)[0].remote_pubkey[:12] if incoming_peer_alias == '' else incoming_peer_alias
        outgoing_peer_alias = Channels.objects.filter(chan_id=forward.chan_id_out)[0].alias if Channels.objects.filter(chan_id=forward.chan_id_out).exists() else None
        outgoing_peer_alias = Channels.objects.filter(chan_id=forward.chan_id_out)[0].remote_pubkey[:12] if outgoing_peer_alias == '' else outgoing_peer_alias
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
            pending_channel = None
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
            pending_channel = PendingChannels.objects.filter(funding_txid=txid, output_index=index)[0] if PendingChannels.objects.filter(funding_txid=txid, output_index=index).exists() else None
        try:
            chan_data = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=channel.chan_id))
            if chan_data.node1_pub == channel.remote_pubkey:
                db_channel.local_base_fee = chan_data.node2_policy.fee_base_msat
                db_channel.local_fee_rate = chan_data.node2_policy.fee_rate_milli_msat
                db_channel.local_disabled = chan_data.node2_policy.disabled
                db_channel.local_cltv = chan_data.node2_policy.time_lock_delta
                db_channel.remote_base_fee = chan_data.node1_policy.fee_base_msat
                db_channel.remote_fee_rate = chan_data.node1_policy.fee_rate_milli_msat
                db_channel.remote_disabled = chan_data.node1_policy.disabled
                db_channel.remote_cltv = chan_data.node1_policy.time_lock_delta
            else:
                db_channel.local_base_fee = chan_data.node1_policy.fee_base_msat
                db_channel.local_fee_rate = chan_data.node1_policy.fee_rate_milli_msat
                db_channel.local_disabled = chan_data.node1_policy.disabled
                db_channel.local_cltv = chan_data.node1_policy.time_lock_delta
                db_channel.remote_base_fee = chan_data.node2_policy.fee_base_msat
                db_channel.remote_fee_rate = chan_data.node2_policy.fee_rate_milli_msat
                db_channel.remote_disabled = chan_data.node2_policy.disabled
                db_channel.remote_cltv = chan_data.node2_policy.time_lock_delta
        except:
            db_channel.local_base_fee = 0
            db_channel.local_fee_rate = 0
            db_channel.local_disabled = False
            db_channel.local_cltv = 40
            db_channel.remote_base_fee = 0
            db_channel.remote_fee_rate = 0
            db_channel.remote_disabled = False
            db_channel.remote_cltv = 40
        db_channel.local_balance = channel.local_balance
        db_channel.remote_balance = channel.remote_balance
        db_channel.unsettled_balance = channel.unsettled_balance
        db_channel.local_commit = channel.commit_fee
        db_channel.local_chan_reserve = channel.local_chan_reserve_sat
        db_channel.num_updates = channel.num_updates
        if db_channel.is_active != channel.active:
            db_channel.last_update = datetime.now()
            peer_alias = Peers.objects.filter(pubkey=db_channel.remote_pubkey)[0].alias if Peers.objects.filter(pubkey=db_channel.remote_pubkey).exists() else None
            db_channel.alias = '' if peer_alias is None else peer_alias
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
        if pending_channel:
            if pending_channel.local_base_fee or pending_channel.local_fee_rate or pending_channel.local_cltv:
                base_fee = pending_channel.local_base_fee if pending_channel.local_base_fee else db_channel.local_base_fee
                fee_rate = pending_channel.local_fee_rate if pending_channel.local_fee_rate else db_channel.local_fee_rate
                cltv = pending_channel.local_cltv if pending_channel.local_cltv else db_channel.local_cltv
                channel_point = ln.ChannelPoint()
                channel_point.funding_txid_bytes = bytes.fromhex(db_channel.funding_txid)
                channel_point.funding_txid_str = db_channel.funding_txid
                channel_point.output_index = int(db_channel.output_index)
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=base_fee, fee_rate=(fee_rate/1000000), time_lock_delta=cltv))
                db_channel.local_base_fee = base_fee
                db_channel.local_fee_rate = fee_rate
                db_channel.local_cltv = cltv
                db_channel.fees_updated = datetime.now()
            if pending_channel.auto_rebalance:
                db_channel.auto_rebalance = pending_channel.auto_rebalance
            if pending_channel.ar_amt_target:
                db_channel.ar_amt_target = pending_channel.ar_amt_target
            if pending_channel.ar_in_target:
                db_channel.ar_in_target = pending_channel.ar_in_target
            if pending_channel.ar_out_target:
                db_channel.ar_out_target = pending_channel.ar_out_target
            if pending_channel.ar_max_cost:
                db_channel.ar_max_cost = pending_channel.ar_max_cost
            if pending_channel.auto_fees:
                db_channel.auto_fees = pending_channel.auto_fees
            pending_channel.delete()
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

def network_links():
    if LocalSettings.objects.filter(key='GUI-NetLinks').exists():
        network_links = str(LocalSettings.objects.filter(key='GUI-NetLinks')[0].value)
    else:
        LocalSettings(key='GUI-NetLinks', value='https://mempool.space').save()
        network_links = 'https://mempool.space'
    return network_links

def get_tx_fees(txid):
    base_url = network_links() + ('/testnet' if LND_NETWORK == 'testnet' else '') + '/api/tx/'
    try:
        request_data = get(base_url + txid).json()
        fee = request_data['fee']
    except Exception as e:
        print('Error getting closure fees for ', txid, ':', str(e))
        fee = 0
    return fee

def update_closures(stub):
    closures = stub.ClosedChannels(ln.ClosedChannelsRequest()).channels
    if len(closures) > Closures.objects.all().count():
        counter = 0
        skip = Closures.objects.all().count()
        for closure in closures:
            counter += 1
            if counter > skip:
                channel = Channels.objects.filter(chan_id=closure.chan_id)[0] if Channels.objects.filter(chan_id=closure.chan_id).exists() else None
                resolution_count = len(closure.resolutions)
                txid, index = closure.channel_point.split(':')
                closing_costs = get_tx_fees(txid) if closure.open_initiator == 1 else 0
                db_closure = Closures(chan_id=closure.chan_id, funding_txid=txid, funding_index=index, closing_tx=closure.closing_tx_hash, remote_pubkey=closure.remote_pubkey, capacity=closure.capacity, close_height=closure.close_height, settled_balance=closure.settled_balance, time_locked_balance=closure.time_locked_balance, close_type=closure.close_type, open_initiator=closure.open_initiator, close_initiator=closure.close_initiator, resolution_count=resolution_count)
                try:
                    db_closure.save()
                except Exception as e:
                    print('Error inserting closure:', str(e))
                    Closures.objects.filter(funding_txid=txid,funding_index=index).delete()
                    return
                if resolution_count > 0:
                    Resolutions.objects.filter(chan_id=closure.chan_id).delete()
                    for resolution in closure.resolutions:
                        if resolution.resolution_type != 2:
                            closing_costs += get_tx_fees(resolution.sweep_txid)
                        Resolutions(chan_id=closure.chan_id, resolution_type=resolution.resolution_type, outcome=resolution.outcome, outpoint_tx=resolution.outpoint.txid_str, outpoint_index=resolution.outpoint.output_index, amount_sat=resolution.amount_sat, sweep_txid=resolution.sweep_txid).save()
                if channel:
                    channel.closing_costs = closing_costs
                    channel.save()

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
                    try:
                        stub.ConnectPeer(request = ln.ConnectPeerRequest(addr=address, perm=True, timeout=5))
                        peer.last_reconnected = datetime.now()
                        peer.save()
                    except Exception as e:
                        error = str(e)
                        details_index = error.find('details =') + 11
                        debug_error_index = error.find('debug_error_string =') - 3
                        error_msg = error[details_index:debug_error_index]
                        print (f"{datetime.now().strftime('%c')} : Error reconnecting {inactive_peer=} {error_msg=}")

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
                print (f"{datetime.now().strftime('%c')} : Error {payment.index=} {payment.status=} {payment.payment_hash=} {error_msg=}")
            finally:
                payment.cleaned = True
                payment.save()
                print (f"{datetime.now().strftime('%c')} : Cleaned {payment.index=} {payment.status=} {payment.cleaned=} {payment.payment_hash=}")

def auto_fees(stub):
    if LocalSettings.objects.filter(key='AF-Enabled').exists():
        enabled = int(LocalSettings.objects.filter(key='AF-Enabled')[0].value)
    else:
        LocalSettings(key='AF-Enabled', value='0').save()
        enabled = 0
    if enabled == 1:
        filter_1day = datetime.now() - timedelta(days=1)
        filter_7day = datetime.now() - timedelta(days=7)
        channels = Channels.objects.filter(is_open=True, is_active=True, private=False, auto_fees=True)
        channels_df = DataFrame.from_records(channels.values())
        if channels_df.shape[0] > 0:
            if LocalSettings.objects.filter(key='AF-MaxRate').exists():
                max_rate = int(LocalSettings.objects.filter(key='AF-MaxRate')[0].value)
            else:
                LocalSettings(key='AF-MaxRate', value='2500').save()
                max_rate = 2500
            if LocalSettings.objects.filter(key='AF-MinRate').exists():
                min_rate = int(LocalSettings.objects.filter(key='AF-MinRate')[0].value)
            else:
                LocalSettings(key='AF-MinRate', value='0').save()
                min_rate = 0
            if LocalSettings.objects.filter(key='AF-Increment').exists():
                increment = int(LocalSettings.objects.filter(key='AF-Increment')[0].value)
            else:
                LocalSettings(key='AF-Increment', value='5').save()
                increment = 5
            if LocalSettings.objects.filter(key='AF-Multiplier').exists():
                multiplier = int(LocalSettings.objects.filter(key='AF-Multiplier')[0].value)
            else:
                LocalSettings(key='AF-Multiplier', value='5').save()
                multiplier = 5
            if LocalSettings.objects.filter(key='AF-FailedHTLCs').exists():
                failed_htlc_limit = int(LocalSettings.objects.filter(key='AF-FailedHTLCs')[0].value)
            else:
                LocalSettings(key='AF-FailedHTLCs', value='25').save()
                failed_htlc_limit = 25
            channels_df['eligible'] = channels_df.apply(lambda row: (datetime.now()-row['fees_updated']).total_seconds() > 86400, axis=1)
            channels_df = channels_df[channels_df['eligible']==True]
            if channels_df.shape[0] > 0:
                failed_htlc_df = DataFrame.from_records(FailedHTLCs.objects.filter(timestamp__gte=filter_1day).order_by('-id').values())
                if failed_htlc_df.shape[0] > 0:
                    failed_htlc_df = failed_htlc_df[(failed_htlc_df['wire_failure']==15) & (failed_htlc_df['failure_detail']==6) & (failed_htlc_df['amount']>failed_htlc_df['chan_out_liq']+failed_htlc_df['chan_out_pending'])]
                forwards = Forwards.objects.filter(forward_date__gte=filter_7day, amt_out_msat__gte=1000000)
                forwards_df_7d = DataFrame.from_records(forwards.values())
                forwards_df_in_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_in', as_index=True).sum()
                forwards_df_out_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_out', as_index=True).sum()
                channels_df['local_balance'] = channels_df.apply(lambda row: row.local_balance + row.pending_outbound, axis=1)
                channels_df['remote_balance'] = channels_df.apply(lambda row: row.remote_balance + row.pending_inbound, axis=1)
                channels_df['in_percent'] = channels_df.apply(lambda row: int(round((row['remote_balance']/row['capacity'])*100, 0)), axis=1)
                channels_df['out_percent'] = channels_df.apply(lambda row: int(round((row['local_balance']/row['capacity'])*100, 0)), axis=1)
                channels_df['amt_routed_in_7day'] = channels_df.apply(lambda row: int(forwards_df_in_7d_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_in_7d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_routed_out_7day'] = channels_df.apply(lambda row: int(forwards_df_out_7d_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_out_7d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['net_routed_7day'] = channels_df.apply(lambda row: round((row['amt_routed_out_7day']-row['amt_routed_in_7day'])/row['capacity'], 1), axis=1)
                channels_df['revenue_7day'] = channels_df.apply(lambda row: int(forwards_df_out_7d_sum.loc[row.chan_id].fee) if forwards_df_out_7d_sum.empty == False and (forwards_df_out_7d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['revenue_assist_7day'] = channels_df.apply(lambda row: int(forwards_df_in_7d_sum.loc[row.chan_id].fee) if forwards_df_in_7d_sum.empty == False and (forwards_df_in_7d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['out_rate'] = channels_df.apply(lambda row: int((row['revenue_7day']/row['amt_routed_out_7day'])*1000000) if row['amt_routed_out_7day'] > 0 else 0, axis=1)
                channels_df['failed_out_1day'] = 0 if failed_htlc_df.empty else channels_df.apply(lambda row: len(failed_htlc_df[failed_htlc_df['chan_id_out']==row.chan_id]), axis=1)
                payments = Payments.objects.filter(status=2).filter(creation_date__gte=filter_7day).filter(rebal_chan__isnull=False)
                invoices = Invoices.objects.filter(state=1).filter(settle_date__gte=filter_7day).filter(r_hash__in=payments.values_list('payment_hash'))
                payments_df_7d = DataFrame.from_records(payments.filter(creation_date__gte=filter_7day).values())
                invoices_df_7d = DataFrame.from_records(invoices.filter(settle_date__gte=filter_7day).values())
                invoices_df_7d_sum = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).sum()
                invoice_hashes_7d = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True)['r_hash'].apply(list)
                channels_df['amt_rebal_in_7day'] = channels_df.apply(lambda row: int(invoices_df_7d_sum.loc[row.chan_id].amt_paid) if invoices_df_7d_sum.empty == False and (invoices_df_7d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['costs_7day'] = channels_df.apply(lambda row: 0 if row['amt_rebal_in_7day'] == 0 else int(payments_df_7d.set_index('payment_hash', inplace=False).loc[invoice_hashes_7d[row.chan_id] if invoice_hashes_7d.empty == False and (invoice_hashes_7d.index == row.chan_id).any() else []]['fee'].sum()), axis=1)
                channels_df['rebal_ppm'] = channels_df.apply(lambda row: int((row['costs_7day']/row['amt_rebal_in_7day'])*1000000) if row['amt_rebal_in_7day'] > 0 else 0, axis=1)
                channels_df['profit_margin'] = channels_df.apply(lambda row: row['out_rate']*((100-row['ar_max_cost'])/100), axis=1)
                channels_df['max_suggestion'] = channels_df.apply(lambda row: int((row['out_rate']+row['profit_margin'] if row['out_rate'] > 0 else row['local_fee_rate'])*1.15) if row['in_percent'] > 25 else int(row['local_fee_rate']), axis=1)
                channels_df['max_suggestion'] = channels_df.apply(lambda row: row['local_fee_rate']+25 if row['max_suggestion'] > (row['local_fee_rate']+25) or row['max_suggestion'] == 0 else row['max_suggestion'], axis=1)
                channels_df['min_suggestion'] = channels_df.apply(lambda row: int((row['rebal_ppm'] if row['out_rate'] > 0 else row['local_fee_rate'])*0.75) if row['out_percent'] > 25 else int(row['local_fee_rate']), axis=1)
                channels_df['min_suggestion'] = channels_df.apply(lambda row: row['local_fee_rate']-50 if row['min_suggestion'] < (row['local_fee_rate']-50) else row['min_suggestion'], axis=1)
                channels_df['assisted_ratio'] = channels_df.apply(lambda row: round((row['revenue_assist_7day'] if row['revenue_7day'] == 0 else row['revenue_assist_7day']/row['revenue_7day']), 2), axis=1)
                channels_df['adjusted_out_rate'] = channels_df.apply(lambda row: int(row['out_rate']+row['net_routed_7day']*row['assisted_ratio']*multiplier), axis=1)
                channels_df['adjusted_rebal_rate'] = channels_df.apply(lambda row: int(row['rebal_ppm']+row['profit_margin']), axis=1)
                channels_df['out_rate_only'] = channels_df.apply(lambda row: int(row['out_rate']+row['net_routed_7day']*row['out_rate']*(multiplier/100)), axis=1)
                channels_df['fee_rate_only'] = channels_df.apply(lambda row: int(row['local_fee_rate']+row['net_routed_7day']*row['local_fee_rate']*(multiplier/100)), axis=1)
                channels_df['new_rate'] = channels_df.apply(lambda row: row['adjusted_out_rate'] if row['net_routed_7day'] != 0 else (row['adjusted_rebal_rate'] if row['rebal_ppm'] > 0 and row['out_rate'] > 0 else (row['out_rate_only'] if row['out_rate'] > 0 else (row['min_suggestion'] if row['net_routed_7day'] == 0 and row['in_percent'] < 25 else row['fee_rate_only']))), axis=1)
                channels_df['new_rate'] = channels_df.apply(lambda row: 0 if row['new_rate'] < 0 else row['new_rate'], axis=1)
                channels_df['adjustment'] = channels_df.apply(lambda row: int(row['new_rate']-row['local_fee_rate']), axis=1)
                channels_df['new_rate'] = channels_df.apply(lambda row: row['local_fee_rate']-10 if row['adjustment']==0 and row['out_percent']>=25 and row['net_routed_7day']==0 else row['new_rate'], axis=1)
                channels_df['new_rate'] = channels_df.apply(lambda row: row['local_fee_rate']+25 if row['adjustment']==0 and row['out_percent']<25 and row['failed_out_1day']>failed_htlc_limit else row['new_rate'], axis=1)
                channels_df['new_rate'] = channels_df.apply(lambda row: row['max_suggestion'] if row['new_rate'] > row['max_suggestion'] else row['new_rate'], axis=1)
                channels_df['new_rate'] = channels_df.apply(lambda row: row['min_suggestion'] if row['new_rate'] < row['min_suggestion'] else row['new_rate'], axis=1)
                channels_df['new_rate'] = channels_df.apply(lambda row: int(round(row['new_rate']/increment, 0)*increment), axis=1)
                channels_df['new_rate'] = channels_df.apply(lambda row: max_rate if max_rate < row['new_rate'] else row['new_rate'], axis=1)
                channels_df['new_rate'] = channels_df.apply(lambda row: min_rate if min_rate > row['new_rate'] else row['new_rate'], axis=1)
                channels_df['adjustment'] = channels_df.apply(lambda row: int(row['new_rate']-row['local_fee_rate']), axis=1)
                update_df = channels_df[channels_df['adjustment']!=0]
                if not update_df.empty:
                    for target_channel in update_df.to_dict(orient='records'):
                        print('Updating fees for channel ' + str(target_channel['chan_id']) + ' to a value of: ' + str(target_channel['new_rate']))
                        channel = Channels.objects.filter(chan_id=target_channel['chan_id'])[0]
                        channel_point = ln.ChannelPoint()
                        channel_point.funding_txid_bytes = bytes.fromhex(channel.funding_txid)
                        channel_point.funding_txid_str = channel.funding_txid
                        channel_point.output_index = channel.output_index
                        stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=channel.local_base_fee, fee_rate=(target_channel['new_rate']/1000000), time_lock_delta=channel.local_cltv))
                        channel.local_fee_rate = target_channel['new_rate']
                        channel.fees_updated = datetime.now()
                        channel.save()
                        Autofees(chan_id=channel.chan_id, peer_alias=channel.alias, setting='Fee Rate', old_value=target_channel['local_fee_rate'], new_value=target_channel['new_rate']).save()

def main():
    try:
        stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        #Update data
        update_peers(stub)
        update_channels(stub)
        update_invoices(stub)
        update_payments(stub)
        update_forwards(stub)
        update_onchain(stub)
        update_closures(stub)
        reconnect_peers(stub)
        clean_payments(stub)
        auto_fees(stub)
    except Exception as e:
        print('Error processing background data: ' + str(e))

if __name__ == '__main__':
    main()
