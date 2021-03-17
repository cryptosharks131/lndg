import grpc
import os
import codecs
from datetime import datetime
from django.shortcuts import render, redirect
from django.db.models import Sum
from .models import Payments, Invoices, Forwards, Channels
from . import rpc_pb2 as ln
from . import rpc_pb2_grpc as lnrpc

# Create your views here.
def home(request):
    if request.method == 'GET':
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
        #Get balance
        balances = stub.WalletBalance(ln.WalletBalanceRequest())
        #Get recorded payment events
        payments = Payments.objects.all()
        total_payments = Payments.objects.filter(status=2).count()
        total_sent = Payments.objects.aggregate(Sum('value'))['value__sum']
        total_fees = Payments.objects.aggregate(Sum('fee'))['fee__sum']
        #Get recorded invoice details
        invoices = Invoices.objects.all()
        total_invoices = Invoices.objects.filter(state=1).count()
        total_received = Invoices.objects.aggregate(Sum('amt_paid'))['amt_paid__sum']
        #Get recorded forwarding events
        forwards = Forwards.objects.all()
        total_forwards = Forwards.objects.count()
        total_earned = 0 if total_forwards == 0 else Forwards.objects.aggregate(Sum('fee'))['fee__sum']
        #Get current active channels
        active_channels = Channels.objects.filter(is_active=True, is_open=True)
        total_capacity = active_channels.aggregate(Sum('capacity'))['capacity__sum']
        total_inbound = active_channels.aggregate(Sum('remote_balance'))['remote_balance__sum']
        total_outbound = active_channels.aggregate(Sum('local_balance'))['local_balance__sum']
        detailed_active_channels = []
        for channel in active_channels:
            alias = Channels.objects.filter(chan_id=channel.chan_id)[0].alias
            detailed_channel = {}
            detailed_channel['remote_pubkey'] = channel.remote_pubkey
            detailed_channel['chan_id'] = channel.chan_id
            detailed_channel['capacity'] = channel.capacity
            detailed_channel['local_balance'] = channel.local_balance
            detailed_channel['remote_balance'] = channel.remote_balance
            detailed_channel['initiator'] = channel.initiator
            detailed_channel['alias'] = alias
            detailed_channel['base_fee'] = channel.base_fee
            detailed_channel['fee_rate'] = channel.fee_rate
            detailed_channel['visual'] = channel.local_balance / (channel.local_balance + channel.remote_balance)
            detailed_active_channels.append(detailed_channel)
        #Get current inactive channels
        inactive_channels = Channels.objects.filter(is_active=False, is_open=True)
        detailed_inactive_channels = []
        for channel in inactive_channels:
            alias = Channels.objects.filter(chan_id=channel.chan_id)[0].alias
            detailed_channel = {}
            detailed_channel['remote_pubkey'] = channel.remote_pubkey
            detailed_channel['chan_id'] = channel.chan_id
            detailed_channel['capacity'] = channel.capacity
            detailed_channel['local_balance'] = channel.local_balance
            detailed_channel['remote_balance'] = channel.remote_balance
            detailed_channel['initiator'] = channel.initiator
            detailed_channel['alias'] = alias
            detailed_channel['base_fee'] = channel.base_fee
            detailed_channel['fee_rate'] = channel.fee_rate
            detailed_inactive_channels.append(detailed_channel)
        #Build context for front-end and render page
        context = {
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
            'active_channels': detailed_active_channels,
            'capacity': total_capacity,
            'inbound': total_inbound,
            'outbound': total_outbound,
            'inactive_channels': detailed_inactive_channels
        }
        return render(request, 'home.html', context)
    else:
        return redirect('home')
