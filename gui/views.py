import grpc
import os
import codecs
from datetime import datetime
from django.shortcuts import render, redirect
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
        #Get payment events
        payments = stub.ListPayments(ln.ListPaymentsRequest(include_incomplete=True)).payments
        total_paid = 0
        total_payments = 0
        detailed_payments = []
        for payment in payments:
            total_paid += payment.fee
            total_payments += 1
            detailed_payment = {}
            detailed_payment['creation_date'] = datetime.fromtimestamp(payment.creation_date)
            detailed_payment['payment_hash'] = payment.payment_hash
            detailed_payment['value'] = payment.value
            detailed_payment['fee'] = payment.fee
            detailed_payment['status'] = payment.status
            detailed_payments.append(detailed_payment)
        #Get forwarding events
        forwards = stub.ForwardingHistory(ln.ForwardingHistoryRequest(start_time=1614556800)).forwarding_events
        total_earned = 0
        total_forwards = 0
        detailed_forwards = []
        for forward in forwards:
            total_earned += forward.fee_msat/1000
            total_forwards += 1
            detailed_forward = {}
            detailed_forward['timestamp'] = datetime.fromtimestamp(forward.timestamp)
            detailed_forward['chan_id_in'] = forward.chan_id_in
            detailed_forward['chan_id_out'] = forward.chan_id_out
            detailed_forward['amt_in'] = forward.amt_in
            detailed_forward['amt_out'] = forward.amt_out
            detailed_forward['fee_msat'] = round(forward.fee_msat/1000, 3)
            detailed_forwards.append(detailed_forward)
        #Get active channels
        active_channels = stub.ListChannels(ln.ListChannelsRequest(active_only=True)).channels
        total_capacity = 0
        total_inbound = 0
        total_outbound = 0
        detailed_active_channels = []
        for channel in active_channels:
            total_capacity += channel.capacity
            total_inbound += channel.remote_balance
            total_outbound += channel.local_balance
            alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=channel.remote_pubkey)).node.alias
            detailed_channel = {}
            detailed_channel['remote_pubkey'] = channel.remote_pubkey
            detailed_channel['chan_id'] = channel.chan_id
            detailed_channel['capacity'] = channel.capacity
            detailed_channel['local_balance'] = channel.local_balance
            detailed_channel['remote_balance'] = channel.remote_balance
            detailed_channel['initiator'] = channel.initiator
            detailed_channel['alias'] = alias
            detailed_active_channels.append(detailed_channel)
        #Get inactive channels
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
        #Build context for front-end and render page
        context = {
            'balances': balances,
            'payments': detailed_payments,
            'paid': total_paid,
            'total_payments': total_payments,
            'forwards': detailed_forwards,
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
