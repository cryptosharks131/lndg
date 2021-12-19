from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Sum, IntegerField
from django.db.models.functions import Round
from django.conf import settings
from datetime import datetime, timedelta
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .forms import OpenChannelForm, CloseChannelForm, ConnectPeerForm, AddInvoiceForm, RebalancerForm, ChanPolicyForm, AutoRebalanceForm, ARTarget
from .models import Payments, PaymentHops, Invoices, Forwards, Channels, Rebalancer, LocalSettings, Peers, Onchain, PendingHTLCs, FailedHTLCs
from .serializers import ConnectPeerSerializer, FailedHTLCSerializer, LocalSettingsSerializer, OpenChannelSerializer, CloseChannelSerializer, AddInvoiceSerializer, PaymentHopsSerializer, PaymentSerializer, InvoiceSerializer, ForwardSerializer, ChannelSerializer, PendingHTLCSerializer, RebalancerSerializer, UpdateAliasSerializer, PeerSerializer, OnchainSerializer, PendingHTLCs, FailedHTLCs
from .lnd_deps import lightning_pb2 as ln
from .lnd_deps import lightning_pb2_grpc as lnrpc
from .lnd_deps.lnd_connect import lnd_connect

# Create your views here.
def home(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        #Get balance and general node information
        node_info = stub.GetInfo(ln.GetInfoRequest())
        balances = stub.WalletBalance(ln.WalletBalanceRequest())
        pending_channels = stub.PendingChannels(ln.PendingChannelsRequest())
        limbo_balance = pending_channels.total_limbo_balance
        pending_open = pending_channels.pending_open_channels
        pending_closed = pending_channels.pending_closing_channels
        pending_force_closed = pending_channels.pending_force_closing_channels
        waiting_for_close = pending_channels.waiting_close_channels
        #Get recorded payment events
        payments = Payments.objects.exclude(status=3).order_by('-creation_date')
        total_payments = payments.filter(status=2).count()
        total_sent = 0 if total_payments == 0 else payments.filter(status=2).aggregate(Sum('value'))['value__sum']
        total_fees = 0 if total_payments == 0 else payments.aggregate(Sum('fee'))['fee__sum']
        #Get recorded invoice details
        invoices = Invoices.objects.exclude(state=2).order_by('-creation_date')
        total_invoices = invoices.filter(state=1).count()
        total_received = 0 if total_invoices == 0 else invoices.aggregate(Sum('amt_paid'))['amt_paid__sum']
        #Get recorded forwarding events
        forwards = Forwards.objects.all().annotate(amt_in=Sum('amt_in_msat')/1000).annotate(amt_out=Sum('amt_out_msat')/1000).annotate(ppm=Round((Sum('fee')*1000000000)/Sum('amt_out_msat'), output_field=IntegerField())).order_by('-id')
        total_forwards = forwards.count()
        total_value_forwards = 0 if total_forwards == 0 else int(forwards.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        total_earned = 0 if total_forwards == 0 else forwards.aggregate(Sum('fee'))['fee__sum']
        #Get current active channels
        active_channels = Channels.objects.filter(is_active=True, is_open=True).annotate(outbound_percent=(Sum('local_balance')*1000)/Sum('capacity')).annotate(inbound_percent=(Sum('remote_balance')*1000)/Sum('capacity')).order_by('outbound_percent')
        total_capacity = 0 if active_channels.count() == 0 else active_channels.aggregate(Sum('capacity'))['capacity__sum']
        total_inbound = 0 if total_capacity == 0 else active_channels.aggregate(Sum('remote_balance'))['remote_balance__sum']
        total_outbound = 0 if total_capacity == 0 else active_channels.aggregate(Sum('local_balance'))['local_balance__sum']
        total_unsettled = 0 if total_capacity == 0 else active_channels.aggregate(Sum('unsettled_balance'))['unsettled_balance__sum']
        detailed_active_channels = []
        filter_7day = datetime.now() - timedelta(days=7)
        routed_7day = forwards.filter(forward_date__gte=filter_7day).count()
        routed_7day_amt = 0 if routed_7day == 0 else int(forwards.filter(forward_date__gte=filter_7day).aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        total_earned_7day = 0 if routed_7day == 0 else forwards.filter(forward_date__gte=filter_7day).aggregate(Sum('fee'))['fee__sum']
        payments_7day = payments.filter(status=2).filter(creation_date__gte=filter_7day).count()
        total_7day_fees = 0 if payments_7day == 0 else payments.filter(creation_date__gte=filter_7day).aggregate(Sum('fee'))['fee__sum']
        pending_htlcs = PendingHTLCs.objects.all()
        pending_htlc_count = pending_htlcs.count()
        pending_outbound = 0 if pending_htlc_count == 0 else pending_htlcs.filter(incoming=False).aggregate(Sum('amount'))['amount__sum']
        for channel in active_channels:
            detailed_channel = {}
            detailed_channel['remote_pubkey'] = channel.remote_pubkey
            detailed_channel['chan_id'] = channel.chan_id
            detailed_channel['capacity'] = channel.capacity
            detailed_channel['local_balance'] = channel.local_balance
            detailed_channel['remote_balance'] = channel.remote_balance
            detailed_channel['unsettled_balance'] = channel.unsettled_balance
            detailed_channel['initiator'] = channel.initiator
            detailed_channel['alias'] = channel.alias
            detailed_channel['local_base_fee'] = channel.local_base_fee
            detailed_channel['local_fee_rate'] = channel.local_fee_rate
            detailed_channel['remote_base_fee'] = channel.remote_base_fee
            detailed_channel['remote_fee_rate'] = channel.remote_fee_rate
            detailed_channel['funding_txid'] = channel.funding_txid
            detailed_channel['output_index'] = channel.output_index
            detailed_channel['outbound_percent'] = int(round(channel.outbound_percent/10, 0))
            detailed_channel['inbound_percent'] = int(round(channel.inbound_percent/10, 0))
            detailed_channel['routed_in'] = forwards.filter(chan_id_in=channel.chan_id).count()
            detailed_channel['routed_out'] = forwards.filter(chan_id_out=channel.chan_id).count()
            detailed_channel['amt_routed_in'] = 0 if detailed_channel['routed_in'] == 0 else int(forwards.filter(chan_id_in=channel.chan_id).aggregate(Sum('amt_in_msat'))['amt_in_msat__sum']/10000000)/100
            detailed_channel['amt_routed_out'] = 0 if detailed_channel['routed_out'] == 0 else int(forwards.filter(chan_id_out=channel.chan_id).aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/10000000)/100
            detailed_channel['routed_in_7day'] = forwards.filter(forward_date__gte=filter_7day).filter(chan_id_in=channel.chan_id).count()
            detailed_channel['routed_out_7day'] = forwards.filter(forward_date__gte=filter_7day).filter(chan_id_out=channel.chan_id).count()
            detailed_channel['amt_routed_in_7day'] = 0 if detailed_channel['routed_in_7day'] == 0 else int(forwards.filter(forward_date__gte=filter_7day).filter(chan_id_in=channel.chan_id).aggregate(Sum('amt_in_msat'))['amt_in_msat__sum']/10000000)/100
            detailed_channel['amt_routed_out_7day'] = 0 if detailed_channel['routed_out_7day'] == 0 else int(forwards.filter(forward_date__gte=filter_7day).filter(chan_id_out=channel.chan_id).aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/10000000)/100
            detailed_channel['htlc_count'] = pending_htlcs.filter(chan_id=channel.chan_id).count()
            detailed_channel['auto_rebalance'] = channel.auto_rebalance
            detailed_channel['ar_target'] = channel.ar_target
            detailed_active_channels.append(detailed_channel)
        #Get current inactive channels
        inactive_channels = Channels.objects.filter(is_active=False, is_open=True).annotate(outbound_percent=(Sum('local_balance')*100)/Sum('capacity')).annotate(inbound_percent=(Sum('remote_balance')*100)/Sum('capacity')).order_by('-local_fee_rate').order_by('outbound_percent')
        inactive_outbound = 0 if inactive_channels.count() == 0 else inactive_channels.aggregate(Sum('local_balance'))['local_balance__sum']
        sum_outbound = total_outbound + pending_outbound + inactive_outbound
        onchain_txs = Onchain.objects.all()
        onchain_costs = 0 if onchain_txs.count() == 0 else onchain_txs.aggregate(Sum('fee'))['fee__sum']
        onchain_costs_7day = 0 if onchain_txs.filter(time_stamp__gte=filter_7day).count() == 0 else onchain_txs.filter(time_stamp__gte=filter_7day).aggregate(Sum('fee'))['fee__sum']
        total_costs = total_fees + onchain_costs
        total_costs_7day = total_7day_fees + onchain_costs_7day
        #Get list of recent rebalance requests
        rebalances = Rebalancer.objects.all().order_by('-requested')
        #Grab local settings
        local_settings = LocalSettings.objects.all()
        #Build context for front-end and render page
        context = {
            'node_info': node_info,
            'balances': balances,
            'payments': payments[:6],
            'total_sent': int(total_sent),
            'fees_paid': round(total_fees, 1),
            'total_payments': total_payments,
            'invoices': invoices[:6],
            'total_received': total_received,
            'total_invoices': total_invoices,
            'forwards': forwards[:15],
            'earned': round(total_earned, 1),
            'total_forwards': total_forwards,
            'total_value_forwards': total_value_forwards,
            'routed_7day': routed_7day,
            'routed_7day_amt': routed_7day_amt,
            'earned_7day': round(total_earned_7day, 1),
            'routed_7day_percent': 0 if sum_outbound == 0 else int((routed_7day_amt/sum_outbound)*100),
            'profit_per_outbound': 0 if sum_outbound == 0 else int((total_earned_7day - total_7day_fees) / (sum_outbound / 1000000)),
            'profit_per_outbound_real': 0 if sum_outbound == 0 else int((total_earned_7day - total_costs_7day) / (sum_outbound / 1000000)),
            'percent_cost': 0 if total_earned == 0 else int((total_costs/total_earned)*100),
            'percent_cost_7day': 0 if total_earned_7day == 0 else int((total_costs_7day/total_earned_7day)*100),
            'onchain_costs': onchain_costs,
            'active_channels': detailed_active_channels,
            'capacity': total_capacity,
            'inbound': total_inbound,
            'outbound': total_outbound,
            'unsettled': total_unsettled,
            'limbo_balance': limbo_balance,
            'inactive_channels': inactive_channels,
            'pending_open': pending_open,
            'pending_closed': pending_closed,
            'pending_force_closed': pending_force_closed,
            'waiting_for_close': waiting_for_close,
            'rebalances': rebalances[:12],
            'rebalancer_form': RebalancerForm,
            'chan_policy_form': ChanPolicyForm,
            'local_settings': local_settings,
            'pending_htlc_count': pending_htlc_count,
            'failed_htlcs': FailedHTLCs.objects.all().order_by('-timestamp')[:10]
        }
        return render(request, 'home.html', context)
    else:
        return redirect('home')

def route(request):
    if request.method == 'GET':
        payment_hash = request.GET.urlencode()[1:]
        context = {
            'payment_hash': payment_hash,
            'route': PaymentHops.objects.filter(payment_hash=payment_hash)
        }
        return render(request, 'route.html', context)
    else:
        return redirect('home')

def peers(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        context = {
            'peers': Peers.objects.filter(connected=True)
        }
        return render(request, 'peers.html', context)
    else:
        return redirect('home')

def balances(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        context = {
            'utxos': stub.ListUnspent(ln.ListUnspentRequest(min_confs=0, max_confs=9999999)).utxos,
            'transactions': list(Onchain.objects.filter(block_height=0)) + list(Onchain.objects.exclude(block_height=0).order_by('-block_height'))
        }
        return render(request, 'balances.html', context)
    else:
        return redirect('home')

def pending_htlcs(request):
    if request.method == 'GET':
        context = {
            'incoming_htlcs': PendingHTLCs.objects.filter(incoming=True).order_by('hash_lock'),
            'outgoing_htlcs': PendingHTLCs.objects.filter(incoming=False).order_by('hash_lock')
        }
        return render(request, 'pending_htlcs.html', context)
    else:
        return redirect('home')

def open_channel_form(request):
    if request.method == 'POST':
        form = OpenChannelForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                pubkey_bytes = bytes.fromhex(form.cleaned_data['peer_pubkey'])
                for response in stub.OpenChannel(ln.OpenChannelRequest(node_pubkey=pubkey_bytes, local_funding_amount=form.cleaned_data['local_amt'], sat_per_byte=form.cleaned_data['sat_per_byte'])):
                    messages.success(request, 'Channel created! Funding TXID: ' + str(response.chan_pending.txid[::-1].hex()) + ':' + str(response.chan_pending.output_index))
                    break
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Channel creation failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')

def close_channel_form(request):
    if request.method == 'POST':
        form = CloseChannelForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                funding_txid = form.cleaned_data['funding_txid']
                output_index = form.cleaned_data['output_index']
                target_fee = form.cleaned_data['target_fee']
                channel_point = ln.ChannelPoint()
                channel_point.funding_txid_bytes = bytes.fromhex(funding_txid)
                channel_point.funding_txid_str = funding_txid
                channel_point.output_index = output_index
                if form.cleaned_data['force']:
                    for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point, force=True)):
                        messages.success(request, 'Channel force closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index))
                        break
                else:
                    for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point, sat_per_byte=target_fee)):
                        messages.success(request, 'Channel gracefully closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index))
                        break
            except Exception as e:
                error = str(e)
                messages.error(request, 'Channel close failed! Error: ' + error)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')

def connect_peer_form(request):
    if request.method == 'POST':
        form = ConnectPeerForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                peer_pubkey = form.cleaned_data['peer_pubkey']
                host = form.cleaned_data['host']
                ln_addr = ln.LightningAddress()
                ln_addr.pubkey = peer_pubkey
                ln_addr.host = host
                response = stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
                messages.success(request, 'Connection successful! ' + str(response))
            except Exception as e:
                error = str(e)
                messages.error(request, 'Connection request failed! Error: ' + error)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')

def new_address_form(request):
    if request.method == 'POST':
        try:
            stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
            response = stub.NewAddress(ln.NewAddressRequest(type=0))
            messages.success(request, 'Deposit Address: ' + str(response.address))
        except Exception as e:
            error = str(e)
            messages.error(request, 'Address request! Error: ' + error)
    return redirect('home')

def add_invoice_form(request):
    if request.method == 'POST':
        form = AddInvoiceForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                response = stub.AddInvoice(ln.Invoice(value=form.cleaned_data['value']))
                messages.success(request, 'Invoice created! ' + str(response.payment_request))
            except Exception as e:
                error = str(e)
                messages.error(request, 'Invoice creation failed! Error: ' + error)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')

def rebalance(request):
    if request.method == 'POST':
        form = RebalancerForm(request.POST)
        if form.is_valid():
            try:
                chan_ids = []
                for channel in form.cleaned_data['outgoing_chan_ids']:
                    chan_ids.append(channel.chan_id)
                Rebalancer(value=form.cleaned_data['value'], fee_limit=form.cleaned_data['fee_limit'], outgoing_chan_ids=chan_ids, last_hop_pubkey=form.cleaned_data['last_hop_pubkey'], duration=form.cleaned_data['duration']).save()
                messages.success(request, 'Rebalancer request created!')
            except Exception as e:
                error = str(e)
                messages.error(request, 'Error entering rebalancer request! Error: ' + error)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')

def update_chan_policy(request):
    if request.method == 'POST':
        form = ChanPolicyForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                if form.cleaned_data['target_all']:
                    args = {'global': True, 'base_fee_msat': form.cleaned_data['new_base_fee'], 'fee_rate': (form.cleaned_data['new_fee_rate']/1000000), 'time_lock_delta': 40}
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(**args))
                elif len(form.cleaned_data['target_chans']) > 0:
                    for channel in form.cleaned_data['target_chans']:
                        channel_point = ln.ChannelPoint()
                        channel_point.funding_txid_bytes = bytes.fromhex(channel.funding_txid)
                        channel_point.funding_txid_str = channel.funding_txid
                        channel_point.output_index = channel.output_index
                        stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=form.cleaned_data['new_base_fee'], fee_rate=(form.cleaned_data['new_fee_rate']/1000000), time_lock_delta=40))
                else:
                    messages.error(request, 'No channels were specified in the update request!')
                messages.success(request, 'Channel policies updated! This will be broadcast during the next graph update!')
            except Exception as e:
                error = str(e)
                messages.error(request, 'Error updating channel policies! Error: ' + error)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
            print(form.errors)
    return redirect('home')

def auto_rebalance(request):
    if request.method == 'POST':
        form = AutoRebalanceForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['chan_id'] is not None:
                target_chan_id = form.cleaned_data['chan_id']
                target_channel = Channels.objects.filter(chan_id=target_chan_id)
                if len(target_channel) == 1:
                    target_channel = target_channel[0]
                    target_channel.auto_rebalance = True if target_channel.auto_rebalance == False else False
                    target_channel.save()
                    messages.success(request, 'Updated auto rebalancer status for: ' + str(target_channel.chan_id))
                else:
                    messages.error(request, 'Failed to update auto rebalancer status of channel: ' + str(target_chan_id))
            if form.cleaned_data['target_percent'] is not None:
                target_percent = form.cleaned_data['target_percent']
                try:
                    db_percent_target = LocalSettings.objects.get(key='AR-Target%')
                except:
                    LocalSettings(key='AR-Target%', value='0.35').save()
                    db_percent_target = LocalSettings.objects.get(key='AR-Target%')
                db_percent_target.value = target_percent
                db_percent_target.save()
                messages.success(request, 'Updated auto rebalancer rebalance target percent setting to: ' + str(target_percent))
            if form.cleaned_data['target_time'] is not None:
                target_time = form.cleaned_data['target_time']
                try:
                    db_time_target = LocalSettings.objects.get(key='AR-Time')
                except:
                    LocalSettings(key='AR-Time', value='10').save()
                    db_time_target = LocalSettings.objects.get(key='AR-Time')
                db_time_target.value = target_time
                db_time_target.save()
                messages.success(request, 'Updated auto rebalancer target time setting to: ' + str(target_time))
            if form.cleaned_data['enabled'] is not None:
                enabled = form.cleaned_data['enabled']
                try:
                    db_enabled = LocalSettings.objects.get(key='AR-Enabled')
                except:
                    LocalSettings(key='AR-Enabled', value='0').save()
                    db_enabled = LocalSettings.objects.get(key='AR-Enabled')
                db_enabled.value = enabled
                db_enabled.save()
                messages.success(request, 'Updated auto rebalancer enabled setting to: ' + str(enabled))
            if form.cleaned_data['outbound_percent'] is not None:
                outbound_percent = form.cleaned_data['outbound_percent']
                try:
                    db_outbound_target = LocalSettings.objects.get(key='AR-Outbound%')
                except:
                    LocalSettings(key='AR-Outbound%', value='0.85').save()
                    db_outbound_target = LocalSettings.objects.get(key='AR-Outbound%')
                db_outbound_target.value = outbound_percent
                db_outbound_target.save()
                messages.success(request, 'Updated auto rebalancer target outbound percent setting to: ' + str(outbound_percent))
            if form.cleaned_data['inbound_percent'] is not None:
                inbound_percent = form.cleaned_data['inbound_percent']
                try:
                    db_inbound_target = LocalSettings.objects.get(key='AR-Inbound%')
                except:
                    LocalSettings(key='AR-Inbound%', value='0.85').save()
                    db_inbound_target = LocalSettings.objects.get(key='AR-Inbound%')
                db_inbound_target.value = inbound_percent
                db_inbound_target.save()
                messages.success(request, 'Updated auto rebalancer target inbound percent setting to: ' + str(inbound_percent))
            if form.cleaned_data['fee_rate'] is not None:
                fee_rate = form.cleaned_data['fee_rate']
                try:
                    db_fee_rate = LocalSettings.objects.get(key='AR-MaxFeeRate')
                except:
                    LocalSettings(key='AR-MaxFeeRate', value='10').save()
                    db_fee_rate = LocalSettings.objects.get(key='AR-MaxFeeRate')
                db_fee_rate.value = fee_rate
                db_fee_rate.save()
                messages.success(request, 'Updated auto rebalancer max fee rate setting to: ' + str(fee_rate))
            if form.cleaned_data['max_cost'] is not None:
                max_cost = form.cleaned_data['max_cost']
                try:
                    db_max_cost = LocalSettings.objects.get(key='AR-MaxCost%')
                except:
                    LocalSettings(key='AR-MaxCost%', value='0.25').save()
                    db_max_cost = LocalSettings.objects.get(key='AR-MaxCost%')
                db_max_cost.value = max_cost
                db_max_cost.save()
                messages.success(request, 'Updated auto rebalancer max cost setting to: ' + str(max_cost))
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')

def ar_target(request):
    if request.method == 'POST':
        form = ARTarget(request.POST)
        if form.is_valid() and Channels.objects.filter(chan_id=form.cleaned_data['chan_id']).exists():
            chan_id = form.cleaned_data['chan_id']
            target = form.cleaned_data['ar_target']
            db_channel = Channels.objects.filter(chan_id=chan_id)[0]
            db_channel.ar_target = target
            db_channel.save()
            messages.success(request, 'Auto rebalancer inbound target for channel ' + str(chan_id) + ' updated to a value of: ' + str(target) + '%')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')

class PaymentsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payments.objects.all()
    serializer_class = PaymentSerializer

class PaymentHopsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentHops.objects.all()
    serializer_class = PaymentHopsSerializer

class InvoicesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Invoices.objects.all()
    serializer_class = InvoiceSerializer

class ForwardsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Forwards.objects.all()
    serializer_class = ForwardSerializer

class PeersViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Peers.objects.all()
    serializer_class = PeerSerializer

class OnchainViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Onchain.objects.all()
    serializer_class = OnchainSerializer

class PendingHTLCViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PendingHTLCs.objects.all()
    serializer_class = PendingHTLCSerializer

class FailedHTLCViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FailedHTLCs.objects.all()
    serializer_class = FailedHTLCSerializer

class LocalSettingsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LocalSettings.objects.all()
    serializer_class = LocalSettingsSerializer

    def update(self, request, pk=None):
        setting = get_object_or_404(LocalSettings.objects.all(), pk=pk)
        serializer = LocalSettingsSerializer(setting, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)

class ChannelsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Channels.objects.all()
    serializer_class = ChannelSerializer

    def update(self, request, pk=None):
        channel = get_object_or_404(Channels.objects.all(), pk=pk)
        serializer = ChannelSerializer(channel, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)

class RebalancerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Rebalancer.objects.all()
    serializer_class = RebalancerSerializer

    def create(self, request):
        serializer = RebalancerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            print(serializer.errors)
            return Response(serializer.errors)

@api_view(['POST'])
def connect_peer(request):
    serializer = ConnectPeerSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
            peer_pubkey = serializer.validated_data['peer_pubkey']
            host = serializer.validated_data['host']
            ln_addr = ln.LightningAddress()
            ln_addr.pubkey = peer_pubkey
            ln_addr.host = host
            response = stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
            return Response({'message': 'Connection successful! ' + str(response)})
        except Exception as e:
            error = str(e)
            return Response({'error': 'Connection request failed! Error: ' + error})
    else:
        return Response({'error': 'Invalid request!'})

@api_view(['POST'])
def open_channel(request):
    serializer = OpenChannelSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
            pubkey_bytes = bytes.fromhex(serializer.validated_data['peer_pubkey'])
            for response in stub.OpenChannel(ln.OpenChannelRequest(node_pubkey=pubkey_bytes, local_funding_amount=serializer.validated_data['local_amt'], sat_per_byte=serializer.validated_data['sat_per_byte'])):
                return Response({'message': 'Channel created! Funding TXID: ' + str(response.chan_pending.txid[::-1].hex()) + ':' + str(response.chan_pending.output_index)})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Channel creation failed! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'})

@api_view(['POST'])
def close_channel(request):
    serializer = CloseChannelSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
            funding_txid = serializer.validated_data['funding_txid']
            output_index = serializer.validated_data['output_index']
            target_fee = serializer.validated_data['target_fee']
            channel_point = ln.ChannelPoint()
            channel_point.funding_txid_bytes = bytes.fromhex(funding_txid)
            channel_point.funding_txid_str = funding_txid
            channel_point.output_index = output_index
            if serializer.validated_data['force']:
                for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point, force=True)):
                    return Response({'message': 'Channel force closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index)})
            else:
                for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point, sat_per_byte=target_fee)):
                    return Response({'message': 'Channel gracefully closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index)})
        except Exception as e:
            error = str(e)
            return Response({'error': 'Channel close failed! Error: ' + error})
    else:
        return Response({'error': 'Invalid request!'})

@api_view(['POST'])
def add_invoice(request):
    serializer = AddInvoiceSerializer(data=request.data)
    if serializer.is_valid() and serializer.validated_data['value'] >= 0:
        try:
            stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
            response = stub.AddInvoice(ln.Invoice(value=serializer.validated_data['value']))
            return Response({'message': 'Invoice created!', 'data':str(response.payment_request)})
        except Exception as e:
            error = str(e)
            return Response({'error': 'Invoice creation failed! Error: ' + error})
    else:
        return Response({'error': 'Invalid request!'})

@api_view(['POST'])
def new_address(request):
    try:
        stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        response = stub.NewAddress(ln.NewAddressRequest(type=0))
        return Response({'message': 'Retrieved new deposit address!', 'data':str(response.address)})
    except Exception as e:
        error = str(e)
        return Response({'error': 'Address creation failed! Error: ' + error})

@api_view(['POST'])
def update_alias(request):
    serializer = UpdateAliasSerializer(data=request.data)
    if serializer.is_valid():
        peer_pubkey = serializer.validated_data['peer_pubkey']
        if Channels.objects.filter(remote_pubkey=peer_pubkey).exists():
            try:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                new_alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey)).node.alias
                update_channels = Channels.objects.filter(remote_pubkey=peer_pubkey)
                for channel in update_channels:
                    channel.alias = new_alias
                    channel.save()
                messages.success(request, 'Alias updated to: ' + str(new_alias))
            except Exception as e:
                error = str(e)
                messages.error(request, 'Error updating alias: ' + error)
        else:
            messages.error(request, 'Pubkey not in channels list.')
    else:
        messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')