from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Sum, IntegerField, Count, F, Q
from django.db.models.functions import Round
from django.contrib.auth.decorators import login_required
from django.conf import settings
from datetime import datetime, timedelta
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .forms import OpenChannelForm, CloseChannelForm, ConnectPeerForm, AddInvoiceForm, RebalancerForm, ChanPolicyForm, UpdateChannel, UpdateSetting, AutoRebalanceForm
from .models import Payments, PaymentHops, Invoices, Forwards, Channels, Rebalancer, LocalSettings, Peers, Onchain, Closures, Resolutions, PendingHTLCs, FailedHTLCs, Autopilot
from .serializers import ConnectPeerSerializer, FailedHTLCSerializer, LocalSettingsSerializer, OpenChannelSerializer, CloseChannelSerializer, AddInvoiceSerializer, PaymentHopsSerializer, PaymentSerializer, InvoiceSerializer, ForwardSerializer, ChannelSerializer, PendingHTLCSerializer, RebalancerSerializer, UpdateAliasSerializer, PeerSerializer, OnchainSerializer
from .lnd_deps import lightning_pb2 as ln
from .lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from .lnd_deps.lnd_connect import lnd_connect
from lndg.settings import LND_NETWORK, LND_DIR_PATH
from os import path
from pandas import DataFrame, merge

def graph_links():
    if LocalSettings.objects.filter(key='GUI-GraphLinks').exists():
        graph_links = str(LocalSettings.objects.filter(key='GUI-GraphLinks')[0].value)
    else:
        LocalSettings(key='GUI-GraphLinks', value='https://1ml.com').save()
        graph_links = 'https://1ml.com'
    return graph_links

def network_links():
    if LocalSettings.objects.filter(key='GUI-NetLinks').exists():
        network_links = str(LocalSettings.objects.filter(key='GUI-NetLinks')[0].value)
    else:
        LocalSettings(key='GUI-NetLinks', value='https://mempool.space').save()
        network_links = 'https://mempool.space'
    return network_links

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
        forwards_df = DataFrame.from_records(forwards.values())
        total_forwards = forwards_df.shape[0]
        total_value_forwards = 0 if total_forwards == 0 else int(forwards_df['amt_out_msat'].sum()/1000)
        total_earned = 0 if total_forwards == 0 else forwards_df['fee'].sum()
        forwards_df_in_sum = DataFrame() if forwards_df.empty else forwards_df.groupby('chan_id_in', as_index=True).sum()
        forwards_df_out_sum = DataFrame() if forwards_df.empty else forwards_df.groupby('chan_id_out', as_index=True).sum()
        forwards_df_in_count = DataFrame() if forwards_df.empty else forwards_df.groupby('chan_id_in', as_index=True).count()
        forwards_df_out_count = DataFrame() if forwards_df.empty else forwards_df.groupby('chan_id_out', as_index=True).count()
        #Get current active channels
        active_channels = Channels.objects.filter(is_active=True, is_open=True).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*1000)/Sum('capacity')).annotate(inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*1000)/Sum('capacity')).order_by('outbound_percent')
        total_capacity = 0 if active_channels.count() == 0 else active_channels.aggregate(Sum('capacity'))['capacity__sum']
        total_inbound = 0 if total_capacity == 0 else active_channels.aggregate(Sum('remote_balance'))['remote_balance__sum']
        total_outbound = 0 if total_capacity == 0 else active_channels.aggregate(Sum('local_balance'))['local_balance__sum']
        total_unsettled = 0 if total_capacity == 0 else active_channels.aggregate(Sum('unsettled_balance'))['unsettled_balance__sum']
        filter_7day = datetime.now() - timedelta(days=7)
        forwards_df_7d = DataFrame.from_records(forwards.filter(forward_date__gte=filter_7day).values())
        forwards_df_in_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_in', as_index=True).sum()
        forwards_df_out_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_out', as_index=True).sum()
        forwards_df_in_7d_count = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_in', as_index=True).count()
        forwards_df_out_7d_count = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_out', as_index=True).count()
        routed_7day = forwards_df_7d.shape[0]
        routed_7day_amt = 0 if routed_7day == 0 else int(forwards_df_7d['amt_out_msat'].sum()/1000)
        total_earned_7day = 0 if routed_7day == 0 else forwards_df_7d['fee'].sum()
        payments_7day = payments.filter(status=2).filter(creation_date__gte=filter_7day)
        payments_7day_amt = 0 if payments_7day.count() == 0 else payments_7day.aggregate(Sum('value'))['value__sum']
        total_7day_fees = 0 if payments_7day.count() == 0 else payments_7day.aggregate(Sum('fee'))['fee__sum']
        pending_htlc_count = Channels.objects.filter(is_open=True).aggregate(Sum('htlc_count'))['htlc_count__sum'] if Channels.objects.filter(is_open=True).exists() else 0
        pending_outbound = Channels.objects.filter(is_open=True).aggregate(Sum('pending_outbound'))['pending_outbound__sum'] if Channels.objects.filter(is_open=True).exists() else 0
        detailed_active_channels = []
        for channel in active_channels:
            detailed_channel = {}
            detailed_channel['remote_pubkey'] = channel.remote_pubkey
            detailed_channel['chan_id'] = channel.chan_id
            detailed_channel['capacity'] = channel.capacity
            detailed_channel['local_balance'] = channel.local_balance + channel.pending_outbound
            detailed_channel['remote_balance'] = channel.remote_balance + channel.pending_inbound
            detailed_channel['unsettled_balance'] = channel.unsettled_balance
            detailed_channel['initiator'] = channel.initiator
            detailed_channel['alias'] = channel.alias
            detailed_channel['local_base_fee'] = channel.local_base_fee
            detailed_channel['local_fee_rate'] = channel.local_fee_rate
            detailed_channel['local_disabled'] = channel.local_disabled
            detailed_channel['remote_base_fee'] = channel.remote_base_fee
            detailed_channel['remote_fee_rate'] = channel.remote_fee_rate
            detailed_channel['remote_disabled'] = channel.remote_disabled
            detailed_channel['last_update'] = channel.last_update
            detailed_channel['funding_txid'] = channel.funding_txid
            detailed_channel['output_index'] = channel.output_index
            detailed_channel['outbound_percent'] = int(round(channel.outbound_percent/10, 0))
            detailed_channel['inbound_percent'] = int(round(channel.inbound_percent/10, 0))
            detailed_channel['routed_in'] = forwards_df_in_count.loc[channel.chan_id].amt_out_msat if (forwards_df_in_count.index == channel.chan_id).any() else 0
            detailed_channel['routed_out'] = forwards_df_out_count.loc[channel.chan_id].amt_out_msat if (forwards_df_out_count.index == channel.chan_id).any() else 0
            detailed_channel['amt_routed_in'] = int(forwards_df_in_sum.loc[channel.chan_id].amt_out_msat//10000000)/100 if (forwards_df_in_sum.index == channel.chan_id).any() else 0
            detailed_channel['amt_routed_out'] = int(forwards_df_out_sum.loc[channel.chan_id].amt_out_msat//10000000)/100 if (forwards_df_out_sum.index == channel.chan_id).any() else 0
            detailed_channel['routed_in_7day'] = forwards_df_in_7d_count.loc[channel.chan_id].amt_out_msat if (forwards_df_in_7d_count.index == channel.chan_id).any() else 0
            detailed_channel['routed_out_7day'] = forwards_df_out_7d_count.loc[channel.chan_id].amt_out_msat if (forwards_df_out_7d_count.index == channel.chan_id).any() else 0
            detailed_channel['amt_routed_in_7day'] = int(forwards_df_in_7d_sum.loc[channel.chan_id].amt_out_msat//10000000)/100 if (forwards_df_in_7d_sum.index == channel.chan_id).any() else 0
            detailed_channel['amt_routed_out_7day'] = int(forwards_df_out_7d_sum.loc[channel.chan_id].amt_out_msat//10000000)/100 if (forwards_df_out_7d_sum.index == channel.chan_id).any() else 0
            detailed_channel['htlc_count'] = channel.htlc_count
            detailed_channel['auto_rebalance'] = channel.auto_rebalance
            detailed_channel['ar_in_target'] = channel.ar_in_target
            detailed_active_channels.append(detailed_channel)
        #Get current inactive channels
        inactive_channels = Channels.objects.filter(is_active=False, is_open=True).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*100)/Sum('capacity')).annotate(inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*100)/Sum('capacity')).order_by('outbound_percent')
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
        local_settings = LocalSettings.objects.filter(key__contains='AR-')
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
            'forwards': forwards_df.head(15).to_dict(orient='records'),
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
            'chan_policy_form': ChanPolicyForm,
            'local_settings': local_settings,
            'pending_htlc_count': pending_htlc_count,
            'failed_htlcs': FailedHTLCs.objects.all().order_by('-timestamp')[:10],
            'payments_ppm': 0 if total_sent == 0 else int((total_fees/total_sent)*1000000),
            'routed_ppm': 0 if total_value_forwards == 0 else int((total_earned/total_value_forwards)*1000000),
            '7day_routed_ppm': 0 if routed_7day_amt == 0 else int((total_earned_7day/routed_7day_amt)*1000000),
            '7day_payments_ppm': 0 if payments_7day_amt == 0 else int((total_7day_fees/payments_7day_amt)*1000000),
            'liq_ratio': 0 if total_outbound == 0 else int((total_inbound/sum_outbound)*100),
            'eligible_count': Channels.objects.filter(is_active=True, is_open=True, auto_rebalance=True).annotate(inbound_can=(Sum('remote_balance')*100)/Sum('capacity')).annotate(fee_ratio=(Sum('remote_fee_rate')*100)/Sum('local_fee_rate')).filter(inbound_can__gte=F('ar_in_target'), fee_ratio__lte=F('ar_max_cost')).count(),
            'enabled_count': Channels.objects.filter(is_open=True, auto_rebalance=True).count(),
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links(),
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
        payments = Payments.objects.filter(status=2).filter(creation_date__gte=filter_30day).filter(rebal_chan__isnull=False)
        invoices = Invoices.objects.filter(state=1).filter(settle_date__gte=filter_30day).filter(r_hash__in=payments.values_list('payment_hash'))
        channels = Channels.objects.filter(is_open=True)
        channels_df = DataFrame.from_records(channels.values())
        if channels_df.shape[0] > 0:
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
            channels_df['capacity'] = channels_df.apply(lambda row: round(row.capacity/1000000, 1), axis=1)
            channels_df['local_balance'] = channels_df.apply(lambda row: row.local_balance + row.pending_outbound, axis=1)
            channels_df['remote_balance'] = channels_df.apply(lambda row: row.remote_balance + row.pending_inbound, axis=1)
            channels_df['routed_in_7day'] = channels_df.apply(lambda row: forwards_df_in_7d_count.loc[row.chan_id].amt_out_msat if (forwards_df_in_7d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['routed_out_7day'] = channels_df.apply(lambda row: forwards_df_out_7d_count.loc[row.chan_id].amt_out_msat if (forwards_df_out_7d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['routed_in_30day'] = channels_df.apply(lambda row: forwards_df_in_30d_count.loc[row.chan_id].amt_out_msat if (forwards_df_in_30d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['routed_out_30day'] = channels_df.apply(lambda row: forwards_df_out_30d_count.loc[row.chan_id].amt_out_msat if (forwards_df_out_30d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_routed_in_7day'] = channels_df.apply(lambda row: int(forwards_df_in_7d_sum.loc[row.chan_id].amt_out_msat/100000000)/10 if (forwards_df_in_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_routed_out_7day'] = channels_df.apply(lambda row: int(forwards_df_out_7d_sum.loc[row.chan_id].amt_out_msat/100000000)/10 if (forwards_df_out_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_routed_in_30day'] = channels_df.apply(lambda row: int(forwards_df_in_30d_sum.loc[row.chan_id].amt_out_msat/100000000)/10 if (forwards_df_in_30d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_routed_out_30day'] = channels_df.apply(lambda row: int(forwards_df_out_30d_sum.loc[row.chan_id].amt_out_msat/100000000)/10 if (forwards_df_out_30d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['rebal_in_30day'] = channels_df.apply(lambda row: invoices_df_30d_count.loc[row.chan_id].amt_paid if invoices_df_30d_count.empty == False and (invoices_df_30d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['rebal_out_30day'] = channels_df.apply(lambda row: payments_df_30d_count.loc[row.chan_id].value if payments_df_30d_count.empty == False and (payments_df_30d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_rebal_in_30day'] = channels_df.apply(lambda row: int(invoices_df_30d_sum.loc[row.chan_id].amt_paid/100000)/10 if invoices_df_30d_count.empty == False and (invoices_df_30d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_rebal_out_30day'] = channels_df.apply(lambda row: int(payments_df_30d_sum.loc[row.chan_id].value/100000)/10 if payments_df_30d_count.empty == False and (payments_df_30d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['rebal_in_7day'] = channels_df.apply(lambda row: invoices_df_7d_count.loc[row.chan_id].amt_paid if invoices_df_7d_count.empty == False and (invoices_df_7d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['rebal_out_7day'] = channels_df.apply(lambda row: payments_df_7d_count.loc[row.chan_id].value if payments_df_7d_count.empty == False and (payments_df_7d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_rebal_in_7day'] = channels_df.apply(lambda row: int(invoices_df_7d_sum.loc[row.chan_id].amt_paid/100000)/10 if invoices_df_7d_count.empty == False and (invoices_df_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_rebal_out_7day'] = channels_df.apply(lambda row: int(payments_df_7d_sum.loc[row.chan_id].value/100000)/10 if payments_df_7d_count.empty == False and (payments_df_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['revenue_7day'] = channels_df.apply(lambda row: int(forwards_df_out_7d_sum.loc[row.chan_id].fee) if forwards_df_out_7d_sum.empty == False and (forwards_df_out_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['revenue_30day'] = channels_df.apply(lambda row: int(forwards_df_out_30d_sum.loc[row.chan_id].fee) if forwards_df_out_30d_sum.empty == False and (forwards_df_out_30d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['revenue_assist_7day'] = channels_df.apply(lambda row: int(forwards_df_in_7d_sum.loc[row.chan_id].fee) if forwards_df_in_7d_sum.empty == False and (forwards_df_in_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['revenue_assist_30day'] = channels_df.apply(lambda row: int(forwards_df_in_30d_sum.loc[row.chan_id].fee) if forwards_df_in_30d_sum.empty == False and (forwards_df_in_30d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['costs_7day'] = channels_df.apply(lambda row: 0 if row['rebal_in_7day'] == 0 else int(payments_df_7d.set_index('payment_hash', inplace=False).loc[invoice_hashes_7d[row.chan_id] if invoice_hashes_7d.empty == False and (invoice_hashes_7d.index == row.chan_id).any() else []]['fee'].sum()), axis=1)
            channels_df['costs_30day'] = channels_df.apply(lambda row: 0 if row['rebal_in_30day'] == 0 else int(payments_df_30d.set_index('payment_hash', inplace=False).loc[invoice_hashes_30d[row.chan_id] if invoice_hashes_30d.empty == False and (invoice_hashes_30d.index == row.chan_id).any() else []]['fee'].sum()), axis=1)
            channels_df['profits_7day'] = channels_df.apply(lambda row: row['revenue_7day'] - row['costs_7day'], axis=1)
            channels_df['profits_30day'] = channels_df.apply(lambda row: row['revenue_30day'] - row['costs_30day'], axis=1)
            channels_df['open_block'] = channels_df.apply(lambda row: int(row.chan_id)>>40, axis=1)
            apy_7day = round((channels_df['profits_7day'].sum()*5214.2857)/channels_df['local_balance'].sum(), 2)
            apy_30day = round((channels_df['profits_30day'].sum()*1216.6667)/channels_df['local_balance'].sum(), 2)
            active_updates = channels_df['num_updates'].sum()
            channels_df['updates'] = channels_df.apply(lambda row: 0 if active_updates == 0 else int(round((row['num_updates']/active_updates)*100, 0)), axis=1)
        context = {
            'channels': channels_df.to_dict(orient='records'),
            'apy_7day': apy_7day,
            'apy_30day': apy_30day,
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
        }
        return render(request, 'channels.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def fees(request):
    if request.method == 'GET':
        filter_7day = datetime.now() - timedelta(days=7)
        forwards = Forwards.objects.filter(forward_date__gte=filter_7day, amt_out_msat__gte=1000000)
        channels = Channels.objects.filter(is_open=True)
        channels_df = DataFrame.from_records(channels.values())
        if channels_df.shape[0] > 0:
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
            payments = Payments.objects.filter(status=2).filter(creation_date__gte=filter_7day).filter(rebal_chan__isnull=False)
            invoices = Invoices.objects.filter(state=1).filter(settle_date__gte=filter_7day).filter(r_hash__in=payments.values_list('payment_hash'))
            payments_df_7d = DataFrame.from_records(payments.filter(creation_date__gte=filter_7day).values())
            invoices_df_7d = DataFrame.from_records(invoices.filter(settle_date__gte=filter_7day).values())
            invoices_df_7d_sum = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).sum()
            invoice_hashes_7d = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True)['r_hash'].apply(list)
            channels_df['amt_rebal_in_7day'] = channels_df.apply(lambda row: int(invoices_df_7d_sum.loc[row.chan_id].amt_paid) if invoices_df_7d_sum.empty == False and (invoices_df_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['costs_7day'] = channels_df.apply(lambda row: 0 if row['amt_rebal_in_7day'] == 0 else int(payments_df_7d.set_index('payment_hash', inplace=False).loc[invoice_hashes_7d[row.chan_id] if invoice_hashes_7d.empty == False and (invoice_hashes_7d.index == row.chan_id).any() else []]['fee'].sum()), axis=1)
            channels_df['rebal_ppm'] = channels_df.apply(lambda row: int((row['costs_7day']/row['amt_rebal_in_7day'])*1000000) if row['amt_rebal_in_7day'] > 0 else 0, axis=1)
            channels_df['max_suggestion'] = channels_df.apply(lambda row: int((row['out_rate'] if row['out_rate'] > 0 else row['local_fee_rate'])*1.15) if row['in_percent'] > 25 else int(row['local_fee_rate']), axis=1)
            channels_df['min_suggestion'] = channels_df.apply(lambda row: int((row['out_rate'] if row['out_rate'] > 0 else row['local_fee_rate'])*0.75) if row['out_percent'] > 25 else int(row['local_fee_rate']), axis=1)
            channels_df['assisted_ratio'] = channels_df.apply(lambda row: round((row['revenue_assist_7day'] if row['revenue_7day'] == 0 else row['revenue_assist_7day']/row['revenue_7day']), 2), axis=1)
            channels_df['profit_margin'] = channels_df.apply(lambda row: row['out_rate']*((100-row['ar_max_cost'])/100), axis=1)
            channels_df['adjusted_out_rate'] = channels_df.apply(lambda row: int(row['out_rate']+row['net_routed_7day']*row['assisted_ratio']), axis=1)
            channels_df['adjusted_rebal_rate'] = channels_df.apply(lambda row: int(row['rebal_ppm']+row['profit_margin']), axis=1)
            channels_df['out_rate_only'] = channels_df.apply(lambda row: int(row['out_rate']+row['net_routed_7day']*row['out_rate']*0.02), axis=1)
            channels_df['fee_rate_only'] = channels_df.apply(lambda row: int(row['local_fee_rate']+row['net_routed_7day']*row['local_fee_rate']*0.05), axis=1)
            channels_df['new_rate'] = channels_df.apply(lambda row: row['adjusted_out_rate'] if row['net_routed_7day'] != 0 else (row['adjusted_rebal_rate'] if row['rebal_ppm'] > 0 and row['out_rate'] > 0 else (row['out_rate_only'] if row['out_rate'] > 0 else (row['min_suggestion'] if row['net_routed_7day'] == 0 and row['in_percent'] < 25 else row['fee_rate_only']))), axis=1)
            channels_df['new_rate'] = channels_df.apply(lambda row: 0 if row['new_rate'] < 0 else row['new_rate'], axis=1)
            channels_df['new_rate'] = channels_df.apply(lambda row: row['max_suggestion'] if row['max_suggestion'] > 0 and row['new_rate'] > row['max_suggestion'] else row['new_rate'], axis=1)
            channels_df['new_rate'] = channels_df.apply(lambda row: row['min_suggestion'] if row['new_rate'] < row['min_suggestion'] else row['new_rate'], axis=1)
            channels_df['new_rate'] = channels_df.apply(lambda row: int(round(row['new_rate']/5, 0)*5), axis=1)
            channels_df['adjustment'] = channels_df.apply(lambda row: int(row['new_rate']-row['local_fee_rate']), axis=1)
        context = {
            'channels': channels_df.sort_values(by=['out_percent']).to_dict(orient='records'),
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
        }
        return render(request, 'fee_rates.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def advanced(request):
    if request.method == 'GET':
        channels = Channels.objects.filter(is_open=True).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*1000)/Sum('capacity')).annotate(inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*1000)/Sum('capacity')).order_by('-is_active', 'outbound_percent')
        channels_df = DataFrame.from_records(channels.values())
        if channels_df.shape[0] > 0:
            channels_df['out_percent'] = channels_df.apply(lambda row: int(round(row['outbound_percent']/10, 0)), axis=1)
            channels_df['in_percent'] = channels_df.apply(lambda row: int(round(row['inbound_percent']/10, 0)), axis=1)
            channels_df['local_balance'] = channels_df.apply(lambda row: row.local_balance + row.pending_outbound, axis=1)
            channels_df['remote_balance'] = channels_df.apply(lambda row: row.remote_balance + row.pending_inbound, axis=1)
            channels_df['fee_ratio'] = channels_df.apply(lambda row: 0 if row['local_fee_rate'] == 0 else int(round(((row['remote_fee_rate']/row['local_fee_rate'])*1000)/10, 0)), axis=1)
        context = {
            'channels': channels_df.to_dict(orient='records'),
            'local_settings': LocalSettings.objects.all(),
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
        }
        return render(request, 'advanced.html', context)
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
        peers = Peers.objects.filter(connected=True)
        context = {
            'peers': peers,
            'num_peers': len(peers),
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links()
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
            'transactions': list(Onchain.objects.filter(block_height=0)) + list(Onchain.objects.exclude(block_height=0).order_by('-block_height')),
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'network_links': network_links()
        }
        return render(request, 'balances.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def closures(request):
    if request.method == 'GET':
        closures_df = DataFrame.from_records(Closures.objects.all().values())
        channels_df = DataFrame.from_records(Channels.objects.all().values('chan_id', 'alias'))
        merged = merge(closures_df, channels_df, on='chan_id', how='left')
        merged['alias'] = merged['alias'].fillna('---')
        context = {
            'closures': merged.sort_values(by=['close_height'], ascending=False).to_dict(orient='records'),
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'network_links': network_links(),
            'graph_links': graph_links()
        }
        return render(request, 'closures.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def resolutions(request):
    if request.method == 'GET':
        chan_id = request.GET.urlencode()[1:]
        context = {
            'chan_id': chan_id,
            'resolutions': Resolutions.objects.filter(chan_id=chan_id),
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'network_links': network_links()
        }
        return render(request, 'resolutions.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def channel(request):
    if request.method == 'GET':
        chan_id = request.GET.urlencode()[1:]
        if Channels.objects.filter(chan_id=chan_id).exists():
            filter_1day = datetime.now() - timedelta(days=1)
            filter_7day = datetime.now() - timedelta(days=7)
            filter_30day = datetime.now() - timedelta(days=30)
            channels_df = DataFrame.from_records(Channels.objects.filter(chan_id=chan_id).values('chan_id', 'capacity', 'local_balance', 'pending_outbound', 'remote_balance', 'pending_inbound', 'remote_pubkey', 'alias', 'is_active', 'is_open', 'funding_txid', 'output_index'))
            channels_df['local_balance'] = channels_df.apply(lambda row: row.local_balance + row.pending_outbound, axis=1)
            channels_df['remote_balance'] = channels_df.apply(lambda row: row.remote_balance + row.pending_inbound, axis=1)
            channels_df['in_percent'] = channels_df.apply(lambda row: int(round((row['remote_balance']/row['capacity'])*100, 0)), axis=1)
            channels_df['out_percent'] = channels_df.apply(lambda row: int(round((row['local_balance']/row['capacity'])*100, 0)), axis=1)
            channels_df['open_block'] = channels_df.apply(lambda row: int(row.chan_id)>>40, axis=1)
            channels_df['routed_in'] = 0
            channels_df['routed_in_30day'] = 0
            channels_df['routed_in_7day'] = 0
            channels_df['routed_in_1day'] = 0
            channels_df['routed_out'] = 0
            channels_df['routed_out_30day'] = 0
            channels_df['routed_out_7day'] = 0
            channels_df['routed_out_1day'] = 0
            channels_df['amt_routed_in'] = 0
            channels_df['amt_routed_in_30day'] = 0
            channels_df['amt_routed_in_7day'] = 0
            channels_df['amt_routed_in_1day'] = 0
            channels_df['amt_routed_out'] = 0
            channels_df['amt_routed_out_30day'] = 0
            channels_df['amt_routed_out_7day'] = 0
            channels_df['amt_routed_out_1day'] = 0
            channels_df['revenue'] = 0
            channels_df['revenue_30day'] = 0
            channels_df['revenue_7day'] = 0
            channels_df['revenue_1day'] = 0
            channels_df['revenue_assist'] = 0
            channels_df['revenue_assist_30day'] = 0
            channels_df['revenue_assist_7day'] = 0
            channels_df['revenue_assist_1day'] = 0
            channels_df['rebal_out'] = 0
            channels_df['rebal_out_30day'] = 0
            channels_df['rebal_out_7day'] = 0
            channels_df['rebal_out_1day'] = 0
            channels_df['amt_rebal_out'] = 0
            channels_df['amt_rebal_out_30day'] = 0
            channels_df['amt_rebal_out_7day'] = 0
            channels_df['amt_rebal_out_1day'] = 0
            channels_df['rebal_in'] = 0
            channels_df['rebal_in_30day'] = 0
            channels_df['rebal_in_7day'] = 0
            channels_df['rebal_in_1day'] = 0
            channels_df['amt_rebal_in'] = 0
            channels_df['amt_rebal_in_30day'] = 0
            channels_df['amt_rebal_in_7day'] = 0
            channels_df['amt_rebal_in_1day'] = 0
            channels_df['costs'] = 0
            channels_df['costs_30day'] = 0
            channels_df['costs_7day'] = 0
            channels_df['costs_1day'] = 0
            start_date = None
            forwards_df = DataFrame.from_records(Forwards.objects.filter(Q(chan_id_in=chan_id) | Q(chan_id_out=chan_id)).values())
            payments_df = DataFrame.from_records(Payments.objects.filter(status=2).filter(chan_out=chan_id).filter(rebal_chan__isnull=False).values())
            invoices_df = DataFrame.from_records(Invoices.objects.filter(state=1).filter(chan_in=chan_id).filter(r_hash__in=Payments.objects.filter(status=2).filter(rebal_chan=chan_id)).values())
            if forwards_df.shape[0]> 0:
                start_date = forwards_df['forward_date'].min()
                forwards_df['amt_in'] = (forwards_df['amt_in_msat']/1000).astype(int)
                forwards_df['amt_out'] = (forwards_df['amt_out_msat']/1000).astype(int)
                forwards_df['ppm'] = (forwards_df['fee']/(forwards_df['amt_in_msat']/1000000)).astype(int)
                forwards_df_30d = forwards_df.loc[forwards_df['forward_date'] >= filter_30day]
                forwards_df_7d = forwards_df_30d.loc[forwards_df_30d['forward_date'] >= filter_7day]
                forwards_df_1d = forwards_df_7d.loc[forwards_df_7d['forward_date'] >= filter_1day]
                forwards_df_in_count = DataFrame() if forwards_df.empty else forwards_df.groupby('chan_id_in', as_index=True).count()
                forwards_df_out_count = DataFrame() if forwards_df.empty else forwards_df.groupby('chan_id_out', as_index=True).count()
                forwards_df_in_30d_count = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_in', as_index=True).count()
                forwards_df_out_30d_count = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_out', as_index=True).count()
                forwards_df_in_7d_count = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_in', as_index=True).count()
                forwards_df_out_7d_count = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_out', as_index=True).count()
                forwards_df_in_1d_count = DataFrame() if forwards_df_1d.empty else forwards_df_1d.groupby('chan_id_in', as_index=True).count()
                forwards_df_out_1d_count = DataFrame() if forwards_df_1d.empty else forwards_df_1d.groupby('chan_id_out', as_index=True).count()
                forwards_df_in_sum = DataFrame() if forwards_df.empty else forwards_df.groupby('chan_id_in', as_index=True).sum()
                forwards_df_out_sum = DataFrame() if forwards_df.empty else forwards_df.groupby('chan_id_out', as_index=True).sum()
                forwards_df_in_30d_sum = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_in', as_index=True).sum()
                forwards_df_out_30d_sum = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_out', as_index=True).sum()
                forwards_df_in_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_in', as_index=True).sum()
                forwards_df_out_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_out', as_index=True).sum()
                forwards_df_in_1d_sum = DataFrame() if forwards_df_1d.empty else forwards_df_1d.groupby('chan_id_in', as_index=True).sum()
                forwards_df_out_1d_sum = DataFrame() if forwards_df_1d.empty else forwards_df_1d.groupby('chan_id_out', as_index=True).sum()
                channels_df['routed_in'] = channels_df.apply(lambda row: forwards_df_in_count.loc[row.chan_id].amt_out_msat if (forwards_df_in_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['routed_in_30day'] = channels_df.apply(lambda row: forwards_df_in_30d_count.loc[row.chan_id].amt_out_msat if (forwards_df_in_30d_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['routed_in_7day'] = channels_df.apply(lambda row: forwards_df_in_7d_count.loc[row.chan_id].amt_out_msat if (forwards_df_in_7d_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['routed_in_1day'] = channels_df.apply(lambda row: forwards_df_in_1d_count.loc[row.chan_id].amt_out_msat if (forwards_df_in_1d_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['routed_out'] = channels_df.apply(lambda row: forwards_df_out_count.loc[row.chan_id].amt_out_msat if (forwards_df_out_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['routed_out_30day'] = channels_df.apply(lambda row: forwards_df_out_30d_count.loc[row.chan_id].amt_out_msat if (forwards_df_out_30d_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['routed_out_7day'] = channels_df.apply(lambda row: forwards_df_out_7d_count.loc[row.chan_id].amt_out_msat if (forwards_df_out_7d_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['routed_out_1day'] = channels_df.apply(lambda row: forwards_df_out_1d_count.loc[row.chan_id].amt_out_msat if (forwards_df_out_1d_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_routed_in'] = channels_df.apply(lambda row: int(forwards_df_in_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_in_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_routed_in_30day'] = channels_df.apply(lambda row: int(forwards_df_in_30d_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_in_30d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_routed_in_7day'] = channels_df.apply(lambda row: int(forwards_df_in_7d_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_in_7d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_routed_in_1day'] = channels_df.apply(lambda row: int(forwards_df_in_1d_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_in_1d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_routed_out'] = channels_df.apply(lambda row: int(forwards_df_out_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_out_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_routed_out_30day'] = channels_df.apply(lambda row: int(forwards_df_out_30d_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_out_30d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_routed_out_7day'] = channels_df.apply(lambda row: int(forwards_df_out_7d_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_out_7d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_routed_out_1day'] = channels_df.apply(lambda row: int(forwards_df_out_1d_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_out_1d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['revenue'] = channels_df.apply(lambda row: int(forwards_df_out_sum.loc[row.chan_id].fee) if forwards_df_out_sum.empty == False and (forwards_df_out_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['revenue_30day'] = channels_df.apply(lambda row: int(forwards_df_out_30d_sum.loc[row.chan_id].fee) if forwards_df_out_30d_sum.empty == False and (forwards_df_out_30d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['revenue_7day'] = channels_df.apply(lambda row: int(forwards_df_out_7d_sum.loc[row.chan_id].fee) if forwards_df_out_7d_sum.empty == False and (forwards_df_out_7d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['revenue_1day'] = channels_df.apply(lambda row: int(forwards_df_out_1d_sum.loc[row.chan_id].fee) if forwards_df_out_1d_sum.empty == False and (forwards_df_out_1d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['revenue_assist'] = channels_df.apply(lambda row: int(forwards_df_in_sum.loc[row.chan_id].fee) if forwards_df_in_sum.empty == False and (forwards_df_in_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['revenue_assist_30day'] = channels_df.apply(lambda row: int(forwards_df_in_30d_sum.loc[row.chan_id].fee) if forwards_df_in_30d_sum.empty == False and (forwards_df_in_30d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['revenue_assist_7day'] = channels_df.apply(lambda row: int(forwards_df_in_7d_sum.loc[row.chan_id].fee) if forwards_df_in_7d_sum.empty == False and (forwards_df_in_7d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['revenue_assist_1day'] = channels_df.apply(lambda row: int(forwards_df_in_1d_sum.loc[row.chan_id].fee) if forwards_df_in_1d_sum.empty == False and (forwards_df_in_1d_sum.index == row.chan_id).any() else 0, axis=1)
            if payments_df.shape[0] > 0:
                payments_df_30d = payments_df.loc[payments_df['creation_date'] >= filter_30day]
                payments_df_7d = payments_df_30d.loc[payments_df_30d['creation_date'] >= filter_7day]
                payments_df_1d = payments_df_7d.loc[payments_df_7d['creation_date'] >= filter_1day]
                payments_df_count = DataFrame() if payments_df.empty else payments_df.groupby('chan_out', as_index=True).count()
                payments_df_30d_count = DataFrame() if payments_df_30d.empty else payments_df_30d.groupby('chan_out', as_index=True).count()
                payments_df_7d_count = DataFrame() if payments_df_7d.empty else payments_df_7d.groupby('chan_out', as_index=True).count()
                payments_df_1d_count = DataFrame() if payments_df_1d.empty else payments_df_1d.groupby('chan_out', as_index=True).count()
                payments_df_sum = DataFrame() if payments_df.empty else payments_df.groupby('chan_out', as_index=True).sum()
                payments_df_30d_sum = DataFrame() if payments_df_30d.empty else payments_df_30d.groupby('chan_out', as_index=True).sum()
                payments_df_7d_sum = DataFrame() if payments_df_7d.empty else payments_df_7d.groupby('chan_out', as_index=True).sum()
                payments_df_1d_sum = DataFrame() if payments_df_1d.empty else payments_df_1d.groupby('chan_out', as_index=True).sum()
                channels_df['rebal_out'] = channels_df.apply(lambda row: payments_df_count.loc[row.chan_id].value if payments_df_count.empty == False and (payments_df_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['rebal_out_30day'] = channels_df.apply(lambda row: payments_df_30d_count.loc[row.chan_id].value if payments_df_30d_count.empty == False and (payments_df_30d_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['rebal_out_7day'] = channels_df.apply(lambda row: payments_df_7d_count.loc[row.chan_id].value if payments_df_7d_count.empty == False and (payments_df_7d_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['rebal_out_1day'] = channels_df.apply(lambda row: payments_df_1d_count.loc[row.chan_id].value if payments_df_1d_count.empty == False and (payments_df_1d_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_rebal_out'] = channels_df.apply(lambda row: int(payments_df_sum.loc[row.chan_id].value) if payments_df_count.empty == False and (payments_df_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_rebal_out_30day'] = channels_df.apply(lambda row: int(payments_df_30d_sum.loc[row.chan_id].value) if payments_df_30d_count.empty == False and (payments_df_30d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_rebal_out_7day'] = channels_df.apply(lambda row: int(payments_df_7d_sum.loc[row.chan_id].value) if payments_df_7d_count.empty == False and (payments_df_7d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_rebal_out_1day'] = channels_df.apply(lambda row: int(payments_df_1d_sum.loc[row.chan_id].value) if payments_df_1d_count.empty == False and (payments_df_1d_sum.index == row.chan_id).any() else 0, axis=1)
            if invoices_df.shape[0]> 0:
                invoices_df_30d = invoices_df.loc[invoices_df['settle_date'] >= filter_30day]
                invoices_df_7d = invoices_df_30d.loc[invoices_df_30d['settle_date'] >= filter_7day]
                invoices_df_1d = invoices_df_7d.loc[invoices_df_7d['settle_date'] >= filter_1day]
                invoices_df_count = DataFrame() if invoices_df.empty else invoices_df.groupby('chan_in', as_index=True).count()
                invoices_df_30d_count = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True).count()
                invoices_df_7d_count = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).count()
                invoices_df_1d_count = DataFrame() if invoices_df_1d.empty else invoices_df_1d.groupby('chan_in', as_index=True).count()
                invoices_df_sum = DataFrame() if invoices_df.empty else invoices_df.groupby('chan_in', as_index=True).sum()
                invoices_df_30d_sum = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True).sum()
                invoices_df_7d_sum = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).sum()
                invoices_df_1d_sum = DataFrame() if invoices_df_1d.empty else invoices_df_1d.groupby('chan_in', as_index=True).sum()
                channels_df['rebal_in'] = channels_df.apply(lambda row: invoices_df_count.loc[row.chan_id].amt_paid if invoices_df_count.empty == False and (invoices_df_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['rebal_in_30day'] = channels_df.apply(lambda row: invoices_df_30d_count.loc[row.chan_id].amt_paid if invoices_df_30d_count.empty == False and (invoices_df_30d_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['rebal_in_7day'] = channels_df.apply(lambda row: invoices_df_7d_count.loc[row.chan_id].amt_paid if invoices_df_7d_count.empty == False and (invoices_df_7d_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['rebal_in_1day'] = channels_df.apply(lambda row: invoices_df_1d_count.loc[row.chan_id].amt_paid if invoices_df_1d_count.empty == False and (invoices_df_1d_count.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_rebal_in'] = channels_df.apply(lambda row: int(invoices_df_sum.loc[row.chan_id].amt_paid) if invoices_df_count.empty == False and (invoices_df_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_rebal_in_30day'] = channels_df.apply(lambda row: int(invoices_df_30d_sum.loc[row.chan_id].amt_paid) if invoices_df_30d_count.empty == False and (invoices_df_30d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_rebal_in_7day'] = channels_df.apply(lambda row: int(invoices_df_7d_sum.loc[row.chan_id].amt_paid) if invoices_df_7d_count.empty == False and (invoices_df_7d_sum.index == row.chan_id).any() else 0, axis=1)
                channels_df['amt_rebal_in_1day'] = channels_df.apply(lambda row: int(invoices_df_1d_sum.loc[row.chan_id].amt_paid) if invoices_df_1d_count.empty == False and (invoices_df_1d_sum.index == row.chan_id).any() else 0, axis=1)
                rebal_payments_df = DataFrame.from_records(Payments.objects.filter(status=2).filter(rebal_chan=chan_id).values())
                if rebal_payments_df.shape[0] > 0:
                    rebal_payments_df_30d = rebal_payments_df.loc[rebal_payments_df['creation_date'] >= filter_30day]
                    rebal_payments_df_7d = rebal_payments_df_30d.loc[rebal_payments_df_30d['creation_date'] >= filter_7day]
                    rebal_payments_df_1d = rebal_payments_df_7d.loc[rebal_payments_df_7d['creation_date'] >= filter_1day]
                    invoice_hashes = DataFrame() if invoices_df.empty else invoices_df.groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    invoice_hashes_30d = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    invoice_hashes_7d = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    invoice_hashes_1d = DataFrame() if invoices_df_1d.empty else invoices_df_1d.groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    channels_df['costs'] = channels_df.apply(lambda row: 0 if row['rebal_in'] == 0 else int(rebal_payments_df.set_index('payment_hash', inplace=False).loc[invoice_hashes[row.chan_id] if invoice_hashes.empty == False and (invoice_hashes.index == row.chan_id).any() else []]['fee'].sum()), axis=1)
                    channels_df['costs_30day'] = channels_df.apply(lambda row: 0 if row['rebal_in_30day'] == 0 else int(rebal_payments_df_30d.set_index('payment_hash', inplace=False).loc[invoice_hashes_30d[row.chan_id] if invoice_hashes_30d.empty == False and (invoice_hashes_30d.index == row.chan_id).any() else []]['fee'].sum()), axis=1)
                    channels_df['costs_7day'] = channels_df.apply(lambda row: 0 if row['rebal_in_7day'] == 0 else int(rebal_payments_df_7d.set_index('payment_hash', inplace=False).loc[invoice_hashes_7d[row.chan_id] if invoice_hashes_7d.empty == False and (invoice_hashes_7d.index == row.chan_id).any() else []]['fee'].sum()), axis=1)
                    channels_df['costs_1day'] = channels_df.apply(lambda row: 0 if row['rebal_in_1day'] == 0 else int(rebal_payments_df_1d.set_index('payment_hash', inplace=False).loc[invoice_hashes_1d[row.chan_id] if invoice_hashes_1d.empty == False and (invoice_hashes_1d.index == row.chan_id).any() else []]['fee'].sum()), axis=1)
            channels_df['profits'] = channels_df.apply(lambda row: row['revenue'] - row['costs'], axis=1)
            channels_df['profits_30day'] = channels_df.apply(lambda row: row['revenue_30day'] - row['costs_30day'], axis=1)
            channels_df['profits_7day'] = channels_df.apply(lambda row: row['revenue_7day'] - row['costs_7day'], axis=1)
            channels_df['profits_1day'] = channels_df.apply(lambda row: row['revenue_1day'] - row['costs_1day'], axis=1)
            channels_df['profits_vol'] = channels_df.apply(lambda row: 0 if row['amt_routed_out'] == 0 else int(row['profits'] / (row['amt_routed_out']/1000000)), axis=1)
            channels_df['profits_vol_30day'] = channels_df.apply(lambda row: 0 if row['amt_routed_out_30day'] == 0 else int(row['profits_30day'] / (row['amt_routed_out_30day']/1000000)), axis=1)
            channels_df['profits_vol_7day'] = channels_df.apply(lambda row: 0 if row['amt_routed_out_7day'] == 0 else int(row['profits_7day'] / (row['amt_routed_out_7day']/1000000)), axis=1)
            channels_df['profits_vol_1day'] = channels_df.apply(lambda row: 0 if row['amt_routed_out_1day'] == 0 else int(row['profits_1day'] / (row['amt_routed_out_1day']/1000000)), axis=1)
            channels_df['apy'] = 0.0
            if start_date is not None:
                time_delta = datetime.now() - start_date.to_pydatetime()
                days_routing = time_delta.days + (time_delta.seconds/86400)
                channels_df['apy'] = round(((channels_df['profits']/days_routing)*36500)/channels_df['capacity'], 2)
            channels_df['apy_30day'] = round((channels_df['profits_30day']*1216.6667)/channels_df['capacity'], 2)
            channels_df['apy_7day'] = round((channels_df['profits_7day']*5214.2857)/channels_df['capacity'], 2)
            channels_df['apy_1day'] = round((channels_df['profits_1day']*36500)/channels_df['capacity'], 2)
        else:
            channels_df = DataFrame()
        context = {
            'chan_id': chan_id,
            'channel': [] if channels_df.empty else channels_df.to_dict(orient='records')[0],
            'incoming_htlcs': PendingHTLCs.objects.filter(chan_id=chan_id).filter(incoming=True).order_by('hash_lock'),
            'outgoing_htlcs': PendingHTLCs.objects.filter(chan_id=chan_id).filter(incoming=False).order_by('hash_lock'),
            'forwards': [] if forwards_df.empty else forwards_df.sort_values(by=['forward_date'], ascending=False).to_dict(orient='records')[:5],
            'payments': [] if payments_df.empty else payments_df.sort_values(by=['creation_date'], ascending=False).to_dict(orient='records')[:5],
            'invoices': [] if invoices_df.empty else invoices_df.sort_values(by=['settle_date'], ascending=False).to_dict(orient='records')[:5],
            'rebalances': Rebalancer.objects.filter(last_hop_pubkey=channels_df['remote_pubkey'][0]).order_by('-requested')[:5],
            'failed_htlcs': FailedHTLCs.objects.filter(Q(chan_id_in=chan_id) | Q(chan_id_out=chan_id)).order_by('-timestamp')[:5],
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
        }
        return render(request, 'channel.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def opens(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        self_pubkey = stub.GetInfo(ln.GetInfoRequest()).identity_pubkey
        current_peers = Channels.objects.filter(is_open=True).values_list('remote_pubkey')
        filter_60day = datetime.now() - timedelta(days=60)
        payments_60day = Payments.objects.filter(creation_date__gte=filter_60day).values_list('payment_hash')
        open_list = PaymentHops.objects.filter(payment_hash__in=payments_60day).exclude(node_pubkey=self_pubkey).exclude(node_pubkey__in=current_peers).values('node_pubkey', 'alias').annotate(ppm=(Sum('fee')/Sum('amt'))*1000000).annotate(score=Round((Round(Count('id')/5, output_field=IntegerField())+Round(Sum('amt')/500000, output_field=IntegerField()))/10, output_field=IntegerField())).annotate(count=Count('id')).annotate(amount=Sum('amt')).annotate(fees=Sum('fee')).annotate(sum_cost_to=Sum('cost_to')/(Sum('amt')/1000000)).exclude(score=0).order_by('-score', 'ppm')[:21]
        context = {
            'open_list': open_list,
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links()
        }
        return render(request, 'open_list.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def actions(request):
    if request.method == 'GET':
        channels = Channels.objects.filter(is_active=True, is_open=True).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*1000)/Sum('capacity')).annotate(inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*1000)/Sum('capacity'))
        filter_7day = datetime.now() - timedelta(days=7)
        forwards = Forwards.objects.filter(forward_date__gte=filter_7day)
        action_list = []
        for channel in channels:
            result = {}
            result['chan_id'] = channel.chan_id
            result['alias'] = channel.alias
            result['capacity'] = channel.capacity
            result['local_balance'] = channel.local_balance + channel.pending_outbound
            result['remote_balance'] = channel.remote_balance + channel.pending_inbound
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
            result['ar_target'] = channel.ar_in_target
            if result['o7D'] > (result['i7D']*1.10) and result['outbound_percent'] > 75:
                #print('Case 1: Pass')
                continue
            elif result['o7D'] > (result['i7D']*1.10) and result['inbound_percent'] > 75 and channel.auto_rebalance == False:
                if channel.local_fee_rate <= channel.remote_fee_rate:
                    #print('Case 6: Peer Fee Too High')
                    result['output'] = 'Peer Fee Too High'
                    result['reason'] = 'o7D > i7D AND Inbound Liq > 75% AND Local Fee < Remote Fee'
                    continue
                #print('Case 2: Enable AR')
                result['output'] = 'Enable AR'
                result['reason'] = 'o7D > i7D AND Inbound Liq > 75%'
            elif result['o7D'] < (result['i7D']*1.10) and result['outbound_percent'] > 75 and channel.auto_rebalance == True:
                #print('Case 3: Disable AR')
                result['output'] = 'Disable AR'
                result['reason'] = 'o7D < i7D AND Outbound Liq > 75%'
            elif result['o7D'] < (result['i7D']*1.10) and result['inbound_percent'] > 75:
                #print('Case 4: Pass')
                continue
            else:
                #print('Case 5: Pass')
                continue
            if len(result) > 0:
                action_list.append(result) 
        context = {
            'action_list': action_list,
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
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
def failed_htlcs(request):
    if request.method == 'GET':
        context = {
            'failed_htlcs': FailedHTLCs.objects.all().order_by('-timestamp')[:150],
        }
        return render(request, 'failed_htlcs.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def payments(request):
    if request.method == 'GET':
        context = {
            'payments': Payments.objects.filter(status=2).order_by('-creation_date')[:150],
        }
        return render(request, 'payments.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def invoices(request):
    if request.method == 'GET':
        context = {
            'invoices': Invoices.objects.filter(state=1).order_by('-creation_date')[:150],
        }
        return render(request, 'invoices.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def forwards(request):
    if request.method == 'GET':
        context = {
            'forwards': Forwards.objects.all().annotate(amt_in=Sum('amt_in_msat')/1000).annotate(amt_out=Sum('amt_out_msat')/1000).annotate(ppm=Round((Sum('fee')*1000000000)/Sum('amt_out_msat'), output_field=IntegerField())).order_by('-id')[:150],
        }
        return render(request, 'forwards.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def rebalancing(request):
    if request.method == 'GET':
        context = {
            'channels': Channels.objects.filter(is_active=True, is_open=True).annotate(percent_inbound=(Sum('remote_balance')*100)/Sum('capacity')).annotate(percent_outbound=(Sum('local_balance')*100)/Sum('capacity')).annotate(inbound_can=((Sum('remote_balance')*100)/Sum('capacity'))/Sum('ar_in_target')).annotate(fee_ratio=(Sum('ar_max_cost')*Sum('local_fee_rate'))/Sum('remote_fee_rate')).order_by('percent_outbound'),
            'rebalancer': Rebalancer.objects.all().order_by('-id')[:20],
            'rebalancer_form': RebalancerForm,
            'local_settings': LocalSettings.objects.filter(key__contains='AR-')
        }
        return render(request, 'rebalancing.html', context)
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
                messages.error(request, 'Error entering rebalancer request! Error: ' + error_msg)
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
                Channels.objects.all().update(ar_amt_target=Round(F('capacity')*target_percent, output_field=IntegerField()))
                messages.success(request, 'Updated auto rebalancer target amount for all channels to: ' + str(target_percent))
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
                Channels.objects.all().update(ar_out_target=int(outbound_percent*100))
                messages.success(request, 'Updated auto rebalancer target outbound percent setting for all channels to: ' + str(outbound_percent))
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
                    LocalSettings(key='AR-MaxCost%', value='0.65').save()
                    db_max_cost = LocalSettings.objects.get(key='AR-MaxCost%')
                db_max_cost.value = max_cost
                db_max_cost.save()
                Channels.objects.all().update(ar_max_cost=int(max_cost*100))
                messages.success(request, 'Updated auto rebalancer max cost setting to: ' + str(max_cost))
            if form.cleaned_data['autopilot'] is not None:
                autopilot = form.cleaned_data['autopilot']
                try:
                    db_autopilot = LocalSettings.objects.get(key='AR-Autopilot')
                except:
                    LocalSettings(key='AR-Autopilot', value='0').save()
                    db_autopilot = LocalSettings.objects.get(key='AR-Autopilot')
                db_autopilot.value = autopilot
                db_autopilot.save()
                messages.success(request, 'Updated autopilot setting to: ' + str(autopilot))
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

@login_required(login_url='/lndg-admin/login/?next=/')
def update_channel(request):
    if request.method == 'POST':
        form = UpdateChannel(request.POST)
        if form.is_valid() and Channels.objects.filter(chan_id=form.cleaned_data['chan_id']).exists():
            chan_id = form.cleaned_data['chan_id']
            target = form.cleaned_data['target']
            update_target = int(form.cleaned_data['update_target'])
            db_channel = Channels.objects.filter(chan_id=chan_id)[0]
            if update_target == 0:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                channel_point = ln.ChannelPoint()
                channel_point.funding_txid_bytes = bytes.fromhex(db_channel.funding_txid)
                channel_point.funding_txid_str = db_channel.funding_txid
                channel_point.output_index = db_channel.output_index
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=target, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=40))
                db_channel.local_base_fee = target
                db_channel.save()
                messages.success(request, 'Base fee for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
            elif update_target == 1:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                channel_point = ln.ChannelPoint()
                channel_point.funding_txid_bytes = bytes.fromhex(db_channel.funding_txid)
                channel_point.funding_txid_str = db_channel.funding_txid
                channel_point.output_index = db_channel.output_index
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(target/1000000), time_lock_delta=40))
                db_channel.local_fee_rate = target
                db_channel.save()
                messages.success(request, 'Fee rate for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
            elif update_target == 2:
                db_channel.ar_amt_target = target
                db_channel.save()
                messages.success(request, 'Auto rebalancer target amount for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
            elif update_target == 3:
                db_channel.ar_in_target = target
                db_channel.save()
                messages.success(request, 'Auto rebalancer inbound target for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target) + '%')
            elif update_target == 4:
                db_channel.ar_out_target = target
                db_channel.save()
                messages.success(request, 'Auto rebalancer outbound target for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target) + '%')
            elif update_target == 5:
                db_channel.auto_rebalance = True if db_channel.auto_rebalance == False else False
                db_channel.save()
                messages.success(request, 'Auto rebalancer status for chanel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(db_channel.auto_rebalance))
            elif update_target == 6:
                db_channel.ar_max_cost = target
                db_channel.save()
                messages.success(request, 'Auto rebalancer max cost for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target) + '%')
            elif update_target == 7:
                stub = lnrouter.RouterStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                channel_point = ln.ChannelPoint()
                channel_point.funding_txid_bytes = bytes.fromhex(db_channel.funding_txid)
                channel_point.funding_txid_str = db_channel.funding_txid
                channel_point.output_index = db_channel.output_index
                stub.UpdateChanStatus(lnr.UpdateChanStatusRequest(chan_point=channel_point, action=0)) if target == 1 else stub.UpdateChanStatus(lnr.UpdateChanStatusRequest(chan_point=channel_point, action=1))
                db_channel.local_disabled = False if target == 1 else True
                db_channel.save()
                messages.success(request, 'Toggled channel state for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') to a value of: ' + ('Enabled' if target == 1 else 'Disabled'))
                if target == 0:
                    messages.warning(request, 'Use with caution, while a channel is disabled (local fees highlighted in red) it will not route out.')
            else:
                messages.error(request, 'Invalid target code. Please try again.')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

@login_required(login_url='/lndg-admin/login/?next=/')
def update_setting(request):
    if request.method == 'POST':
        form = UpdateSetting(request.POST)
        if form.is_valid():
            key = form.cleaned_data['key']
            value = form.cleaned_data['value']
            if key == 'AR-Target%':
                target_percent = value
                try:
                    db_percent_target = LocalSettings.objects.get(key='AR-Target%')
                except:
                    LocalSettings(key='AR-Target%', value='0.05').save()
                    db_percent_target = LocalSettings.objects.get(key='AR-Target%')
                db_percent_target.value = target_percent
                db_percent_target.save()
                Channels.objects.all().update(ar_amt_target=Round(F('capacity')*target_percent, output_field=IntegerField()))
                messages.success(request, 'Updated auto rebalancer target amount for all channels to: ' + str(target_percent))
            elif key == 'AR-Time':
                target_time = int(value)
                try:
                    db_time_target = LocalSettings.objects.get(key='AR-Time')
                except:
                    LocalSettings(key='AR-Time', value='5').save()
                    db_time_target = LocalSettings.objects.get(key='AR-Time')
                db_time_target.value = target_time
                db_time_target.save()
                messages.success(request, 'Updated auto rebalancer target time setting to: ' + str(target_time))
            elif key == 'AR-Enabled':
                enabled = int(value)
                try:
                    db_enabled = LocalSettings.objects.get(key='AR-Enabled')
                except:
                    LocalSettings(key='AR-Enabled', value='0').save()
                    db_enabled = LocalSettings.objects.get(key='AR-Enabled')
                db_enabled.value = enabled
                db_enabled.save()
                messages.success(request, 'Updated auto rebalancer enabled setting to: ' + str(enabled))
            elif key == 'AR-Outbound%':
                outbound_percent = float(value)
                try:
                    db_outbound_target = LocalSettings.objects.get(key='AR-Outbound%')
                except:
                    LocalSettings(key='AR-Outbound%', value='0.75').save()
                    db_outbound_target = LocalSettings.objects.get(key='AR-Outbound%')
                db_outbound_target.value = outbound_percent
                db_outbound_target.save()
                Channels.objects.all().update(ar_out_target=int(outbound_percent*100))
                messages.success(request, 'Updated auto rebalancer target outbound percent setting for all channels to: ' + str(outbound_percent))
            elif key == 'AR-MaxFeeRate':
                fee_rate = int(value)
                try:
                    db_fee_rate = LocalSettings.objects.get(key='AR-MaxFeeRate')
                except:
                    LocalSettings(key='AR-MaxFeeRate', value='100').save()
                    db_fee_rate = LocalSettings.objects.get(key='AR-MaxFeeRate')
                db_fee_rate.value = fee_rate
                db_fee_rate.save()
                messages.success(request, 'Updated auto rebalancer max fee rate setting to: ' + str(fee_rate))
            elif key == 'AR-MaxCost%':
                max_cost = float(value)
                try:
                    db_max_cost = LocalSettings.objects.get(key='AR-MaxCost%')
                except:
                    LocalSettings(key='AR-MaxCost%', value='0.65').save()
                    db_max_cost = LocalSettings.objects.get(key='AR-MaxCost%')
                db_max_cost.value = max_cost
                db_max_cost.save()
                Channels.objects.all().update(ar_max_cost=int(max_cost*100))
                messages.success(request, 'Updated auto rebalancer max cost setting to: ' + str(max_cost))
            elif key == 'AR-Autopilot':
                autopilot = int(value)
                try:
                    db_autopilot = LocalSettings.objects.get(key='AR-Autopilot')
                except:
                    LocalSettings(key='AR-Autopilot', value='0').save()
                    db_autopilot = LocalSettings.objects.get(key='AR-Autopilot')
                db_autopilot.value = autopilot
                db_autopilot.save()
                messages.success(request, 'Updated autopilot setting to: ' + str(autopilot))
            elif key == 'GUI-GraphLinks':
                links = str(value)
                try:
                    db_links = LocalSettings.objects.get(key='GUI-GraphLinks')
                except:
                    LocalSettings(key='GUI-GraphLinks', value='0').save()
                    db_links = LocalSettings.objects.get(key='GUI-GraphLinks')
                db_links.value = links
                db_links.save()
                messages.success(request, 'Updated graph links to use: ' + str(links))
            elif key == 'GUI-NetLinks':
                links = str(value)
                try:
                    db_links = LocalSettings.objects.get(key='GUI-NetLinks')
                except:
                    LocalSettings(key='GUI-NetLinks', value='0').save()
                    db_links = LocalSettings.objects.get(key='GUI-NetLinks')
                db_links.value = links
                db_links.save()
                messages.success(request, 'Updated network links to use: ' + str(links))
            elif key == 'LND-CleanPayments':
                clean_payments = int(value)
                try:
                    db_clean_payments = LocalSettings.objects.get(key='LND-CleanPayments')
                except:
                    LocalSettings(key='LND-CleanPayments', value='0').save()
                    db_clean_payments = LocalSettings.objects.get(key='LND-CleanPayments')
                db_clean_payments.value = clean_payments
                db_clean_payments.save()
                messages.success(request, 'Updated auto payment cleanup setting to: ' + str(clean_payments))
            elif key == 'LND-RetentionDays':
                retention_days = int(value)
                try:
                    db_retention_days = LocalSettings.objects.get(key='LND-RetentionDays')
                except:
                    LocalSettings(key='LND-RetentionDays', value='0').save()
                    db_retention_days = LocalSettings.objects.get(key='LND-RetentionDays')
                db_retention_days.value = retention_days
                db_retention_days.save()
                messages.success(request, 'Updated payment cleanup retention days to: ' + str(retention_days))
            else:
                messages.error(request, 'Invalid Request. Please try again.')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

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