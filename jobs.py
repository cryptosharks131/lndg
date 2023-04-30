import django
from django.db.models import Max, Sum, Avg, Count
from django.db.models.functions import TruncDay
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
from gui.models import Payments, PaymentHops, Invoices, Forwards, Channels, Peers, Onchain, Closures, Resolutions, PendingHTLCs, LocalSettings, FailedHTLCs, Autofees, PendingChannels, HistFailedHTLC, PeerEvents

def update_payments(stub):
    self_pubkey = stub.GetInfo(ln.GetInfoRequest()).identity_pubkey
    inflight_payments = Payments.objects.filter(status=1).order_by('index')
    for payment in inflight_payments:
        payment_data = stub.ListPayments(ln.ListPaymentsRequest(include_incomplete=True, index_offset=payment.index-1, max_payments=1)).payments
        #Ignore inflight payments before 30 days
        if len(payment_data) > 0 and payment.payment_hash == payment_data[0].payment_hash and payment.creation_date > (datetime.now() - timedelta(days=30)):
            update_payment(stub, payment_data[0], self_pubkey)
        else:
            payment.status = 3
            payment.save()
    last_index = Payments.objects.aggregate(Max('index'))['index__max'] if Payments.objects.exists() else 0
    payments = stub.ListPayments(ln.ListPaymentsRequest(include_incomplete=True, index_offset=last_index, max_payments=100)).payments
    for payment in payments:
        #print(f"{datetime.now().strftime('%c')} : Processing New {payment.payment_index=} {payment.status=} {payment.payment_hash=}")
        try:
            new_payment = Payments(creation_date=datetime.fromtimestamp(payment.creation_date), payment_hash=payment.payment_hash, value=round(payment.value_msat/1000, 3), fee=round(payment.fee_msat/1000, 3), status=payment.status, index=payment.payment_index)
            new_payment.save()
        except Exception as e:
            #Error inserting, try to update instead
            print(f"{datetime.now().strftime('%c')} : Error processing {new_payment=} : {str(e)=}")
        update_payment(stub, payment, self_pubkey)

def update_payment(stub, payment, self_pubkey):
    db_payment = Payments.objects.filter(payment_hash=payment.payment_hash)[0]
    db_payment.creation_date = datetime.fromtimestamp(payment.creation_date)
    db_payment.value = round(payment.value_msat/1000, 3)
    db_payment.fee = round(payment.fee_msat/1000, 3)
    db_payment.status = payment.status
    db_payment.index = payment.payment_index
    if payment.status == 2 or payment.status == 1:
        PaymentHops.objects.filter(payment_hash=db_payment).delete()
        db_payment.chan_out = None
        db_payment.rebal_chan = None
        db_payment.save()
        for attempt in payment.htlcs:
            if attempt.status == 1 or attempt.status == 0:
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
                    if hop_count == total_hops:
                        # Add additional HTLC information in last hop alias
                        alias += f'[ {payment.status}-{attempt.status}-{attempt.failure.code}-{attempt.failure.failure_source_index} ]'
                    #if hop_count == total_hops:
                        #print(f"{datetime.now().strftime('%c')} : Debug Hop {attempt.attempt_id=} {attempt.route.total_amt=} {hop.mpp_record.payment_addr.hex()=} {hop.mpp_record.total_amt_msat=} {hop.amp_record=} {db_payment.payment_hash=}")
                    if attempt.status == 1 or attempt.status == 0 or (attempt.status == 2 and attempt.failure.code in (1,2,12)):
                        PaymentHops(payment_hash=db_payment, attempt_id=attempt.attempt_id, step=hop_count, chan_id=hop.chan_id, alias=alias, chan_capacity=hop.chan_capacity, node_pubkey=hop.pub_key, amt=round(hop.amt_to_forward_msat/1000, 3), fee=round(fee, 3), cost_to=round(cost_to, 3)).save()
                    cost_to += fee
                    if hop_count == 1 and attempt.status == 1:
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
    open_invoices = Invoices.objects.filter(state=0).order_by('index')
    for open_invoice in open_invoices:
        #print(f"{datetime.now().strftime('%c')} : Processing open invoice {open_invoice.index=} {open_invoice.state=} {open_invoice.r_hash=}")
        invoice_data = stub.ListInvoices(ln.ListInvoiceRequest(index_offset=open_invoice.index-1, num_max_invoices=1)).invoices
        if len(invoice_data) > 0 and open_invoice.r_hash == invoice_data[0].r_hash.hex():
            update_invoice(stub, invoice_data[0], open_invoice)
        else:
            open_invoice.state = 2
            open_invoice.save()
    last_index = Invoices.objects.aggregate(Max('index'))['index__max'] if Invoices.objects.exists() else 0
    invoices = stub.ListInvoices(ln.ListInvoiceRequest(index_offset=last_index, num_max_invoices=100)).invoices
    for invoice in invoices:
        db_invoice = Invoices(creation_date=datetime.fromtimestamp(invoice.creation_date), r_hash=invoice.r_hash.hex(), value=round(invoice.value_msat/1000, 3), amt_paid=invoice.amt_paid_sat, state=invoice.state, index=invoice.add_index)
        db_invoice.save()
        update_invoice(stub, invoice, db_invoice)

def update_invoice(stub, invoice, db_invoice):
    if invoice.state == 1:
        if len(invoice.htlcs) > 0:
            chan_in_id = invoice.htlcs[0].chan_id
            alias = Channels.objects.filter(chan_id=chan_in_id)[0].alias if Channels.objects.filter(chan_id=chan_in_id).exists() else None
            records = invoice.htlcs[0].custom_records
            keysend_preimage = records[5482373484].hex() if 5482373484 in records else None
            message = records[34349334].decode('utf-8', errors='ignore')[:1000] if 34349334 in records else None
            if 34349337 in records and 34349339 in records and 34349343 in records and 34349334 in records:
                signerstub = lnsigner.SignerStub(lnd_connect())
                self_pubkey = stub.GetInfo(ln.GetInfoRequest()).identity_pubkey
                try:
                    valid = signerstub.VerifyMessage(lns.VerifyMessageReq(msg=(records[34349339]+bytes.fromhex(self_pubkey)+records[34349343]+records[34349334]), signature=records[34349337], pubkey=records[34349339])).valid
                except:
                    print(f"{datetime.now().strftime('%c')} : Unable to validate signature on invoice: {invoice.r_hash.hex()}")
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
        db_invoice.state = invoice.state
        db_invoice.amt_paid = invoice.amt_paid_sat
        db_invoice.settle_date = datetime.fromtimestamp(invoice.settle_date)
        db_invoice.chan_in = chan_in_id
        db_invoice.chan_in_alias = alias
        db_invoice.keysend_preimage = keysend_preimage
        db_invoice.message = message
        db_invoice.sender = sender
        db_invoice.sender_alias = sender_alias
    else:
        db_invoice.state = invoice.state
    db_invoice.save()

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
            db_channel.short_chan_id = str(channel.chan_id >> 40) + 'x' + str(channel.chan_id >> 16 & 0xFFFFFF) + 'x' + str(channel.chan_id & 0xFFFF)
            db_channel.initiator = channel.initiator
            db_channel.alias = alias
            db_channel.funding_txid = txid
            db_channel.output_index = index
            db_channel.capacity = channel.capacity
            db_channel.private = channel.private
            pending_channel = PendingChannels.objects.filter(funding_txid=txid, output_index=index)[0] if PendingChannels.objects.filter(funding_txid=txid, output_index=index).exists() else None
        # Update basic channel data
        db_channel.local_balance = channel.local_balance
        db_channel.remote_balance = channel.remote_balance
        db_channel.unsettled_balance = channel.unsettled_balance
        db_channel.local_commit = channel.commit_fee
        db_channel.local_chan_reserve = channel.local_chan_reserve_sat
        db_channel.num_updates = channel.num_updates
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
        # Check for peer events
        if db_channel.is_active != channel.active:
            db_channel.last_update = datetime.now()
            peer_alias = Peers.objects.filter(pubkey=db_channel.remote_pubkey)[0].alias if Peers.objects.filter(pubkey=db_channel.remote_pubkey).exists() else None
            db_channel.alias = '' if peer_alias is None else peer_alias
            if db_channel.is_active is None:
                PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='Connection', old_value=None, new_value=(1 if channel.active else 0), out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
            elif channel.active:
                PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='Connection', old_value=0, new_value=1, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
            else:
                PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='Connection', old_value=1, new_value=0, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
            db_channel.is_active = channel.active
        try:
            chan_data = stub.GetChanInfo(ln.ChanInfoRequest(chan_id=channel.chan_id))
            if chan_data.node1_pub == channel.remote_pubkey:
                local_policy = chan_data.node2_policy
                remote_policy = chan_data.node1_policy
            else:
                local_policy = chan_data.node1_policy
                remote_policy = chan_data.node2_policy
            old_fee_rate = db_channel.local_fee_rate if db_channel.local_fee_rate is not None else 0
            db_channel.local_base_fee = local_policy.fee_base_msat
            db_channel.local_fee_rate = local_policy.fee_rate_milli_msat
            db_channel.local_cltv = local_policy.time_lock_delta
            db_channel.local_disabled = local_policy.disabled
            db_channel.local_min_htlc_msat = local_policy.min_htlc
            db_channel.local_max_htlc_msat = local_policy.max_htlc_msat
            if db_channel.remote_cltv == -1:
                PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='BaseFee', old_value=None, new_value=remote_policy.fee_base_msat, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                db_channel.remote_base_fee = remote_policy.fee_base_msat
                PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='FeeRate', old_value=None, new_value=remote_policy.fee_rate_milli_msat, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                db_channel.remote_fee_rate = remote_policy.fee_rate_milli_msat
                if remote_policy.disabled:
                    PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='Disabled', old_value=None, new_value=1, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                else:
                    PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='Disabled', old_value=None, new_value=0, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                db_channel.remote_disabled = remote_policy.disabled
                PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='CTLV', old_value=None, new_value=remote_policy.time_lock_delta, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                db_channel.remote_cltv = remote_policy.time_lock_delta
                PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='MinHTLC', old_value=None, new_value=remote_policy.min_htlc, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                db_channel.remote_min_htlc_msat = remote_policy.min_htlc
                PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='MaxHTLC', old_value=None, new_value=remote_policy.max_htlc_msat, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                db_channel.remote_max_htlc_msat = remote_policy.max_htlc_msat
            else:
                if db_channel.remote_base_fee != remote_policy.fee_base_msat:
                    PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='BaseFee', old_value=db_channel.remote_base_fee, new_value=remote_policy.fee_base_msat, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                    db_channel.remote_base_fee = remote_policy.fee_base_msat
                if db_channel.remote_fee_rate != remote_policy.fee_rate_milli_msat:
                    PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='FeeRate', old_value=db_channel.remote_fee_rate, new_value=remote_policy.fee_rate_milli_msat, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                    db_channel.remote_fee_rate = remote_policy.fee_rate_milli_msat
                if db_channel.remote_disabled != remote_policy.disabled:
                    if db_channel.remote_disabled is None:
                        PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='Disabled', old_value=None, new_value=(1 if remote_policy.disabled else 0), out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                    elif remote_policy.disabled:
                        PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='Disabled', old_value=0, new_value=1, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                    else:
                        PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='Disabled', old_value=1, new_value=0, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                    db_channel.remote_disabled = remote_policy.disabled
                if db_channel.remote_cltv != remote_policy.time_lock_delta:
                    PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='CTLV', old_value=db_channel.remote_cltv, new_value=remote_policy.time_lock_delta, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                    db_channel.remote_cltv = remote_policy.time_lock_delta
                if db_channel.remote_min_htlc_msat != remote_policy.min_htlc:
                    PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='MinHTLC', old_value=db_channel.remote_min_htlc_msat, new_value=remote_policy.min_htlc, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                    db_channel.remote_min_htlc_msat = remote_policy.min_htlc
                if db_channel.remote_max_htlc_msat != remote_policy.max_htlc_msat:
                    PeerEvents(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, event='MaxHTLC', old_value=db_channel.remote_max_htlc_msat, new_value=remote_policy.max_htlc_msat, out_liq=(db_channel.local_balance + db_channel.pending_outbound)).save()
                    db_channel.remote_max_htlc_msat = remote_policy.max_htlc_msat
        except:
            old_fee_rate = None
            db_channel.local_base_fee = -1 if db_channel.local_base_fee is None else db_channel.local_base_fee
            db_channel.local_fee_rate = -1 if db_channel.local_fee_rate is None else db_channel.local_fee_rate
            db_channel.local_cltv = -1 if db_channel.local_cltv is None else db_channel.local_cltv
            db_channel.local_disabled = False if db_channel.local_disabled is None else db_channel.local_disabled
            db_channel.local_min_htlc_msat = -1 if db_channel.local_min_htlc_msat is None else db_channel.local_min_htlc_msat
            db_channel.local_max_htlc_msat = -1 if db_channel.local_max_htlc_msat is None else db_channel.local_max_htlc_msat
            db_channel.remote_base_fee = -1 if db_channel.remote_base_fee is None else db_channel.remote_base_fee
            db_channel.remote_fee_rate = -1 if db_channel.remote_fee_rate is None else db_channel.remote_fee_rate
            db_channel.remote_cltv = -1 if db_channel.remote_cltv is None else db_channel.remote_cltv
            db_channel.remote_disabled = False if db_channel.remote_disabled is None else db_channel.remote_disabled
            db_channel.remote_min_htlc_msat = -1 if db_channel.remote_min_htlc_msat is None else db_channel.remote_min_htlc_msat
            db_channel.remote_max_htlc_msat = -1 if db_channel.remote_max_htlc_msat is None else db_channel.remote_max_htlc_msat
        # Check for pending settings to be applied
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
            if pending_channel.auto_rebalance is not None:
                db_channel.auto_rebalance = pending_channel.auto_rebalance
            if pending_channel.ar_amt_target:
                db_channel.ar_amt_target = pending_channel.ar_amt_target
            if pending_channel.ar_in_target:
                db_channel.ar_in_target = pending_channel.ar_in_target
            if pending_channel.ar_out_target:
                db_channel.ar_out_target = pending_channel.ar_out_target
            if pending_channel.ar_max_cost:
                db_channel.ar_max_cost = pending_channel.ar_max_cost
            if pending_channel.auto_fees is not None:
                db_channel.auto_fees = pending_channel.auto_fees
            pending_channel.delete()
        if old_fee_rate is not None and old_fee_rate != local_policy.fee_rate_milli_msat:
            print(f"{datetime.now().strftime('%c')} : Ext Fee Change Detected {db_channel.chan_id=} {db_channel.alias=} {old_fee_rate=} {db_channel.local_fee_rate=}")
            #External Fee change detected, update auto fee log
            db_channel.fees_updated = datetime.now()
            Autofees(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, setting=(f"Ext"), old_value=old_fee_rate, new_value=db_channel.local_fee_rate).save()
        db_channel.save()
        counter += 1
        chan_list.append(channel.chan_id)
    records = Channels.objects.filter(is_open=True).count()
    if records > counter:
        #A channel must have been closed, mark it as closed
        channels = Channels.objects.filter(is_open=True).exclude(chan_id__in=chan_list)
        for channel in channels:
            channel.last_update = datetime.now()
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
    base_url = network_links() + ('/testnet' if settings.LND_NETWORK == 'testnet' else '') + '/api/tx/'
    try:
        request_data = get(base_url + txid).json()
        fee = request_data['fee']
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : Error getting closure fees {txid=} {str(e)=}")
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
                closing_costs = get_tx_fees(closure.closing_tx_hash) if (closure.open_initiator != 2 and closure.close_type not in [4, 5]) else 0
                db_closure = Closures(chan_id=closure.chan_id, funding_txid=txid, funding_index=index, closing_tx=closure.closing_tx_hash, remote_pubkey=closure.remote_pubkey, capacity=closure.capacity, close_height=closure.close_height, settled_balance=closure.settled_balance, time_locked_balance=closure.time_locked_balance, close_type=closure.close_type, open_initiator=closure.open_initiator, close_initiator=closure.close_initiator, resolution_count=resolution_count)
                try:
                    db_closure.save()
                except Exception as e:
                    print(f"{datetime.now().strftime('%c')} : Error inserting closure: {str(e)}")
                    Closures.objects.filter(funding_txid=txid,funding_index=index).delete()
                    return
                if resolution_count > 0:
                    Resolutions.objects.filter(chan_id=closure.chan_id).delete()
                    for resolution in closure.resolutions:
                        if resolution.resolution_type != 2 and not Resolutions.objects.filter(sweep_txid=resolution.sweep_txid).exists():
                            closing_costs += get_tx_fees(resolution.sweep_txid)
                        Resolutions(chan_id=closure.chan_id, resolution_type=resolution.resolution_type, outcome=resolution.outcome, outpoint_tx=resolution.outpoint.txid_str, outpoint_index=resolution.outpoint.output_index, amount_sat=resolution.amount_sat, sweep_txid=resolution.sweep_txid).save()
                db_closure.closing_costs = closing_costs
                db_closure.save()

def reconnect_peers(stub):
    inactive_peers = Channels.objects.filter(is_open=True, is_active=False, private=False).values_list('remote_pubkey', flat=True).distinct()
    if len(inactive_peers) > 0:
        peers = Peers.objects.all()
        for inactive_peer in inactive_peers:
            if peers.filter(pubkey=inactive_peer).exists():
                peer = peers.filter(pubkey=inactive_peer)[0]
                if peer.last_reconnected == None or (int((datetime.now() - peer.last_reconnected).total_seconds() / 60) > 2):
                    print(f"{datetime.now().strftime('%c')} : Reconnecting peer {peer.alias} {peer.pubkey=} {peer.last_reconnected=}")
                    if peer.connected == True:
                        print(f"{datetime.now().strftime('%c')} : ... Inactive channel is still connected to peer, disconnecting peer. {peer.alias=} {inactive_peer=}")
                        try:
                            response = stub.DisconnectPeer(ln.DisconnectPeerRequest(pub_key=inactive_peer))
                            print(f"{datetime.now().strftime('%c')} : .... Disconnected peer {peer.alias} {inactive_peer=} {response=}")
                            peer.connected = False
                            peer.save()
                        except Exception as e:
                            print(f"{datetime.now().strftime('%c')} : .... Error disconnecting peer {peer.alias} {inactive_peer=} {str(e)=}")

                    try:
                        node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=inactive_peer, include_channels=False)).node
                        host = node.addresses[0].addr
                    except Exception as e:
                        print(f"{datetime.now().strftime('%c')} : ... Unable to find node info on graph, using last known value for {peer.alias} {peer.pubkey=} {peer.address=} {str(e)=}")
                        host = peer.address
                    #address = ln.LightningAddress(pubkey=inactive_peer, host=host)
                    print(f"{datetime.now().strftime('%c')} : ... Attempting connection to {peer.alias} {inactive_peer=} {host=}")
                    try:
                        #try both the graph value and last know value
                        stub.ConnectPeer(request = ln.ConnectPeerRequest(addr=ln.LightningAddress(pubkey=inactive_peer, host=host), perm=True, timeout=5))
                        if host != peer.address and peer.address[:9] != '127.0.0.1':
                            stub.ConnectPeer(request = ln.ConnectPeerRequest(addr=ln.LightningAddress(pubkey=inactive_peer, host=peer.address), perm=True, timeout=5))
                    except Exception as e:
                        error = str(e)
                        details_index = error.find('details =') + 11
                        debug_error_index = error.find('debug_error_string =') - 3
                        error_msg = error[details_index:debug_error_index]
                        print(f"{datetime.now().strftime('%c')} : .... Error reconnecting {peer.alias} {inactive_peer=} {error_msg=}")
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
                print(f"{datetime.now().strftime('%c')} : Error {payment.index=} {payment.status=} {payment.payment_hash=} {error_msg=}")
            finally:
                payment.cleaned = True
                payment.save()

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
            if LocalSettings.objects.filter(key='AF-UpdateHours').exists():
                update_hours = int(LocalSettings.objects.filter(key='AF-UpdateHours')[0].value)
            else:
                LocalSettings(key='AF-UpdateHours', value='24').save()
                update_hours = 24
            channels_df['eligible'] = channels_df.apply(lambda row: (datetime.now()-row['fees_updated']).total_seconds() > (update_hours*3600), axis=1)
            channels_df = channels_df[channels_df['eligible']==True]
            if channels_df.shape[0] > 0:
                failed_htlc_df = DataFrame.from_records(FailedHTLCs.objects.filter(timestamp__gte=filter_1day).order_by('-id').values())
                if failed_htlc_df.shape[0] > 0:
                    failed_htlc_df = failed_htlc_df[(failed_htlc_df['wire_failure']==15) & (failed_htlc_df['failure_detail']==6) & (failed_htlc_df['amount']>failed_htlc_df['chan_out_liq']+failed_htlc_df['chan_out_pending'])]
                forwards = Forwards.objects.filter(forward_date__gte=filter_7day, amt_out_msat__gte=1000000)
                forwards_df_7d = DataFrame.from_records(forwards.values())
                forwards_df_in_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
                forwards_df_out_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
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
                invoices_df_7d_sum = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).sum(numeric_only=True)
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
                        print(f"{datetime.now().strftime('%c')} : Updating fees for channel {str(target_channel['chan_id'])} to a value of: {str(target_channel['new_rate'])}")
                        channel = Channels.objects.filter(chan_id=target_channel['chan_id'])[0]
                        channel_point = ln.ChannelPoint()
                        channel_point.funding_txid_bytes = bytes.fromhex(channel.funding_txid)
                        channel_point.funding_txid_str = channel.funding_txid
                        channel_point.output_index = channel.output_index
                        stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=channel.local_base_fee, fee_rate=(target_channel['new_rate']/1000000), time_lock_delta=channel.local_cltv))
                        channel.local_fee_rate = target_channel['new_rate']
                        channel.fees_updated = datetime.now()
                        channel.save()
                        Autofees(chan_id=channel.chan_id, peer_alias=channel.alias, setting=(f"AF [ {target_channel['net_routed_7day']}:{target_channel['in_percent']}:{target_channel['out_percent']} ]"), old_value=target_channel['local_fee_rate'], new_value=target_channel['new_rate']).save()

def agg_htlcs(target_htlcs, category):
    try:
        target_ids = target_htlcs.values_list('id')
        agg_htlcs = FailedHTLCs.objects.filter(id__in=target_ids).annotate(day=TruncDay('timestamp')).values('day', 'chan_id_in', 'chan_id_out').annotate(amount=Sum('amount'), fee=Sum('missed_fee'), liq=Avg('chan_out_liq'), pending=Avg('chan_out_pending'), count=Count('id'), chan_in_alias=Max('chan_in_alias'), chan_out_alias=Max('chan_out_alias'))
        for htlc in agg_htlcs:
            if HistFailedHTLC.objects.filter(date=htlc['day'],chan_id_in=htlc['chan_id_in'],chan_id_out=htlc['chan_id_out']).exists():
                htlc_itm = HistFailedHTLC.objects.filter(date=htlc['day'],chan_id_in=htlc['chan_id_in'],chan_id_out=htlc['chan_id_out']).get()
            else:
                htlc_itm = HistFailedHTLC(htlc_count=0, amount_sum=0, fee_sum=0, liq_avg=0, pending_avg=0, balance_count=0, downstream_count=0, other_count=0)
                htlc_itm.date = htlc['day']
                htlc_itm.chan_id_in = htlc['chan_id_in']
                htlc_itm.chan_id_out = htlc['chan_id_out']
                htlc_itm.chan_in_alias = htlc['chan_in_alias']
                htlc_itm.chan_out_alias = htlc['chan_out_alias']
            htlc_itm.htlc_count += htlc['count']
            htlc_itm.amount_sum += htlc['amount']
            htlc_itm.fee_sum += htlc['fee']
            htlc_itm.liq_avg += (htlc['count']/htlc_itm.htlc_count)*((0 if htlc['liq'] is None else htlc['liq'])-htlc_itm.liq_avg)
            htlc_itm.pending_avg += (htlc['count']/htlc_itm.htlc_count)*((0 if htlc['pending'] is None else htlc['pending'])-htlc_itm.pending_avg)
            if category == 'balance':
                htlc_itm.balance_count += htlc['count']
            elif category == 'downstream':
                htlc_itm.downstream_count += htlc['count']
            elif category == 'other':
                htlc_itm.other_count += htlc['count']
            htlc_itm.save()
            FailedHTLCs.objects.filter(id__in=target_ids, chan_id_in=htlc['chan_id_in'], chan_id_out=htlc['chan_id_out']).annotate(day=TruncDay('timestamp')).filter(day=htlc['day']).delete()
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : Error processing background data: {str(e)}")

def agg_failed_htlcs():
    time_filter = datetime.now() - timedelta(days=30)
    agg_htlcs(FailedHTLCs.objects.filter(timestamp__lte=time_filter, failure_detail=6)[:100], 'balance')
    agg_htlcs(FailedHTLCs.objects.filter(timestamp__lte=time_filter, failure_detail=99)[:100], 'downstream')
    agg_htlcs(FailedHTLCs.objects.filter(timestamp__lte=time_filter).exclude(failure_detail__in=[6, 99])[:100], 'other')


def main():
    try:
        stub = lnrpc.LightningStub(lnd_connect())
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
        agg_failed_htlcs()
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : Error processing background data: {str(e)}")
if __name__ == '__main__':
    main()
