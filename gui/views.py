from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Sum, IntegerField, Count
from django.db.models.functions import Round
from django.contrib.auth.decorators import login_required
from django.conf import settings
from datetime import datetime, timedelta
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .forms import OpenChannelForm, CloseChannelForm, ConnectPeerForm, AddInvoiceForm, RebalancerForm, ChanPolicyForm, AutoRebalanceForm, ARTarget
from .models import Payments, PaymentHops, Invoices, Forwards, Channels, Rebalancer, LocalSettings, Peers, Onchain, PendingHTLCs, FailedHTLCs, Autopilot
from .serializers import ConnectPeerSerializer, FailedHTLCSerializer, LocalSettingsSerializer, OpenChannelSerializer, CloseChannelSerializer, AddInvoiceSerializer, PaymentHopsSerializer, PaymentSerializer, InvoiceSerializer, ForwardSerializer, ChannelSerializer, PendingHTLCSerializer, RebalancerSerializer, UpdateAliasSerializer, PeerSerializer, OnchainSerializer, PendingHTLCs, FailedHTLCs
from .lnd_deps import lightning_pb2 as ln
from .lnd_deps import lightning_pb2_grpc as lnrpc
from .lnd_deps.lnd_connect import lnd_connect
from lndg.settings import LND_NETWORK, LND_DIR_PATH
from os import path
from pandas import DataFrame

@login_required(login_url='/lndg-admin/login/?next=/')
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
        payments_7day = payments.filter(status=2).filter(creation_date__gte=filter_7day)
        payments_7day_amt = 0 if payments_7day.count() == 0 else payments_7day.aggregate(Sum('value'))['value__sum']
        total_7day_fees = 0 if payments_7day.count() == 0 else payments_7day.aggregate(Sum('fee'))['fee__sum']
        pending_htlcs = PendingHTLCs.objects.all()
        pending_htlc_count = pending_htlcs.count()
        pending_outbound = 0 if pending_htlcs.filter(incoming=False).count() == 0 else pending_htlcs.filter(incoming=False).aggregate(Sum('amount'))['amount__sum']
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
        total_channels = node_info.num_active_channels + node_info.num_inactive_channels
        local_settings = LocalSettings.objects.all()
        try:
            db_size = round(path.getsize(path.expanduser(LND_DIR_PATH + '/data/graph/' + LND_NETWORK + '/channel.db'))*0.000000001, 3)
        except:
            db_size = 0
        #Build context for front-end and render page
        context = {
            'node_info': node_info,
            'total_channels': total_channels,
            'balances': balances,
            'payments': payments[:6],
            'total_sent': int(total_sent),
            'fees_paid': int(total_fees),
            'total_payments': total_payments,
            'invoices': invoices[:6],
            'total_received': total_received,
            'total_invoices': total_invoices,
            'forwards': forwards[:15],
            'earned': int(total_earned),
            'total_forwards': total_forwards,
            'total_value_forwards': total_value_forwards,
            'routed_7day': routed_7day,
            'routed_7day_amt': routed_7day_amt,
            'earned_7day': int(total_earned_7day),
            'routed_7day_percent': 0 if sum_outbound == 0 else int((routed_7day_amt/sum_outbound)*100),
            'profit_per_outbound': 0 if sum_outbound == 0 else int((total_earned_7day - total_7day_fees)/(sum_outbound/1000000)),
            'profit_per_outbound_real': 0 if sum_outbound == 0 else int((total_earned_7day - total_costs_7day)/(sum_outbound/1000000)),
            'percent_cost': 0 if total_earned == 0 else int((total_costs/total_earned)*100),
            'percent_cost_7day': 0 if total_earned_7day == 0 else int((total_costs_7day/total_earned_7day)*100),
            'onchain_costs': onchain_costs,
            'onchain_costs_7day': onchain_costs_7day,
            'total_7day_fees': int(total_7day_fees),
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
            'failed_htlcs': FailedHTLCs.objects.all().order_by('-timestamp')[:10],
            'payments_ppm': 0 if total_sent == 0 else int((total_fees/total_sent)*1000000),
            'routed_ppm': 0 if total_value_forwards == 0 else int((total_earned/total_value_forwards)*1000000),
            '7day_routed_ppm': 0 if routed_7day_amt == 0 else int((total_earned_7day/routed_7day_amt)*1000000),
            '7day_payments_ppm': 0 if payments_7day_amt == 0 else int((total_7day_fees/payments_7day_amt)*1000000),
            'liq_ratio': 0 if total_outbound == 0 else int((total_inbound/sum_outbound)*100),
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'db_size': db_size
        }
        return render(request, 'home.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def channels(request):
    if request.method == 'GET':
        filter_7day = datetime.now() - timedelta(days=7)
        filter_30day = datetime.now() - timedelta(days=30)
        forwards = Forwards.objects.filter(forward_date__gte=filter_30day)
        payments = Payments.objects.filter(status=2).filter(creation_date__gte=filter_30day).filter(payment_hash__in=Invoices.objects.filter(state=1).filter(settle_date__gte=filter_30day).values_list('r_hash'))
        invoices = Invoices.objects.filter(state=1).filter(settle_date__gte=filter_30day).filter(r_hash__in=payments.values_list('payment_hash'))
        channels = Channels.objects.filter(is_open=True)
        channels_df = DataFrame.from_records(channels.values())
        forwards_df_30d = DataFrame.from_records(forwards.values())
        forwards_df_7d = DataFrame.from_records(forwards.filter(forward_date__gte=filter_7day).values())
        forwards_df_in_30d_sum = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_in', as_index=True).sum()
        forwards_df_out_30d_sum = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_out', as_index=True).sum()
        forwards_df_in_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_in', as_index=True).sum()
        forwards_df_out_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_out', as_index=True).sum()
        forwards_df_in_30d_count = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_in', as_index=True).count()
        forwards_df_out_30d_count = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_out', as_index=True).count()
        forwards_df_in_7d_count = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_in', as_index=True).count()
        forwards_df_out_7d_count = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_out', as_index=True).count()
        payments_df_30d = DataFrame.from_records(payments.values())
        payments_df_7d = DataFrame.from_records(payments.filter(creation_date__gte=filter_7day).values())
        payments_df_30d_sum = DataFrame() if payments_df_30d.empty else payments_df_30d.groupby('chan_out', as_index=True).sum()
        payments_df_7d_sum = DataFrame() if payments_df_7d.empty else payments_df_7d.groupby('chan_out', as_index=True).sum()
        payments_df_30d_count = DataFrame() if payments_df_30d.empty else payments_df_30d.groupby('chan_out', as_index=True).count()
        payments_df_7d_count = DataFrame() if payments_df_7d.empty else payments_df_7d.groupby('chan_out', as_index=True).count()
        invoices_df_30d = DataFrame.from_records(invoices.values())
        invoices_df_7d = DataFrame.from_records(invoices.filter(settle_date__gte=filter_7day).values())
        invoices_df_30d_sum = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True).sum()
        invoices_df_7d_sum = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).sum()
        invoices_df_30d_count = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True).count()
        invoices_df_7d_count = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).count()
        invoice_hashes_7d = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True)['r_hash'].apply(list)
        invoice_hashes_30d = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True)['r_hash'].apply(list)
        detailed_channels = []
        for channel in channels_df.itertuples():
            detailed_channel = {}
            detailed_channel['remote_pubkey'] = channel.remote_pubkey
            detailed_channel['chan_id'] = channel.chan_id
            detailed_channel['capacity'] = round(channel.capacity/1000000, 1)
            detailed_channel['initiator'] = channel.initiator
            detailed_channel['alias'] = channel.alias
            detailed_channel['local_base_fee'] = channel.local_base_fee
            detailed_channel['local_fee_rate'] = channel.local_fee_rate
            detailed_channel['remote_base_fee'] = channel.remote_base_fee
            detailed_channel['remote_fee_rate'] = channel.remote_fee_rate
            detailed_channel['funding_txid'] = channel.funding_txid
            detailed_channel['output_index'] = channel.output_index
            detailed_channel['num_updates'] = channel.num_updates
            detailed_channel['is_active'] = channel.is_active
            detailed_channel['routed_in_7day'] = forwards_df_in_7d_count.loc[channel.chan_id].amt_in_msat if (forwards_df_in_7d_count.index == channel.chan_id).any() else 0
            detailed_channel['routed_out_7day'] = forwards_df_out_7d_count.loc[channel.chan_id].amt_out_msat if (forwards_df_out_7d_count.index == channel.chan_id).any() else 0
            detailed_channel['routed_in_30day'] = forwards_df_in_30d_count.loc[channel.chan_id].amt_in_msat if (forwards_df_in_30d_count.index == channel.chan_id).any() else 0
            detailed_channel['routed_out_30day'] = forwards_df_out_30d_count.loc[channel.chan_id].amt_out_msat if (forwards_df_out_30d_count.index == channel.chan_id).any() else 0
            detailed_channel['amt_routed_in_7day'] = int(forwards_df_in_7d_sum.loc[channel.chan_id].amt_out_msat/100000000)/10 if (forwards_df_in_7d_sum.index == channel.chan_id).any() else 0
            detailed_channel['amt_routed_out_7day'] = int(forwards_df_out_7d_sum.loc[channel.chan_id].amt_out_msat/100000000)/10 if (forwards_df_out_7d_sum.index == channel.chan_id).any() else 0
            detailed_channel['amt_routed_in_30day'] = int(forwards_df_in_30d_sum.loc[channel.chan_id].amt_out_msat/100000000)/10 if (forwards_df_in_30d_sum.index == channel.chan_id).any() else 0
            detailed_channel['amt_routed_out_30day'] = int(forwards_df_out_30d_sum.loc[channel.chan_id].amt_out_msat/100000000)/10 if (forwards_df_out_30d_sum.index == channel.chan_id).any() else 0
            detailed_channel['rebal_in_30day'] = invoices_df_30d_count.loc[channel.chan_id].amt_paid if invoices_df_30d_count.empty == False and (invoices_df_30d_count.index == channel.chan_id).any() else 0
            detailed_channel['rebal_out_30day'] = payments_df_30d_count.loc[channel.chan_id].value if payments_df_30d_count.empty == False and (payments_df_30d_count.index == channel.chan_id).any() else 0
            detailed_channel['amt_rebal_in_30day'] = int(invoices_df_30d_sum.loc[channel.chan_id].amt_paid/100000)/10 if invoices_df_30d_count.empty == False and (invoices_df_30d_sum.index == channel.chan_id).any() else 0
            detailed_channel['amt_rebal_out_30day'] = int(payments_df_30d_sum.loc[channel.chan_id].value/100000)/10 if payments_df_30d_count.empty == False and (payments_df_30d_sum.index == channel.chan_id).any() else 0
            detailed_channel['rebal_in_7day'] = invoices_df_7d_count.loc[channel.chan_id].amt_paid if invoices_df_7d_count.empty == False and (invoices_df_7d_count.index == channel.chan_id).any() else 0
            detailed_channel['rebal_out_7day'] = payments_df_7d_count.loc[channel.chan_id].value if payments_df_7d_count.empty == False and (payments_df_7d_count.index == channel.chan_id).any() else 0
            detailed_channel['amt_rebal_in_7day'] = int(invoices_df_7d_sum.loc[channel.chan_id].amt_paid/100000)/10 if invoices_df_7d_count.empty == False and (invoices_df_7d_sum.index == channel.chan_id).any() else 0
            detailed_channel['amt_rebal_out_7day'] = int(payments_df_7d_sum.loc[channel.chan_id].value/100000)/10 if payments_df_7d_count.empty == False and (payments_df_7d_sum.index == channel.chan_id).any() else 0
            detailed_channel['revenue_7day'] = int(forwards_df_out_7d_sum.loc[channel.chan_id].fee) if forwards_df_out_7d_sum.empty == False and (forwards_df_out_7d_sum.index == channel.chan_id).any() else 0
            detailed_channel['revenue_30day'] = int(forwards_df_out_30d_sum.loc[channel.chan_id].fee) if forwards_df_out_30d_sum.empty == False and (forwards_df_out_30d_sum.index == channel.chan_id).any() else 0
            detailed_channel['revenue_assist_7day'] = int(forwards_df_in_7d_sum.loc[channel.chan_id].fee) if forwards_df_in_7d_sum.empty == False and (forwards_df_in_7d_sum.index == channel.chan_id).any() else 0
            detailed_channel['revenue_assist_30day'] = int(forwards_df_in_30d_sum.loc[channel.chan_id].fee) if forwards_df_in_30d_sum.empty == False and (forwards_df_in_30d_sum.index == channel.chan_id).any() else 0
            detailed_channel['costs_7day'] = 0 if detailed_channel['rebal_in_7day'] == 0 else int(payments_df_7d.set_index('payment_hash', inplace=False).loc[invoice_hashes_7d[channel.chan_id] if invoice_hashes_7d.empty == False and (invoice_hashes_7d.index == channel.chan_id).any() else []]['fee'].sum())
            detailed_channel['costs_30day'] = 0 if detailed_channel['rebal_in_30day'] == 0 else int(payments_df_30d.set_index('payment_hash', inplace=False).loc[invoice_hashes_30d[channel.chan_id] if invoice_hashes_30d.empty == False and (invoice_hashes_30d.index == channel.chan_id).any() else []]['fee'].sum())
            detailed_channel['profits_7day'] = 0 if detailed_channel['revenue_7day'] == 0 else detailed_channel['revenue_7day'] - detailed_channel['costs_7day']
            detailed_channel['profits_30day'] = 0 if detailed_channel['revenue_30day'] == 0 else detailed_channel['revenue_30day'] - detailed_channel['costs_30day']
            detailed_channel['open_block'] = channel.chan_id>>40
            detailed_channels.append(detailed_channel)
        context = {
            'channels': detailed_channels,
            'network': 'testnet/' if LND_NETWORK == 'testnet' else ''
        }
        return render(request, 'channels.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def route(request):
    if request.method == 'GET':
        payment_hash = request.GET.urlencode()[1:]
        context = {
            'payment_hash': payment_hash,
            'route': PaymentHops.objects.filter(payment_hash=payment_hash).annotate(ppm=Round((Sum('fee')/Sum('amt'))*1000000, output_field=IntegerField()))
        }
        return render(request, 'route.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def peers(request):
    if request.method == 'GET':
        context = {
            'peers': Peers.objects.filter(connected=True)
        }
        return render(request, 'peers.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
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

@login_required(login_url='/lndg-admin/login/?next=/')
def suggested_opens(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        self_pubkey = stub.GetInfo(ln.GetInfoRequest()).identity_pubkey
        current_peers = Channels.objects.filter(is_open=True).values_list('remote_pubkey')
        filter_60day = datetime.now() - timedelta(days=60)
        payments_60day = Payments.objects.filter(creation_date__gte=filter_60day).values_list('payment_hash')
        open_list = PaymentHops.objects.filter(payment_hash__in=payments_60day).exclude(node_pubkey=self_pubkey).exclude(node_pubkey__in=current_peers).values('node_pubkey', 'alias').annotate(ppm=(Sum('fee')/Sum('amt'))*1000000).annotate(score=Round((Round(Count('id')/5, output_field=IntegerField())+Round(Sum('amt')/500000, output_field=IntegerField()))/10, output_field=IntegerField())).annotate(count=Count('id')).annotate(amount=Sum('amt')).annotate(fees=Sum('fee')).annotate(sum_cost_to=Sum('cost_to')/(Sum('amt')/1000000)).order_by('-score', 'ppm')[:21]
        context = {
            'open_list': open_list
        }
        return render(request, 'open_list.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def suggested_actions(request):
    if request.method == 'GET':
        channels = Channels.objects.filter(is_active=True, is_open=True).annotate(outbound_percent=(Sum('local_balance')*1000)/Sum('capacity')).annotate(inbound_percent=(Sum('remote_balance')*1000)/Sum('capacity'))
        filter_7day = datetime.now() - timedelta(days=7)
        forwards = Forwards.objects.filter(forward_date__gte=filter_7day)
        action_list = []
        for channel in channels:
            result = {}
            result['chan_id'] = channel.chan_id
            result['alias'] = channel.alias
            result['capacity'] = channel.capacity
            result['local_balance'] = channel.local_balance
            result['remote_balance'] = channel.remote_balance
            result['outbound_percent'] = int(round(channel.outbound_percent/10, 0))
            result['inbound_percent'] = int(round(channel.inbound_percent/10, 0))
            result['unsettled_balance'] = channel.unsettled_balance
            result['local_base_fee'] = channel.local_base_fee
            result['local_fee_rate'] = channel.local_fee_rate
            result['remote_base_fee'] = channel.remote_base_fee
            result['remote_fee_rate'] = channel.remote_fee_rate
            result['routed_in_7day'] = forwards.filter(chan_id_in=channel.chan_id).count()
            result['routed_out_7day'] = forwards.filter(chan_id_out=channel.chan_id).count()
            result['i7D'] = 0 if result['routed_in_7day'] == 0 else int(forwards.filter(chan_id_in=channel.chan_id).aggregate(Sum('amt_in_msat'))['amt_in_msat__sum']/10000000)/100
            result['o7D'] = 0 if result['routed_out_7day'] == 0 else int(forwards.filter(chan_id_out=channel.chan_id).aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/10000000)/100
            result['auto_rebalance'] = channel.auto_rebalance
            result['ar_target'] = channel.ar_target
            if result['o7D'] > (result['i7D']*1.10) and result['outbound_percent'] > 75:
                print('Case 1: Pass')
                continue
            elif result['o7D'] > (result['i7D']*1.10) and result['inbound_percent'] > 75 and channel.auto_rebalance == False:
                if channel.local_fee_rate <= channel.remote_fee_rate:
                    print('Case 6: Peer Fee Too High')
                    result['output'] = 'Peer Fee Too High'
                    result['reason'] = 'o7D > i7D AND Inbound Liq > 75% AND Local Fee < Remote Fee'
                    continue
                print('Case 2: Enable AR')
                result['output'] = 'Enable AR'
                result['reason'] = 'o7D > i7D AND Inbound Liq > 75%'
            elif result['o7D'] < (result['i7D']*1.10) and result['outbound_percent'] > 75 and channel.auto_rebalance == True:
                print('Case 3: Disable AR')
                result['output'] = 'Disable AR'
                result['reason'] = 'o7D < i7D AND Outbound Liq > 75%'
            elif result['o7D'] < (result['i7D']*1.10) and result['inbound_percent'] > 75:
                print('Case 4: Pass')
                continue
            else:
                print('Case 5: Pass')
                continue
            if len(result) > 0:
                action_list.append(result) 
        context = {
            'action_list': action_list
        }
        return render(request, 'action_list.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def pending_htlcs(request):
    if request.method == 'GET':
        context = {
            'incoming_htlcs': PendingHTLCs.objects.filter(incoming=True).order_by('hash_lock'),
            'outgoing_htlcs': PendingHTLCs.objects.filter(incoming=False).order_by('hash_lock')
        }
        return render(request, 'pending_htlcs.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def keysends(request):
    if request.method == 'GET':
        context = {
            'keysends': Invoices.objects.filter(keysend_preimage__isnull=False).order_by('-settle_date')
        }
        return render(request, 'keysends.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def autopilot(request):
    if request.method == 'GET':
        context = {
            'autopilot': Autopilot.objects.all().order_by('-timestamp')
        }
        return render(request, 'autopilot.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def open_channel_form(request):
    if request.method == 'POST':
        form = OpenChannelForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                peer_pubkey = form.cleaned_data['peer_pubkey']
                connected = False
                if Peers.objects.filter(pubkey=peer_pubkey, connected=True).exists():
                    connected = True
                else:
                    try:
                        node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey, include_channels=False)).node
                        host = node.addresses[0].addr
                        ln_addr = ln.LightningAddress(pubkey=peer_pubkey, host=host)
                        response = stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
                        connected = True
                    except Exception as e:
                        error = str(e)
                        details_index = error.find('details =') + 11
                        debug_error_index = error.find('debug_error_string =') - 3
                        error_msg = error[details_index:debug_error_index]
                        messages.error(request, 'Error connecting to new peer: ' + error_msg)
                if connected:
                    for response in stub.OpenChannel(ln.OpenChannelRequest(node_pubkey=bytes.fromhex(peer_pubkey), local_funding_amount=form.cleaned_data['local_amt'], sat_per_byte=form.cleaned_data['sat_per_byte'])):
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

@login_required(login_url='/lndg-admin/login/?next=/')
def close_channel_form(request):
    if request.method == 'POST':
        form = CloseChannelForm(request.POST)
        if form.is_valid():
            try:
                chan_id = form.cleaned_data['chan_id']
                if Channels.objects.filter(chan_id=chan_id).exists():
                    target_channel = Channels.objects.filter(chan_id=chan_id).get()
                    funding_txid = target_channel.funding_txid
                    output_index = target_channel.output_index
                    target_fee = form.cleaned_data['target_fee']
                    channel_point = ln.ChannelPoint()
                    channel_point.funding_txid_bytes = bytes.fromhex(funding_txid)
                    channel_point.funding_txid_str = funding_txid
                    channel_point.output_index = output_index
                    stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                    if form.cleaned_data['force']:
                        for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point, force=True)):
                            messages.success(request, 'Channel force closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index))
                            break
                    else:
                        for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point, sat_per_byte=target_fee)):
                            messages.success(request, 'Channel gracefully closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index))
                            break
                else:
                    messages.error(request, 'Channel ID is not valid. Please try again.')
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Channel close failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def connect_peer_form(request):
    if request.method == 'POST':
        form = ConnectPeerForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                peer_id = form.cleaned_data['peer_id']
                if peer_id.count('@') == 0 and len(peer_id) == 66:
                    peer_pubkey = peer_id
                    node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey, include_channels=False)).node
                    host = node.addresses[0].addr
                elif peer_id.count('@') == 1 and len(peer_id.split('@')[0]) == 66:
                    peer_pubkey, host = peer_id.split('@')
                else:
                    raise Exception('Invalid peer pubkey or connection string.')
                ln_addr = ln.LightningAddress(pubkey=peer_pubkey, host=host)
                response = stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
                messages.success(request, 'Connection successful!' + str(response))
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Connection request failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def new_address_form(request):
    if request.method == 'POST':
        try:
            stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
            response = stub.NewAddress(ln.NewAddressRequest(type=0))
            messages.success(request, 'Deposit Address: ' + str(response.address))
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            messages.error(request, 'Address request failed! Error: ' + error_msg)
    return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
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
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Invoice creation failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def rebalance(request):
    if request.method == 'POST':
        form = RebalancerForm(request.POST)
        if form.is_valid():
            try:
                if Channels.objects.filter(is_active=True, is_open=True, remote_pubkey=form.cleaned_data['last_hop_pubkey']).exists() or form.cleaned_data['last_hop_pubkey'] == '':
                    chan_ids = []
                    for channel in form.cleaned_data['outgoing_chan_ids']:
                        chan_ids.append(channel.chan_id)
                    target_alias = Channels.objects.filter(is_active=True, is_open=True, remote_pubkey=form.cleaned_data['last_hop_pubkey'])[0].alias if Channels.objects.filter(is_active=True, is_open=True, remote_pubkey=form.cleaned_data['last_hop_pubkey']).exists() else ''
                    Rebalancer(value=form.cleaned_data['value'], fee_limit=form.cleaned_data['fee_limit'], outgoing_chan_ids=chan_ids, last_hop_pubkey=form.cleaned_data['last_hop_pubkey'], target_alias=target_alias, duration=form.cleaned_data['duration']).save()
                    messages.success(request, 'Rebalancer request created!')
                else:
                    messages.error(request, 'Target peer is invalid or unknown.')
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Error entering rebalancer request! Error: ' + error)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
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
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Error updating channel policies! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
            print(form.errors)
    return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
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
                    LocalSettings(key='AR-Target%', value='0.05').save()
                    db_percent_target = LocalSettings.objects.get(key='AR-Target%')
                db_percent_target.value = target_percent
                db_percent_target.save()
                messages.success(request, 'Updated auto rebalancer rebalance target percent setting to: ' + str(target_percent))
            if form.cleaned_data['target_time'] is not None:
                target_time = form.cleaned_data['target_time']
                try:
                    db_time_target = LocalSettings.objects.get(key='AR-Time')
                except:
                    LocalSettings(key='AR-Time', value='5').save()
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
                    LocalSettings(key='AR-Outbound%', value='0.75').save()
                    db_outbound_target = LocalSettings.objects.get(key='AR-Outbound%')
                db_outbound_target.value = outbound_percent
                db_outbound_target.save()
                messages.success(request, 'Updated auto rebalancer target outbound percent setting to: ' + str(outbound_percent))
            if form.cleaned_data['fee_rate'] is not None:
                fee_rate = form.cleaned_data['fee_rate']
                try:
                    db_fee_rate = LocalSettings.objects.get(key='AR-MaxFeeRate')
                except:
                    LocalSettings(key='AR-MaxFeeRate', value='100').save()
                    db_fee_rate = LocalSettings.objects.get(key='AR-MaxFeeRate')
                db_fee_rate.value = fee_rate
                db_fee_rate.save()
                messages.success(request, 'Updated auto rebalancer max fee rate setting to: ' + str(fee_rate))
            if form.cleaned_data['max_cost'] is not None:
                max_cost = form.cleaned_data['max_cost']
                try:
                    db_max_cost = LocalSettings.objects.get(key='AR-MaxCost%')
                except:
                    LocalSettings(key='AR-MaxCost%', value='0.50').save()
                    db_max_cost = LocalSettings.objects.get(key='AR-MaxCost%')
                db_max_cost.value = max_cost
                db_max_cost.save()
                messages.success(request, 'Updated auto rebalancer max cost setting to: ' + str(max_cost))
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
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
            peer_id = serializer.validated_data['peer_id']
            if peer_id.count('@') == 0 and len(peer_id) == 66:
                peer_pubkey = peer_id
                node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey, include_channels=False)).node
                host = node.addresses[0].addr
            elif peer_id.count('@') == 1 and len(peer_id.split('@')[0]) == 66:
                peer_pubkey, host = peer_id.split('@')
            else:
                raise Exception('Invalid peer pubkey or connection string.')
            ln_addr = ln.LightningAddress(pubkey=peer_pubkey, host=host)
            response = stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
            return Response({'message': 'Connection successful!' + str(response)})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Connection request failed! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'})

@api_view(['POST'])
def open_channel(request):
    serializer = OpenChannelSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
            peer_pubkey = serializer.validated_data['peer_pubkey']
            connected = False
            if Peers.objects.filter(pubkey=peer_pubkey, connected=True).exists():
                connected = True
            else:
                try:
                    node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey, include_channels=False)).node
                    host = node.addresses[0].addr
                    ln_addr = ln.LightningAddress(pubkey=peer_pubkey, host=host)
                    response = stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
                    connected = True
                except Exception as e:
                    error = str(e)
                    details_index = error.find('details =') + 11
                    debug_error_index = error.find('debug_error_string =') - 3
                    error_msg = error[details_index:debug_error_index]
                    return Response({'error': 'Error connecting to new peer: ' + error_msg})
            if connected:
                for response in stub.OpenChannel(ln.OpenChannelRequest(node_pubkey=bytes.fromhex(peer_pubkey), local_funding_amount=serializer.validated_data['local_amt'], sat_per_byte=serializer.validated_data['sat_per_byte'])):
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
            chan_id = serializer.validated_data['chan_id']
            if Channels.objects.filter(chan_id=chan_id).exists():
                target_channel = Channels.objects.filter(chan_id=chan_id).get()
                funding_txid = target_channel.funding_txid
                output_index = target_channel.output_index
                target_fee = serializer.validated_data['target_fee']
                channel_point = ln.ChannelPoint()
                channel_point.funding_txid_bytes = bytes.fromhex(funding_txid)
                channel_point.funding_txid_str = funding_txid
                channel_point.output_index = output_index
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                if serializer.validated_data['force']:
                    for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point, force=True)):
                        return Response({'message': 'Channel force closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index)})
                else:
                    for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point, sat_per_byte=target_fee)):
                        return Response({'message': 'Channel gracefully closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index)})
            else:
                return Response({'error': 'Channel ID is not valid.'})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Channel close failed! Error: ' + error_msg})
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
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Invoice creation failed! Error: ' + error_msg})
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
        details_index = error.find('details =') + 11
        debug_error_index = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_error_index]
        return Response({'error': 'Address creation failed! Error: ' + error_msg})

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
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Error updating alias: ' + error_msg)
        else:
            messages.error(request, 'Pubkey not in channels list.')
    else:
        messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')