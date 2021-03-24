import grpc
import os
import codecs
from datetime import datetime
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.models import Sum
from .forms import OpenChannelForm, CloseChannelForm, ConnectPeerForm
from .models import Payments, Invoices, Forwards, Channels
from . import rpc_pb2 as ln
from . import rpc_pb2_grpc as lnrpc

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
    stub = lnrpc.LightningStub(channel)
    return stub

# Create your views here.
def home(request):
    if request.method == 'GET':
        stub = lnd_connect()
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
        payments = Payments.objects.all()
        total_payments = Payments.objects.filter(status=2).count()
        total_sent = 0 if total_payments == 0 else Payments.objects.filter(status=2).aggregate(Sum('value'))['value__sum']
        total_fees = 0 if total_payments == 0 else Payments.objects.aggregate(Sum('fee'))['fee__sum']
        #Get recorded invoice details
        invoices = Invoices.objects.all()
        total_invoices = Invoices.objects.filter(state=1).count()
        total_received = 0 if total_invoices == 0 else Invoices.objects.aggregate(Sum('amt_paid'))['amt_paid__sum']
        #Get recorded forwarding events
        forwards = Forwards.objects.all()
        total_forwards = Forwards.objects.count()
        total_value_forwards = 0 if total_forwards == 0 else Forwards.objects.aggregate(Sum('amt_out'))['amt_out__sum']
        total_earned = 0 if total_forwards == 0 else Forwards.objects.aggregate(Sum('fee'))['fee__sum']
        #Get current active channels
        active_channels = Channels.objects.filter(is_active=True, is_open=True).order_by('-alias')
        total_capacity = 0 if active_channels.count() == 0 else active_channels.aggregate(Sum('capacity'))['capacity__sum']
        total_inbound = 0 if total_capacity == 0 else active_channels.aggregate(Sum('remote_balance'))['remote_balance__sum']
        total_outbound = 0 if total_capacity == 0 else active_channels.aggregate(Sum('local_balance'))['local_balance__sum']
        detailed_active_channels = []
        for channel in active_channels:
            detailed_channel = {}
            detailed_channel['remote_pubkey'] = channel.remote_pubkey
            detailed_channel['chan_id'] = channel.chan_id
            detailed_channel['capacity'] = channel.capacity
            detailed_channel['local_balance'] = channel.local_balance
            detailed_channel['remote_balance'] = channel.remote_balance
            detailed_channel['initiator'] = channel.initiator
            detailed_channel['alias'] = channel.alias
            detailed_channel['base_fee'] = channel.base_fee
            detailed_channel['fee_rate'] = channel.fee_rate
            detailed_channel['funding_txid'] = channel.funding_txid
            detailed_channel['output_index'] = channel.output_index
            detailed_channel['visual'] = channel.local_balance / (channel.local_balance + channel.remote_balance)
            detailed_active_channels.append(detailed_channel)
        #Get current inactive channels
        inactive_channels = Channels.objects.filter(is_active=False, is_open=True).order_by('-fee_rate').order_by('-alias')
        #Build context for front-end and render page
        context = {
            'node_info': node_info,
            'balances': balances,
            'payments': payments,
            'total_sent': total_sent,
            'fees_paid': round(total_fees, 3),
            'total_payments': total_payments,
            'invoices': invoices,
            'total_received': total_received,
            'total_invoices': total_invoices,
            'forwards': forwards,
            'earned': round(total_earned, 3),
            'total_forwards': total_forwards,
            'total_value_forwards': total_value_forwards,
            'active_channels': detailed_active_channels,
            'capacity': total_capacity,
            'inbound': total_inbound,
            'outbound': total_outbound,
            'limbo_balance': limbo_balance,
            'inactive_channels': inactive_channels,
            'pending_open': pending_open,
            'pending_closed': pending_closed,
            'pending_force_closed': pending_force_closed,
            'waiting_for_close': waiting_for_close,
            'peers': peers
        }
        return render(request, 'home.html', context)
    else:
        return redirect('home')

def open_channel(request):
    if request.method == 'POST':
        form = OpenChannelForm(request.POST)
        if form.is_valid():
            stub = lnd_connect()
            pubkey_bytes = bytes.fromhex(form.cleaned_data['peer_pubkey'])
            try:
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
            stub = lnd_connect()
            funding_txid = form.cleaned_data['funding_txid']
            output_index = form.cleaned_data['output_index']
            channel_point = ln.ChannelPoint()
            channel_point.funding_txid_bytes = bytes.fromhex(funding_txid)
            channel_point.funding_txid_str = funding_txid
            channel_point.output_index = output_index
            try:
                for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point)):
                    messages.success(request, 'Channel closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index))
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
            stub = lnd_connect()
            peer_pubkey = form.cleaned_data['peer_pubkey']
            host = form.cleaned_data['host']
            ln_addr = ln.LightningAddress()
            ln_addr.pubkey = peer_pubkey
            ln_addr.host = host
            try:
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
        stub = lnd_connect()
        try:
            response = stub.NewAddress(ln.NewAddressRequest(type=0))
            messages.success(request, 'Deposit Address: ' + str(response.address))
        except Exception as e:
            error = str(e)
            messages.error(request, 'Address request! Error: ' + error)
        return redirect('home')
    else:
        return redirect('home')
