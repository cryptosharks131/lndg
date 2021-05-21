import grpc, os, codecs
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.models import Sum
from rest_framework import viewsets
from .forms import OpenChannelForm, CloseChannelForm, ConnectPeerForm, AddInvoiceForm, RebalancerForm, ChanPolicyForm, AutoRebalanceForm
from .models import Payments, PaymentHops, Invoices, Forwards, Channels, Rebalancer, LocalSettings
from .serializers import PaymentSerializer, InvoiceSerializer, ForwardSerializer, ChannelSerializer, RebalancerSerializer
from . import rpc_pb2 as ln
from . import rpc_pb2_grpc as lnrpc
from . import router_pb2 as lnr
from . import router_pb2_grpc as lnrouter

#Define lnd connection for repeated use
def lnd_connect():
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
    return channel

# Create your views here.
def home(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect())
        #Get balance and peers
        node_info = stub.GetInfo(ln.GetInfoRequest())
        balances = stub.WalletBalance(ln.WalletBalanceRequest())
        peers = stub.ListPeers(ln.ListPeersRequest()).peers
        pending_channels = stub.PendingChannels(ln.PendingChannelsRequest())
        limbo_balance = pending_channels.total_limbo_balance
        pending_open = pending_channels.pending_open_channels
        pending_closed = pending_channels.pending_closing_channels
        pending_force_closed = pending_channels.pending_force_closing_channels
        waiting_for_close = pending_channels.waiting_close_channels
        #Get recorded payment events
        payments = Payments.objects.exclude(status=3).order_by('-creation_date')
        total_payments = Payments.objects.filter(status=2).count()
        total_sent = 0 if total_payments == 0 else Payments.objects.filter(status=2).aggregate(Sum('value'))['value__sum']
        total_fees = 0 if total_payments == 0 else Payments.objects.aggregate(Sum('fee'))['fee__sum']
        #Get recorded invoice details
        invoices = Invoices.objects.exclude(state=2).order_by('-creation_date')
        total_invoices = Invoices.objects.filter(state=1).count()
        total_received = 0 if total_invoices == 0 else Invoices.objects.aggregate(Sum('amt_paid'))['amt_paid__sum']
        #Get recorded forwarding events
        forwards = Forwards.objects.all().order_by('-forward_date')
        total_forwards = Forwards.objects.count()
        total_value_forwards = 0 if total_forwards == 0 else int(Forwards.objects.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        total_earned = 0 if total_forwards == 0 else Forwards.objects.aggregate(Sum('fee'))['fee__sum']
        #Get current active channels
        active_channels = Channels.objects.filter(is_active=True, is_open=True).annotate(ordering=(Sum('local_balance')*100)/Sum('capacity')).order_by('ordering')
        total_capacity = 0 if active_channels.count() == 0 else active_channels.aggregate(Sum('capacity'))['capacity__sum']
        total_inbound = 0 if total_capacity == 0 else active_channels.aggregate(Sum('remote_balance'))['remote_balance__sum']
        total_outbound = 0 if total_capacity == 0 else active_channels.aggregate(Sum('local_balance'))['local_balance__sum']
        total_unsettled = 0 if total_capacity == 0 else active_channels.aggregate(Sum('unsettled_balance'))['unsettled_balance__sum']
        detailed_active_channels = []
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
            detailed_channel['base_fee'] = channel.base_fee
            detailed_channel['fee_rate'] = channel.fee_rate
            detailed_channel['funding_txid'] = channel.funding_txid
            detailed_channel['output_index'] = channel.output_index
            detailed_channel['visual'] = channel.local_balance / (channel.local_balance + channel.remote_balance)
            detailed_channel['outbound_percent'] = int(round(detailed_channel['visual'] * 100, 0))
            detailed_channel['inbound_percent'] = int(round((1-detailed_channel['visual']) * 100, 0))
            detailed_channel['routed_in'] = forwards.filter(chan_id_in=channel.chan_id).count()
            detailed_channel['routed_out'] = forwards.filter(chan_id_out=channel.chan_id).count()
            detailed_channel['amt_routed_in'] = 0 if detailed_channel['routed_in'] == 0 else int(forwards.filter(chan_id_in=channel.chan_id).aggregate(Sum('amt_in_msat'))['amt_in_msat__sum']/1000)
            detailed_channel['amt_routed_out'] = 0 if detailed_channel['routed_out'] == 0 else int(forwards.filter(chan_id_out=channel.chan_id).aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
            detailed_channel['auto_rebalance'] = channel.auto_rebalance
            detailed_active_channels.append(detailed_channel)
        #Get current inactive channels
        inactive_channels = Channels.objects.filter(is_active=False, is_open=True).order_by('-fee_rate').order_by('-alias')
        #Get list of recent rebalance requests
        rebalances = Rebalancer.objects.all().order_by('-requested')
        #Grab local settings
        local_settings = LocalSettings.objects.all()
        #Build context for front-end and render page
        context = {
            'node_info': node_info,
            'balances': balances,
            'payments': payments[:5],
            'total_sent': total_sent,
            'fees_paid': round(total_fees, 3),
            'total_payments': total_payments,
            'invoices': invoices[:5],
            'total_received': total_received,
            'total_invoices': total_invoices,
            'forwards': forwards[:10],
            'earned': round(total_earned, 3),
            'total_forwards': total_forwards,
            'total_value_forwards': total_value_forwards,
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
            'peers': peers,
            'rebalances': rebalances[:10],
            'rebalancer_form': RebalancerForm,
            'chan_policy_form': ChanPolicyForm,
            'local_settings': local_settings,
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

def open_channel(request):
    if request.method == 'POST':
        form = OpenChannelForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
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
            return redirect('home')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
            return redirect('home')
    else:
        return redirect('home')

def close_channel(request):
    if request.method == 'POST':
        form = CloseChannelForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
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
                messages.error(request, 'Channel creation failed! Error: ' + error)
            return redirect('home')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
            return redirect('home')
    else:
        return redirect('home')

def connect_peer(request):
    if request.method == 'POST':
        form = ConnectPeerForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
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
            return redirect('home')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
            return redirect('home')
    else:
        return redirect('home')

def new_address(request):
    if request.method == 'POST':
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            response = stub.NewAddress(ln.NewAddressRequest(type=0))
            messages.success(request, 'Deposit Address: ' + str(response.address))
        except Exception as e:
            error = str(e)
            messages.error(request, 'Address request! Error: ' + error)
        return redirect('home')
    else:
        return redirect('home')

def add_invoice(request):
    if request.method == 'POST':
        form = AddInvoice(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
                response = stub.AddInvoice(ln.Invoice(value=form.cleaned_data['value']))
                messages.success(request, 'Invoice created! ' + str(response.payment_request))
            except Exception as e:
                error = str(e)
                messages.error(request, 'Invoice creation failed! Error: ' + error)
            return redirect('home')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
            return redirect('home')
    else:
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
            return redirect('home')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
            return redirect('home')
    else:
        return redirect('home')

def update_chan_policy(request):
    if request.method == 'POST':
        form = ChanPolicyForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
                if form.cleaned_data['target_all']:
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(update_all=True, base_fee_msat=form.cleaned_data['new_base_fee'], fee_rate=(form.cleaned_data['new_fee_rate']/1000000), time_lock_delta=40))
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
            return redirect('home')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
            print(form.errors)
            return redirect('home')
    else:
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
                    LocalSettings(key='AR-Time', value='20').save()
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
                messages.success(request, 'Updated auto rebalancer value sent per 1 sat fee setting to: ' + str(fee_rate))
            return redirect('home')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
            return redirect('home')
    else:
        return redirect('home')

class PaymentsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payments.objects.all()
    serializer_class = PaymentSerializer

class InvoicesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Invoices.objects.all()
    serializer_class = InvoiceSerializer

class ForwardsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Forwards.objects.all()
    serializer_class = ForwardSerializer

class ChannelsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Channels.objects.all()
    serializer_class = ChannelSerializer

class RebalancerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Rebalancer.objects.all()
    serializer_class = RebalancerSerializer

    def create(self, request):
        serializer = RebalancerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return redirect('api-root')
        else:
            print(serializer.errors)
            return redirect('api-root')