from django.shortcuts import render, redirect
from . import rpc_pb2 as ln
from . import rpc_pb2_grpc as lnrpc
import grpc
import os
import codecs

# Create your views here.
def home(request):
    if request.method == 'GET':
        with open(os.path.expanduser('admin.macaroon'), 'rb') as f:
            macaroon_bytes = f.read()
            macaroon = codecs.encode(macaroon_bytes, 'hex')
        def metadata_callback(context, callback):
            callback([('macaroon', macaroon)], None)
        os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'
        cert = open(os.path.expanduser('tls.cert'), 'rb').read()
        cert_creds = grpc.ssl_channel_credentials(cert)
        auth_creds = grpc.metadata_call_credentials(metadata_callback)
        creds = grpc.composite_channel_credentials(cert_creds, auth_creds)
        channel = grpc.secure_channel('localhost:10009', creds)
        stub = lnrpc.LightningStub(channel)
        balances = stub.WalletBalance(ln.WalletBalanceRequest())
        payments = stub.ListPayments(ln.ListPaymentsRequest(include_incomplete=True)).payments
        total_paid = 0
        for payment in payments:
            total_paid += payment.fee
        forwards = stub.ForwardingHistory(ln.ForwardingHistoryRequest(start_time=1614556800)).forwarding_events
        total_earned = 0
        for forward in forwards:
            total_earned += forward.fee_msat/1000
        active_channels = stub.ListChannels(ln.ListChannelsRequest(active_only=True)).channels
        detailed_active_channels = []
        for channel in active_channels:
            detailed_channel = {}
            alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=channel.remote_pubkey)).node.alias
            detailed_channel['remote_pubkey'] = channel.remote_pubkey
            detailed_channel['chan_id'] = channel.chan_id
            detailed_channel['capacity'] = channel.capacity
            detailed_channel['local_balance'] = channel.local_balance
            detailed_channel['remote_balance'] = channel.remote_balance
            detailed_channel['initiator'] = channel.initiator
            detailed_channel['alias'] = alias
            detailed_active_channels.append(detailed_channel)
        inactive_channels = stub.ListChannels(ln.ListChannelsRequest(inactive_only=True)).channels
        detailed_inactive_channels = []
        for channel in inactive_channels:
            detailed_channel = {}
            alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=channel.remote_pubkey)).node.alias
            detailed_channel['remote_pubkey'] = channel.remote_pubkey
            detailed_channel['chan_id'] = channel.chan_id
            detailed_channel['capacity'] = channel.capacity
            detailed_channel['local_balance'] = channel.local_balance
            detailed_channel['remote_balance'] = channel.remote_balance
            detailed_channel['initiator'] = channel.initiator
            detailed_channel['alias'] = alias
            detailed_inactive_channels.append(detailed_channel)
        context = {
            'balances': balances,
            'payments': payments,
            'paid': total_paid,
            'forwards': forwards,
            'earned': round(total_earned, 3),
            'active_channels': detailed_active_channels,
            'inactive_channels': detailed_inactive_channels
        }
        return render(request, 'home.html', context)
    else:
        return redirect('home')
