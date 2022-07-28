from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Sum, IntegerField, FloatField, Count, F, Q
from django.db.models.functions import Round
from django.contrib.auth.decorators import login_required
from django.conf import settings
from datetime import datetime, timedelta
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .forms import OpenChannelForm, CloseChannelForm, ConnectPeerForm, AddInvoiceForm, RebalancerForm, ChanPolicyForm, UpdateChannel, UpdateSetting, AutoRebalanceForm, AddTowerForm, RemoveTowerForm, DeleteTowerForm, BatchOpenForm
from .models import Payments, PaymentHops, Invoices, Forwards, Channels, Rebalancer, LocalSettings, Peers, Onchain, Closures, Resolutions, PendingHTLCs, FailedHTLCs, Autopilot, Autofees
from .serializers import ConnectPeerSerializer, FailedHTLCSerializer, LocalSettingsSerializer, OpenChannelSerializer, CloseChannelSerializer, AddInvoiceSerializer, PaymentHopsSerializer, PaymentSerializer, InvoiceSerializer, ForwardSerializer, ChannelSerializer, PendingHTLCSerializer, RebalancerSerializer, UpdateAliasSerializer, PeerSerializer, OnchainSerializer, ClosuresSerializer, ResolutionsSerializer
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps import wtclient_pb2 as wtrpc
from gui.lnd_deps import wtclient_pb2_grpc as wtstub
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
        try:
            stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
            #Get balance and general node information
            node_info = stub.GetInfo(ln.GetInfoRequest())
            balances = stub.WalletBalance(ln.WalletBalanceRequest())
            pending_channels = stub.PendingChannels(ln.PendingChannelsRequest())
            channels = Channels.objects.all()
            limbo_balance = pending_channels.total_limbo_balance
            pending_open = None
            pending_closed = None
            pending_force_closed = None
            waiting_for_close = None
            if pending_channels.pending_open_channels:
                target_resp = pending_channels.pending_open_channels
                peers = Peers.objects.all()
                pending_open = [{'alias':peers.filter(pubkey=target_resp[i].channel.remote_node_pub)[0].alias if peers.filter(pubkey=target_resp[i].channel.remote_node_pub).exists() else None,'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'commit_fee':target_resp[i].commit_fee,'commit_weight':target_resp[i].commit_weight,'fee_per_kw':target_resp[i].fee_per_kw} for i in range(0,len(target_resp))]
            if pending_channels.pending_closing_channels:
                target_resp = pending_channels.pending_closing_channels
                pending_closed = [{'chan_id':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].chan_id if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'alias':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].alias if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type, 'local_commit_fee_sat': target_resp[i].commitments.local_commit_fee_sat, 'limbo_balance':target_resp[i].limbo_balance, 'closing_txid':target_resp[i].closing_txid} for i in range(0,len(target_resp))]
            if pending_channels.pending_force_closing_channels:
                target_resp = pending_channels.pending_force_closing_channels
                pending_force_closed = [{'chan_id':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].chan_id if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'alias':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].alias if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'closing_txid':target_resp[i].closing_txid,'limbo_balance':target_resp[i].limbo_balance,'maturity_height':target_resp[i].maturity_height,'blocks_til_maturity':target_resp[i].blocks_til_maturity if target_resp[i].blocks_til_maturity > 0 else find_next_block_maturity(target_resp[i]),'maturity_datetime':(datetime.now()+timedelta(minutes=(10*target_resp[i].blocks_til_maturity if target_resp[i].blocks_til_maturity > 0 else 10*find_next_block_maturity(target_resp[i]) )))} for i in range(0,len(target_resp))]
            if pending_channels.waiting_close_channels:
                target_resp = pending_channels.waiting_close_channels
                waiting_for_close = [{'chan_id':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].chan_id if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'alias':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].alias if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type, 'local_commit_fee_sat': target_resp[i].commitments.local_commit_fee_sat, 'limbo_balance':target_resp[i].limbo_balance, 'closing_txid':target_resp[i].closing_txid} for i in range(0,len(target_resp))]
            #Get recorded payment events
            payments = Payments.objects.exclude(status=3)
            #Get recorded invoice details
            invoices = Invoices.objects.exclude(state=2)
            #Get recorded forwarding events
            forwards = Forwards.objects.all().annotate(amt_in=Sum('amt_in_msat')/1000).annotate(amt_out=Sum('amt_out_msat')/1000).annotate(ppm=Round((Sum('fee')*1000000000)/Sum('amt_out_msat'), output_field=IntegerField())).order_by('-id')
            #Get current active channels
            active_channels = channels.filter(is_active=True, is_open=True, private=False).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*1000)/Sum('capacity')).annotate(inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*1000)/Sum('capacity')).order_by('outbound_percent')
            active_capacity = 0 if active_channels.count() == 0 else active_channels.aggregate(Sum('capacity'))['capacity__sum']
            active_inbound = 0 if active_capacity == 0 else active_channels.aggregate(Sum('remote_balance'))['remote_balance__sum']
            active_outbound = 0 if active_capacity == 0 else active_channels.aggregate(Sum('local_balance'))['local_balance__sum']
            active_unsettled = 0 if active_capacity == 0 else active_channels.aggregate(Sum('unsettled_balance'))['unsettled_balance__sum']
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
            pending_htlc_count = channels.filter(is_open=True).aggregate(Sum('htlc_count'))['htlc_count__sum'] if channels.filter(is_open=True).exists() else 0
            pending_outbound = channels.filter(is_open=True).aggregate(Sum('pending_outbound'))['pending_outbound__sum'] if channels.filter(is_open=True).exists() else 0
            pending_inbound = channels.filter(is_open=True).aggregate(Sum('pending_inbound'))['pending_inbound__sum'] if channels.filter(is_open=True).exists() else 0
            num_updates = channels.filter(is_open=True).aggregate(Sum('num_updates'))['num_updates__sum'] if channels.filter(is_open=True).exists() else 0
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
                detailed_channel['routed_in_7day'] = forwards_df_in_7d_count.loc[channel.chan_id].amt_out_msat if (forwards_df_in_7d_count.index == channel.chan_id).any() else 0
                detailed_channel['routed_out_7day'] = forwards_df_out_7d_count.loc[channel.chan_id].amt_out_msat if (forwards_df_out_7d_count.index == channel.chan_id).any() else 0
                detailed_channel['amt_routed_in_7day'] = int(forwards_df_in_7d_sum.loc[channel.chan_id].amt_out_msat//10000000)/100 if (forwards_df_in_7d_sum.index == channel.chan_id).any() else 0
                detailed_channel['amt_routed_out_7day'] = int(forwards_df_out_7d_sum.loc[channel.chan_id].amt_out_msat//10000000)/100 if (forwards_df_out_7d_sum.index == channel.chan_id).any() else 0
                detailed_channel['htlc_count'] = channel.htlc_count
                detailed_channel['auto_rebalance'] = channel.auto_rebalance
                detailed_channel['ar_in_target'] = channel.ar_in_target
                detailed_active_channels.append(detailed_channel)
            #Get current inactive channels
            inactive_channels = channels.filter(is_active=False, is_open=True, private=False).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*100)/Sum('capacity')).annotate(inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*100)/Sum('capacity')).order_by('outbound_percent')
            inactive_capacity = 0 if inactive_channels.count() == 0 else inactive_channels.aggregate(Sum('capacity'))['capacity__sum']
            private_channels = channels.filter(is_open=True, private=True).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*100)/Sum('capacity')).annotate(inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*100)/Sum('capacity')).order_by('outbound_percent')
            inactive_outbound = 0 if inactive_channels.count() == 0 else inactive_channels.aggregate(Sum('local_balance'))['local_balance__sum']
            inactive_inbound = 0 if inactive_channels.count() == 0 else inactive_channels.aggregate(Sum('remote_balance'))['remote_balance__sum']
            private_count = private_channels.count()
            active_private = private_channels.filter(is_active=True).count()
            private_capacity = private_channels.aggregate(Sum('capacity'))['capacity__sum']
            private_outbound = 0 if private_count == 0 else private_channels.aggregate(Sum('local_balance'))['local_balance__sum']
            sum_outbound = active_outbound + pending_outbound + inactive_outbound
            sum_inbound = active_inbound + pending_inbound + inactive_inbound
            onchain_txs = Onchain.objects.all()
            onchain_costs_7day = 0 if onchain_txs.filter(time_stamp__gte=filter_7day).count() == 0 else onchain_txs.filter(time_stamp__gte=filter_7day).aggregate(Sum('fee'))['fee__sum']
            closures_7day = Closures.objects.filter(close_height__gte=(node_info.block_height - 1008))
            close_fees_7day = channels.filter(chan_id__in=closures_7day.values('chan_id')).aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures_7day.exists() else 0
            onchain_costs_7day += close_fees_7day
            total_costs_7day = total_7day_fees + onchain_costs_7day
            #Get list of recent rebalance requests
            rebalances = Rebalancer.objects.all().annotate(ppm=Round((Sum('fee_limit')*1000000)/Sum('value'), output_field=IntegerField())).order_by('-id')
            total_channels = node_info.num_active_channels + node_info.num_inactive_channels - private_count
            local_settings = LocalSettings.objects.filter(key__contains='AR-').order_by('key')
            try:
                db_size = round(path.getsize(path.expanduser(LND_DIR_PATH + '/data/graph/' + LND_NETWORK + '/channel.db'))*0.000000001, 3)
            except:
                db_size = 0
            #Build context for front-end and render page
            context = {
                'node_info': node_info,
                'total_channels': total_channels,
                'balances': balances,
                'payments': payments.annotate(ppm=Round((Sum('fee')*1000000)/Sum('value'), output_field=IntegerField())).order_by('-creation_date')[:6],
                'invoices': invoices.order_by('-creation_date')[:6],
                'forwards': forwards[:15],
                'routed_7day': routed_7day,
                'routed_7day_amt': routed_7day_amt,
                'earned_7day': int(total_earned_7day),
                'routed_7day_percent': 0 if sum_outbound == 0 else int((routed_7day_amt/sum_outbound)*100),
                'profit_per_outbound': 0 if sum_outbound == 0 else int((total_earned_7day - total_7day_fees)/(sum_outbound/1000000)),
                'profit_per_outbound_real': 0 if sum_outbound == 0 else int((total_earned_7day - total_costs_7day)/(sum_outbound/1000000)),
                'percent_cost_7day': 0 if total_earned_7day == 0 else int((total_costs_7day/total_earned_7day)*100),
                'onchain_costs_7day': onchain_costs_7day,
                'total_7day_fees': int(total_7day_fees),
                'active_channels': detailed_active_channels,
                'total_capacity': active_capacity + inactive_capacity,
                'active_private': active_private,
                'total_private': private_count,
                'private_outbound': private_outbound,
                'private_capacity': private_capacity,
                'inbound': active_inbound,
                'sum_inbound': sum_inbound,
                'inactive_inbound': inactive_inbound,
                'outbound': active_outbound,
                'sum_outbound': sum_outbound,
                'inactive_outbound': inactive_outbound,
                'unsettled': active_unsettled,
                'inactive_unsettled': pending_outbound + pending_inbound - active_unsettled,
                'total_unsettled': pending_outbound + pending_inbound,
                'limbo_balance': limbo_balance,
                'inactive_channels': inactive_channels,
                'private_channels': private_channels,
                'pending_open': pending_open,
                'pending_closed': pending_closed,
                'pending_force_closed': pending_force_closed,
                'waiting_for_close': waiting_for_close,
                'rebalances': rebalances[:12],
                'chan_policy_form': ChanPolicyForm,
                'local_settings': local_settings,
                'pending_htlc_count': pending_htlc_count,
                'failed_htlcs': FailedHTLCs.objects.all().order_by('-id')[:10],
                '7day_routed_ppm': 0 if routed_7day_amt == 0 else int((total_earned_7day/routed_7day_amt)*1000000),
                '7day_payments_ppm': 0 if payments_7day_amt == 0 else int((total_7day_fees/payments_7day_amt)*1000000),
                'liq_ratio': 0 if sum_outbound == 0 else int((sum_inbound/sum_outbound)*100),
                'eligible_count': channels.filter(is_active=True, is_open=True, private=False, auto_rebalance=True).annotate(inbound_can=((Sum('remote_balance')+Sum('pending_inbound'))*100)/Sum('capacity')).annotate(fee_ratio=(Sum('remote_fee_rate')*100)/Sum('local_fee_rate')).filter(inbound_can__gte=F('ar_in_target'), fee_ratio__lte=F('ar_max_cost')).count(),
                'enabled_count': channels.filter(is_open=True, auto_rebalance=True).count(),
                'available_count': channels.filter(is_active=True, is_open=True, private=False, auto_rebalance=False).annotate(outbound_can=((Sum('local_balance')+Sum('pending_outbound'))*100)/Sum('capacity')).filter(outbound_can__gte=F('ar_out_target')).count(),
                'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
                'graph_links': graph_links(),
                'network_links': network_links(),
                'db_size': db_size,
                'num_updates': num_updates
            }
            return render(request, 'home.html', context)
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def channels(request):
    if request.method == 'GET':
        filter_7day = datetime.now() - timedelta(days=7)
        filter_30day = datetime.now() - timedelta(days=30)
        forwards = Forwards.objects.filter(forward_date__gte=filter_30day)
        payments = Payments.objects.filter(status=2, creation_date__gte=filter_30day, rebal_chan__isnull=False)
        invoices = Invoices.objects.filter(state=1, r_hash__in=payments.values_list('payment_hash'))
        channels = Channels.objects.filter(is_open=True, private=False)
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
            channels_df['mil_capacity'] = channels_df.apply(lambda row: round(row.capacity/1000000, 1), axis=1)
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
            node_outbound = channels_df['local_balance'].sum()
            node_capacity = channels_df['capacity'].sum()
            if node_capacity > 0:
                outbound_ratio = node_outbound/node_capacity
                channels_df['apy_7day'] = channels_df.apply(lambda row: round((row['profits_7day']*5214.2857)/(row['capacity']*outbound_ratio), 2), axis=1)
                channels_df['apy_30day'] = channels_df.apply(lambda row: round((row['profits_30day']*1216.6667)/(row['capacity']*outbound_ratio), 2), axis=1)
                channels_df['cv_7day'] = channels_df.apply(lambda row: round((row['revenue_7day']*5214.2857)/(row['capacity']*outbound_ratio) + (row['revenue_assist_7day']*5214.2857)/(row['capacity']*(1-outbound_ratio)), 2), axis=1)
                channels_df['cv_30day'] = channels_df.apply(lambda row: round((row['revenue_30day']*1216.6667)/(row['capacity']*outbound_ratio) + (row['revenue_assist_30day']*1216.6667)/(row['capacity']*(1-outbound_ratio)), 2), axis=1)
            else:
                channels_df['apy_7day'] = 0.0
                channels_df['apy_30day'] = 0.0
                channels_df['cv_7day'] = 0.0
                channels_df['cv_30day'] = 0.0
        else:
            apy_7day = 0
            apy_30day = 0
        context = {
            'channels': channels_df.sort_values(by=['cv_30day'], ascending=False).to_dict(orient='records'),
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
        filter_1day = datetime.now() - timedelta(days=1)
        filter_7day = datetime.now() - timedelta(days=7)
        channels = Channels.objects.filter(is_open=True, private=False)
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
            channels_df['eligible'] = channels_df.apply(lambda row: (datetime.now()-row['fees_updated']).total_seconds() > 86400, axis=1)
        context = {
            'channels': [] if channels_df.empty else channels_df.sort_values(by=['out_percent']).to_dict(orient='records'),
            'local_settings': LocalSettings.objects.filter(key__contains='AF-').order_by('key'),
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
            channels_df['fee_ratio'] = channels_df.apply(lambda row: 100 if row['local_fee_rate'] == 0 else int(round(((row['remote_fee_rate']/row['local_fee_rate'])*1000)/10, 0)), axis=1)
        context = {
            'channels': channels_df.to_dict(orient='records'),
            'local_settings': LocalSettings.objects.all().order_by('key'),
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
def routes(request):
    if request.method == 'GET':
        try:
            stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
            pubkey = request.GET.urlencode()[1:]
            #print (f"{pubkey=}")
            context = {
                'payment_hash': pubkey,
                'route': PaymentHops.objects.filter(payment_hash__in=PaymentHops.objects.filter(node_pubkey=pubkey).order_by('-id').values_list('payment_hash')[:69]).annotate(ppm=Round((Sum('fee')/Sum('amt'))*1000000, output_field=IntegerField()))
            }
            return render(request, 'route.html', context)
        except:
            error = str(e)
        return render(request, 'error.html', {'error': error})

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
        try:
            stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
            pending_channels = stub.PendingChannels(ln.PendingChannelsRequest())
            channels = Channels.objects.all()
            pending_closed = None
            pending_force_closed = None
            waiting_for_close = None
            if pending_channels.pending_closing_channels:
                target_resp = pending_channels.pending_closing_channels
                pending_closed = [{'chan_id':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].chan_id if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'alias':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].alias if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type, 'local_commit_fee_sat': target_resp[i].commitments.local_commit_fee_sat, 'limbo_balance':target_resp[i].limbo_balance, 'closing_txid':target_resp[i].closing_txid} for i in range(0,len(target_resp))]
            if pending_channels.pending_force_closing_channels:
                target_resp = pending_channels.pending_force_closing_channels
                pending_force_closed = [{'chan_id':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].chan_id if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'alias':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].alias if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'closing_txid':target_resp[i].closing_txid,'limbo_balance':target_resp[i].limbo_balance,'maturity_height':target_resp[i].maturity_height,'blocks_til_maturity':target_resp[i].blocks_til_maturity if target_resp[i].blocks_til_maturity > 0 else find_next_block_maturity(target_resp[i]),'maturity_datetime':(datetime.now()+timedelta(minutes=(10*target_resp[i].blocks_til_maturity if target_resp[i].blocks_til_maturity > 0 else 10*find_next_block_maturity(target_resp[i]) )))} for i in range(0,len(target_resp))]
            if pending_channels.waiting_close_channels:
                target_resp = pending_channels.waiting_close_channels
                waiting_for_close = [{'chan_id':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].chan_id if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'alias':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].alias if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type, 'local_commit_fee_sat': target_resp[i].commitments.local_commit_fee_sat, 'limbo_balance':target_resp[i].limbo_balance, 'closing_txid':target_resp[i].closing_txid} for i in range(0,len(target_resp))]
            closures_df = DataFrame.from_records(Closures.objects.all().values())
            if closures_df.empty:
                merged = DataFrame()
            else:
                channels_df = DataFrame.from_records(Channels.objects.all().values('chan_id', 'alias', 'closing_costs'))
                if channels_df.empty:
                    merged = closures_df
                    merged['alias'] = ''
                else:
                    merged = merge(closures_df, channels_df, on='chan_id', how='left')
                    merged['alias'] = merged['alias'].fillna('')
                    merged['closing_costs'] = merged['closing_costs'].fillna('')
            context = {
                'pending_closed': pending_closed,
                'pending_force_closed': pending_force_closed,
                'waiting_for_close': waiting_for_close,
                'closures': [] if merged.empty else merged.sort_values(by=['close_height'], ascending=False).to_dict(orient='records'),
                'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
                'network_links': network_links(),
                'graph_links': graph_links()
            }
            return render(request, 'closures.html', context)
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')

def find_next_block_maturity(force_closing_channel):

    #print (f"{datetime.now().strftime('%c')} : {force_closing_channel=}")
    if force_closing_channel.blocks_til_maturity > 0:
        return force_closing_channel.blocks_til_maturity
    for pending_htlc in force_closing_channel.pending_htlcs:
        if pending_htlc.blocks_til_maturity > 0:
            #print (f"{datetime.now().strftime('%c')} : {pending_htlc=}")
            return pending_htlc.blocks_til_maturity
    return -1

@login_required(login_url='/lndg-admin/login/?next=/')
def towers(request):
    if request.method == 'GET':
        try:
            stub = wtstub.WatchtowerClientStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
            towers = stub.ListTowers(wtrpc.ListTowersRequest(include_sessions=False)).towers
            active_towers = []
            inactive_towers = []
            for item in towers:
                for address in item.addresses:
                    tower = {}
                    tower['pubkey'] = item.pubkey.hex()
                    tower['address'] = address
                    tower['active'] = item.active_session_candidate
                    tower['num_sessions'] = item.num_sessions
                    active_towers.append(tower) if tower['active'] else inactive_towers.append(tower)
            stats = stub.Stats(wtrpc.StatsRequest())
            context = {
                'active_towers': active_towers,
                'inactive_towers': inactive_towers,
                'stats': stats
            }
            return render(request, 'towers.html', context)
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect(request.META.get('HTTP_REFERER'))

@login_required(login_url='/lndg-admin/login/?next=/')
def add_tower_form(request):
    if request.method == 'POST':
        form = AddTowerForm(request.POST)
        if form.is_valid():
            try:
                stub = wtstub.WatchtowerClientStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                tower = form.cleaned_data['tower']
                if tower.count('@') == 1 and len(tower.split('@')[0]) == 66:
                    peer_pubkey, host = tower.split('@')
                else:
                    raise Exception('Invalid tower connection string.')
                response = stub.AddTower(wtrpc.AddTowerRequest(pubkey=bytes.fromhex(peer_pubkey), address=host))
                messages.success(request, 'Tower addition successful!' + str(response))
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Add tower request failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

@login_required(login_url='/lndg-admin/login/?next=/')
def delete_tower_form(request):
    if request.method == 'POST':
        form = DeleteTowerForm(request.POST)
        if form.is_valid():
            try:
                stub = wtstub.WatchtowerClientStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                pubkey = bytes.fromhex(form.cleaned_data['pubkey'])
                address = form.cleaned_data['address']
                response = stub.RemoveTower(wtrpc.RemoveTowerRequest(pubkey=pubkey, address=address))
                messages.success(request, 'Tower deletion successful!' + str(response))
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Delete tower request failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

@login_required(login_url='/lndg-admin/login/?next=/')
def remove_tower_form(request):
    if request.method == 'POST':
        form = RemoveTowerForm(request.POST)
        if form.is_valid():
            try:
                stub = wtstub.WatchtowerClientStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                pubkey = bytes.fromhex(form.cleaned_data['pubkey'])
                response = stub.RemoveTower(wtrpc.RemoveTowerRequest(pubkey=pubkey))
                messages.success(request, 'Tower removal successful!' + str(response))
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Remove tower request failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

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
            forwards_df = DataFrame.from_records(Forwards.objects.filter(Q(chan_id_in=chan_id) | Q(chan_id_out=chan_id)).values())
            payments_df = DataFrame.from_records(Payments.objects.filter(status=2).filter(chan_out=chan_id).filter(rebal_chan__isnull=False).annotate(ppm=Round((Sum('fee')*1000000)/Sum('value'), output_field=IntegerField())).values())
            invoices_df = DataFrame.from_records(Invoices.objects.filter(state=1).filter(chan_in=chan_id).filter(r_hash__in=Payments.objects.filter(status=2).filter(rebal_chan=chan_id)).values())
            channels_df = DataFrame.from_records(Channels.objects.filter(is_open=True).values())
            node_outbound = channels_df['local_balance'].sum()
            node_capacity = channels_df['capacity'].sum()
            channels_df = DataFrame.from_records(Channels.objects.filter(chan_id=chan_id).values())
            rebalancer_df = DataFrame.from_records(Rebalancer.objects.filter(last_hop_pubkey=channels_df['remote_pubkey'][0]).annotate(ppm=Round((Sum('fee_limit')*1000000)/Sum('value'), output_field=IntegerField())).order_by('-id').values())
            failed_htlc_df = DataFrame.from_records(FailedHTLCs.objects.filter(Q(chan_id_in=chan_id) | Q(chan_id_out=chan_id)).order_by('-id').values())
            channels_df['local_balance'] = channels_df['local_balance'] + channels_df['pending_outbound']
            channels_df['remote_balance'] = channels_df['remote_balance'] + channels_df['pending_inbound']
            channels_df['in_percent'] = int(round((channels_df['remote_balance']/channels_df['capacity'])*100, 0))
            channels_df['out_percent'] = int(round((channels_df['local_balance']/channels_df['capacity'])*100, 0))
            channels_df['open_block'] = int(channels_df.chan_id)>>40
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
            channels_df['amt_routed_in_7day_fees'] = 0
            channels_df['amt_routed_in_1day'] = 0
            channels_df['amt_routed_out'] = 0
            channels_df['amt_routed_out_30day'] = 0
            channels_df['amt_routed_out_7day'] = 0
            channels_df['amt_routed_out_7day_fees'] = 0
            channels_df['amt_routed_out_1day'] = 0
            channels_df['average_in'] = 0
            channels_df['average_in_30day'] = 0
            channels_df['average_in_7day'] = 0
            channels_df['average_in_1day'] = 0
            channels_df['average_out'] = 0
            channels_df['average_out_30day'] = 0
            channels_df['average_out_7day'] = 0
            channels_df['average_out_1day'] = 0
            channels_df['revenue'] = 0
            channels_df['revenue_30day'] = 0
            channels_df['revenue_7day'] = 0
            channels_df['revenue_7day_fees'] = 0
            channels_df['revenue_1day'] = 0
            channels_df['revenue_assist'] = 0
            channels_df['revenue_assist_30day'] = 0
            channels_df['revenue_assist_7day'] = 0
            channels_df['revenue_assist_7day_fees'] = 0
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
            channels_df['attempts'] = 0
            channels_df['attempts_30day'] = 0
            channels_df['attempts_7day'] = 0
            channels_df['attempts_1day'] = 0
            channels_df['success'] = 0
            channels_df['success_30day'] = 0
            channels_df['success_7day'] = 0
            channels_df['success_1day'] = 0
            channels_df['success_rate'] = 0
            channels_df['success_rate_30day'] = 0
            channels_df['success_rate_7day'] = 0
            channels_df['success_rate_1day'] = 0
            channels_df['failed_out'] = 0
            channels_df['failed_out_30day'] = 0
            channels_df['failed_out_7day'] = 0
            channels_df['failed_out_1day'] = 0
            start_date = None
            if failed_htlc_df.shape[0]> 0:
                channels_df['failed_out'] = len(failed_htlc_df[(failed_htlc_df['chan_id_out']==chan_id) & (failed_htlc_df['wire_failure']==15) & (failed_htlc_df['failure_detail']==6) & (failed_htlc_df['amount']>failed_htlc_df['chan_out_liq']+failed_htlc_df['chan_out_pending'])])
                failed_htlc_df_30d = failed_htlc_df.loc[failed_htlc_df['timestamp'] >= filter_30day]
                if failed_htlc_df_30d.shape[0]> 0:
                    channels_df['failed_out_30day'] = len(failed_htlc_df_30d[(failed_htlc_df_30d['chan_id_out']==chan_id) & (failed_htlc_df_30d['wire_failure']==15) & (failed_htlc_df_30d['failure_detail']==6) & (failed_htlc_df_30d['amount']>failed_htlc_df_30d['chan_out_liq']+failed_htlc_df_30d['chan_out_pending'])])
                    failed_htlc_df_7d = failed_htlc_df_30d.loc[failed_htlc_df_30d['timestamp'] >= filter_7day]
                    if failed_htlc_df_7d.shape[0]> 0:
                        channels_df['failed_out_7day'] = len(failed_htlc_df_7d[(failed_htlc_df_7d['chan_id_out']==chan_id) & (failed_htlc_df_7d['wire_failure']==15) & (failed_htlc_df_7d['failure_detail']==6) & (failed_htlc_df_7d['amount']>failed_htlc_df_7d['chan_out_liq']+failed_htlc_df_7d['chan_out_pending'])])
                        failed_htlc_df_1d = failed_htlc_df_7d.loc[failed_htlc_df_7d['timestamp'] >= filter_1day]
                        if failed_htlc_df_1d.shape[0]> 0:
                            channels_df['failed_out_1day'] = len(failed_htlc_df_1d[(failed_htlc_df_1d['chan_id_out']==chan_id) & (failed_htlc_df_1d['wire_failure']==15) & (failed_htlc_df_1d['failure_detail']==6) & (failed_htlc_df_1d['amount']>failed_htlc_df_1d['chan_out_liq']+failed_htlc_df_1d['chan_out_pending'])])
            if rebalancer_df.shape[0]> 0:
                channels_df['attempts'] = len(rebalancer_df[(rebalancer_df['status']>=2) & (rebalancer_df['status']<400)])
                channels_df['success'] = len(rebalancer_df[rebalancer_df['status']==2])
                channels_df['success_rate'] = 0 if channels_df['attempts'][0] == 0 else int((channels_df['success']/channels_df['attempts'])*100)
                rebalancer_df_30d = rebalancer_df.loc[rebalancer_df['stop'] >= filter_30day]
                if rebalancer_df_30d.shape[0]> 0:
                    channels_df['attempts_30day'] = len(rebalancer_df_30d[(rebalancer_df_30d['status']>=2) & (rebalancer_df_30d['status']<400)])
                    channels_df['success_30day'] = len(rebalancer_df_30d[rebalancer_df_30d['status']==2])
                    channels_df['success_rate_30day'] = 0 if channels_df['attempts_30day'][0] == 0 else int((channels_df['success_30day']/channels_df['attempts_30day'])*100)
                    rebalancer_df_7d = rebalancer_df_30d.loc[rebalancer_df_30d['stop'] >= filter_7day]
                    if rebalancer_df_7d.shape[0]> 0:
                        channels_df['attempts_7day'] = len(rebalancer_df_7d[(rebalancer_df_7d['status']>=2) & (rebalancer_df_7d['status']<400)])
                        channels_df['success_7day'] = len(rebalancer_df_7d[rebalancer_df_7d['status']==2])
                        channels_df['success_rate_7day'] = 0 if channels_df['attempts_7day'][0] == 0 else int((channels_df['success_7day']/channels_df['attempts_7day'])*100)
                        rebalancer_df_1d = rebalancer_df_7d.loc[rebalancer_df_7d['stop'] >= filter_1day]
                        if rebalancer_df_1d.shape[0]> 0:
                            channels_df['attempts_1day'] = len(rebalancer_df_1d[(rebalancer_df_1d['status']>=2) & (rebalancer_df_1d['status']<400)])
                            channels_df['success_1day'] = len(rebalancer_df_1d[rebalancer_df_1d['status']==2])
                            channels_df['success_rate_1day'] = 0 if channels_df['attempts_1day'][0] == 0 else int((channels_df['success_1day']/channels_df['attempts_1day'])*100)
            if forwards_df.shape[0]> 0:
                forwards_in_df = forwards_df[forwards_df['chan_id_in'] == chan_id]
                forwards_out_df = forwards_df[forwards_df['chan_id_out'] == chan_id]
                forwards_df['amt_in'] = (forwards_df['amt_in_msat']/1000).astype(int)
                forwards_df['amt_out'] = (forwards_df['amt_out_msat']/1000).astype(int)
                forwards_df['ppm'] = (forwards_df['fee']/(forwards_df['amt_out']/1000000)).astype(int)
            else:
                forwards_in_df = DataFrame()
                forwards_out_df = DataFrame()
            if forwards_in_df.shape[0]> 0:
                forwards_in_df_count = forwards_in_df.groupby('chan_id_in', as_index=True).count()
                forwards_in_df_sum = forwards_in_df.groupby('chan_id_in', as_index=True).sum()
                channels_df['routed_in'] = forwards_in_df_count.loc[chan_id].amt_out_msat
                channels_df['amt_routed_in'] = int(forwards_in_df_sum.loc[chan_id].amt_out_msat/1000)
                channels_df['average_in'] = 0 if channels_df['routed_in'][0] == 0 else int(channels_df['amt_routed_in']/channels_df['routed_in'])
                channels_df['revenue_assist'] = int(forwards_in_df_sum.loc[chan_id].fee) if forwards_in_df_sum.empty == False else 0
                forwards_in_df_30d = forwards_in_df.loc[forwards_in_df['forward_date'] >= filter_30day]
                if forwards_in_df_30d.shape[0] > 0:
                    forwards_in_df_30d_count = forwards_in_df_30d.groupby('chan_id_in', as_index=True).count()
                    forwards_in_df_30d_sum = forwards_in_df_30d.groupby('chan_id_in', as_index=True).sum()
                    channels_df['routed_in_30day'] = forwards_in_df_30d_count.loc[chan_id].amt_out_msat
                    channels_df['amt_routed_in_30day'] = int(forwards_in_df_30d_sum.loc[chan_id].amt_out_msat/1000)
                    channels_df['average_in_30day'] = 0 if channels_df['routed_in_30day'][0] == 0 else int(channels_df['amt_routed_in_30day']/channels_df['routed_in_30day'])
                    channels_df['revenue_assist_30day'] = int(forwards_in_df_30d_sum.loc[chan_id].fee) if forwards_in_df_30d_sum.empty == False else 0
                    forwards_in_df_7d = forwards_in_df_30d.loc[forwards_in_df_30d['forward_date'] >= filter_7day]
                    if forwards_in_df_7d.shape[0] > 0:
                        forwards_in_df_7d_count = forwards_in_df_7d.groupby('chan_id_in', as_index=True).count()
                        forwards_in_df_7d_sum = forwards_in_df_7d.groupby('chan_id_in', as_index=True).sum()
                        channels_df['routed_in_7day'] = forwards_in_df_7d_count.loc[chan_id].amt_out_msat
                        channels_df['amt_routed_in_7day'] = int(forwards_in_df_7d_sum.loc[chan_id].amt_out_msat/1000)
                        channels_df['average_in_7day'] = 0 if channels_df['routed_in_7day'][0] == 0 else int(channels_df['amt_routed_in_7day']/channels_df['routed_in_7day'])
                        channels_df['revenue_assist_7day'] = int(forwards_in_df_7d_sum.loc[chan_id].fee)
                        forwards_in_df_7d_sum = forwards_in_df_7d[forwards_in_df_7d['amt_out_msat']>=1000000].groupby('chan_id_in', as_index=True).sum()
                        if forwards_in_df_7d_sum.shape[0] > 0:
                            channels_df['amt_routed_in_7day_fees'] = int(forwards_in_df_7d_sum.loc[chan_id].amt_out_msat/1000)
                            channels_df['revenue_assist_7day_fees'] = int(forwards_in_df_7d_sum.loc[chan_id].fee)
                        forwards_in_df_1d = forwards_in_df_7d.loc[forwards_in_df_7d['forward_date'] >= filter_1day]
                        if forwards_in_df_1d.shape[0] > 0:
                            forwards_in_df_1d_count = forwards_in_df_1d.groupby('chan_id_in', as_index=True).count()
                            forwards_in_df_1d_sum = forwards_in_df_1d.groupby('chan_id_in', as_index=True).sum()
                            channels_df['routed_in_1day'] = forwards_in_df_1d_count.loc[chan_id].amt_out_msat
                            channels_df['amt_routed_in_1day'] = int(forwards_in_df_1d_sum.loc[chan_id].amt_out_msat/1000)
                            channels_df['average_in_1day'] = 0 if channels_df['routed_in_1day'][0] == 0 else int(channels_df['amt_routed_in_1day']/channels_df['routed_in_1day'])
                            channels_df['revenue_assist_1day'] = int(forwards_in_df_1d_sum.loc[chan_id].fee)
            if forwards_out_df.shape[0]> 0:
                start_date = forwards_out_df['forward_date'].min()
                forwards_out_df_count = forwards_out_df.groupby('chan_id_out', as_index=True).count()
                forwards_out_df_sum = forwards_out_df.groupby('chan_id_out', as_index=True).sum()
                channels_df['routed_out'] = forwards_out_df_count.loc[chan_id].amt_out_msat
                channels_df['amt_routed_out'] = int(forwards_out_df_sum.loc[chan_id].amt_out_msat/1000)
                channels_df['average_out'] = 0 if channels_df['routed_out'][0] == 0 else int(channels_df['amt_routed_out']/channels_df['routed_out'])
                channels_df['revenue'] = int(forwards_out_df_sum.loc[chan_id].fee) if forwards_out_df_sum.empty == False else 0
                forwards_out_df_30d = forwards_out_df.loc[forwards_out_df['forward_date'] >= filter_30day]
                if forwards_out_df_30d.shape[0] > 0:
                    forwards_out_df_30d_count = forwards_out_df_30d.groupby('chan_id_out', as_index=True).count()
                    forwards_out_df_30d_sum = forwards_out_df_30d.groupby('chan_id_out', as_index=True).sum()
                    channels_df['routed_out_30day'] = forwards_out_df_30d_count.loc[chan_id].amt_out_msat
                    channels_df['amt_routed_out_30day'] = int(forwards_out_df_30d_sum.loc[chan_id].amt_out_msat/1000)
                    channels_df['average_out_30day'] = 0 if channels_df['routed_out_30day'][0] == 0 else int(channels_df['amt_routed_out_30day']/channels_df['routed_out_30day'])
                    channels_df['revenue_30day'] = int(forwards_out_df_30d_sum.loc[chan_id].fee) if forwards_out_df_30d_sum.empty == False else 0
                    forwards_out_df_7d = forwards_out_df_30d.loc[forwards_out_df_30d['forward_date'] >= filter_7day]
                    if forwards_out_df_7d.shape[0] > 0:
                        forwards_out_df_7d_count = forwards_out_df_7d.groupby('chan_id_out', as_index=True).count()
                        forwards_out_df_7d_sum = forwards_out_df_7d.groupby('chan_id_out', as_index=True).sum()
                        channels_df['routed_out_7day'] = forwards_out_df_7d_count.loc[chan_id].amt_out_msat
                        channels_df['amt_routed_out_7day'] = int(forwards_out_df_7d_sum.loc[chan_id].amt_out_msat/1000)
                        channels_df['average_out_7day'] = 0 if channels_df['routed_out_7day'][0] == 0 else int(channels_df['amt_routed_out_7day']/channels_df['routed_out_7day'])
                        channels_df['revenue_7day'] = int(forwards_out_df_7d_sum.loc[chan_id].fee)
                        forwards_out_df_7d_sum = forwards_out_df_7d[forwards_out_df_7d['amt_out_msat']>=1000000].groupby('chan_id_out', as_index=True).sum()
                        if forwards_out_df_7d_sum.shape[0] > 0:
                            channels_df['amt_routed_out_7day_fees'] = int(forwards_out_df_7d_sum.loc[chan_id].amt_out_msat/1000)
                            channels_df['revenue_7day_fees'] = int(forwards_out_df_7d_sum.loc[chan_id].fee)
                        forwards_out_df_1d = forwards_out_df_7d.loc[forwards_out_df_7d['forward_date'] >= filter_1day]
                        if forwards_out_df_1d.shape[0] > 0:
                            forwards_out_df_1d_count = forwards_out_df_1d.groupby('chan_id_out', as_index=True).count()
                            forwards_out_df_1d_sum = forwards_out_df_1d.groupby('chan_id_out', as_index=True).sum()
                            channels_df['routed_out_1day'] = forwards_out_df_1d_count.loc[chan_id].amt_out_msat
                            channels_df['amt_routed_out_1day'] = int(forwards_out_df_1d_sum.loc[chan_id].amt_out_msat/1000)
                            channels_df['average_out_1day'] = 0 if channels_df['routed_out_1day'][0] == 0 else int(channels_df['amt_routed_out_1day']/channels_df['routed_out_1day'])
                            channels_df['revenue_1day'] = int(forwards_out_df_1d_sum.loc[chan_id].fee)
            if payments_df.shape[0] > 0:
                payments_df_count = payments_df.groupby('chan_out', as_index=True).count()
                payments_df_sum = payments_df.groupby('chan_out', as_index=True).sum()
                channels_df['rebal_out'] = payments_df_count.loc[chan_id].value
                channels_df['amt_rebal_out'] = int(payments_df_sum.loc[chan_id].value)
                payments_df_30d = payments_df.loc[payments_df['creation_date'] >= filter_30day]
                if payments_df_30d.shape[0] > 0:
                    payments_df_30d_count = payments_df_30d.groupby('chan_out', as_index=True).count()
                    payments_df_30d_sum = payments_df_30d.groupby('chan_out', as_index=True).sum()
                    channels_df['rebal_out_30day'] = payments_df_30d_count.loc[chan_id].value
                    channels_df['amt_rebal_out_30day'] = int(payments_df_30d_sum.loc[chan_id].value)
                    payments_df_7d = payments_df_30d.loc[payments_df_30d['creation_date'] >= filter_7day]
                    if payments_df_7d.shape[0] > 0:
                        payments_df_7d_count = payments_df_7d.groupby('chan_out', as_index=True).count()
                        payments_df_7d_sum = payments_df_7d.groupby('chan_out', as_index=True).sum()
                        channels_df['rebal_out_7day'] = payments_df_7d_count.loc[chan_id].value
                        channels_df['amt_rebal_out_7day'] = int(payments_df_7d_sum.loc[chan_id].value)
                        payments_df_1d = payments_df_7d.loc[payments_df_7d['creation_date'] >= filter_1day]
                        if payments_df_1d.shape[0] > 0:
                            payments_df_1d_count = payments_df_1d.groupby('chan_out', as_index=True).count()
                            payments_df_1d_sum = payments_df_1d.groupby('chan_out', as_index=True).sum()
                            channels_df['rebal_out_1day'] = payments_df_1d_count.loc[chan_id].value
                            channels_df['amt_rebal_out_1day'] = int(payments_df_1d_sum.loc[chan_id].value)
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
                channels_df['rebal_in'] = invoices_df_count.loc[chan_id].amt_paid if invoices_df_count.empty == False else 0
                channels_df['rebal_in_30day'] = invoices_df_30d_count.loc[chan_id].amt_paid if invoices_df_30d_count.empty == False else 0
                channels_df['rebal_in_7day'] = invoices_df_7d_count.loc[chan_id].amt_paid if invoices_df_7d_count.empty == False else 0
                channels_df['rebal_in_1day'] = invoices_df_1d_count.loc[chan_id].amt_paid if invoices_df_1d_count.empty == False else 0
                channels_df['amt_rebal_in'] = int(invoices_df_sum.loc[chan_id].amt_paid) if invoices_df_count.empty == False else 0
                channels_df['amt_rebal_in_30day'] = int(invoices_df_30d_sum.loc[chan_id].amt_paid) if invoices_df_30d_count.empty == False else 0
                channels_df['amt_rebal_in_7day'] = int(invoices_df_7d_sum.loc[chan_id].amt_paid) if invoices_df_7d_count.empty == False else 0
                channels_df['amt_rebal_in_1day'] = int(invoices_df_1d_sum.loc[chan_id].amt_paid) if invoices_df_1d_count.empty == False else 0
                rebal_payments_df = DataFrame.from_records(Payments.objects.filter(status=2).filter(rebal_chan=chan_id).values())
                if rebal_payments_df.shape[0] > 0:
                    rebal_payments_df_30d = rebal_payments_df.loc[rebal_payments_df['creation_date'] >= filter_30day]
                    rebal_payments_df_7d = rebal_payments_df_30d.loc[rebal_payments_df_30d['creation_date'] >= filter_7day]
                    rebal_payments_df_1d = rebal_payments_df_7d.loc[rebal_payments_df_7d['creation_date'] >= filter_1day]
                    invoice_hashes = DataFrame() if invoices_df.empty else invoices_df.groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    invoice_hashes_30d = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    invoice_hashes_7d = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    invoice_hashes_1d = DataFrame() if invoices_df_1d.empty else invoices_df_1d.groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    channels_df['costs'] = 0 if channels_df['rebal_in'][0] == 0 or invoice_hashes.empty == True else int(rebal_payments_df.set_index('payment_hash', inplace=False).loc[invoice_hashes[chan_id]]['fee'].sum())
                    channels_df['costs_30day'] = 0 if channels_df['rebal_in_30day'][0] == 0 or invoice_hashes_30d.empty == True else int(rebal_payments_df_30d.set_index('payment_hash', inplace=False).loc[invoice_hashes_30d[chan_id]]['fee'].sum())
                    channels_df['costs_7day'] = 0 if channels_df['rebal_in_7day'][0] == 0 or invoice_hashes_7d.empty == True else int(rebal_payments_df_7d.set_index('payment_hash', inplace=False).loc[invoice_hashes_7d[chan_id]]['fee'].sum())
                    channels_df['costs_1day'] = 0 if channels_df['rebal_in_1day'][0] == 0 or invoice_hashes_1d.empty == True else int(rebal_payments_df_1d.set_index('payment_hash', inplace=False).loc[invoice_hashes_1d[chan_id]]['fee'].sum())
            channels_df['profits'] = channels_df['revenue'] - channels_df['costs']
            channels_df['profits_30day'] = channels_df['revenue_30day'] - channels_df['costs_30day']
            channels_df['profits_7day'] = channels_df['revenue_7day'] - channels_df['costs_7day']
            channels_df['profits_1day'] = channels_df['revenue_1day'] - channels_df['costs_1day']
            channels_df['profits_vol'] = 0 if channels_df['amt_routed_out'][0] == 0 else int(channels_df['profits'] / (channels_df['amt_routed_out']/1000000))
            channels_df['profits_vol_30day'] = 0 if channels_df['amt_routed_out_30day'][0] == 0 else int(channels_df['profits_30day'] / (channels_df['amt_routed_out_30day']/1000000))
            channels_df['profits_vol_7day'] = 0 if channels_df['amt_routed_out_7day'][0] == 0 else int(channels_df['profits_7day'] / (channels_df['amt_routed_out_7day']/1000000))
            channels_df['profits_vol_1day'] = 0 if channels_df['amt_routed_out_1day'][0] == 0 else int(channels_df['profits_1day'] / (channels_df['amt_routed_out_1day']/1000000))
            channels_df = channels_df.copy()
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
            channels_df['net_routed_7day'] = round((channels_df['amt_routed_out_7day_fees']-channels_df['amt_routed_in_7day_fees'])/channels_df['capacity'], 1)
            channels_df['out_rate'] = int((channels_df['revenue_7day_fees']/channels_df['amt_routed_out_7day_fees'])*1000000) if channels_df['amt_routed_out_7day_fees'][0] > 0 else 0
            channels_df['rebal_ppm'] = int((channels_df['costs_7day']/channels_df['amt_rebal_in_7day'])*1000000) if channels_df['amt_rebal_in_7day'][0] > 0 else 0
            channels_df['profit_margin'] = channels_df['out_rate']*((100-channels_df['ar_max_cost'])/100)
            channels_df['max_suggestion'] = int((channels_df['out_rate'] if channels_df['out_rate'][0] > 0 else channels_df['local_fee_rate'])*1.15) if channels_df['in_percent'][0] > 25 else int(channels_df['local_fee_rate'])
            channels_df['max_suggestion'] = channels_df['local_fee_rate']+25 if channels_df['max_suggestion'][0] > (channels_df['local_fee_rate'][0]+25) else channels_df['max_suggestion']
            channels_df['min_suggestion'] = int((channels_df['out_rate'] if channels_df['out_rate'][0] > 0 else channels_df['local_fee_rate'])*0.75) if channels_df['out_percent'][0] > 25 else int(channels_df['local_fee_rate'])
            channels_df['min_suggestion'] = channels_df['local_fee_rate']-50 if channels_df['min_suggestion'][0] < (channels_df['local_fee_rate'][0]-50) else channels_df['min_suggestion']
            channels_df['assisted_ratio'] = round((channels_df['revenue_assist_7day_fees'] if channels_df['revenue_7day_fees'][0] == 0 else channels_df['revenue_assist_7day_fees']/channels_df['revenue_7day_fees']), 2)
            channels_df['adjusted_out_rate'] = int(channels_df['out_rate']+channels_df['net_routed_7day']*channels_df['assisted_ratio']*multiplier)
            channels_df['adjusted_rebal_rate'] = int(channels_df['rebal_ppm']+channels_df['profit_margin'])
            channels_df['out_rate_only'] = int(channels_df['out_rate']+channels_df['net_routed_7day']*channels_df['out_rate']*(multiplier/100))
            channels_df['fee_rate_only'] = int(channels_df['local_fee_rate']+channels_df['net_routed_7day']*channels_df['local_fee_rate']*(multiplier/100))
            channels_df['new_rate'] = channels_df['adjusted_out_rate'] if channels_df['net_routed_7day'][0] != 0 else (channels_df['adjusted_rebal_rate'] if channels_df['rebal_ppm'][0] > 0 and channels_df['out_rate'][0] > 0 else (channels_df['out_rate_only'] if channels_df['out_rate'][0] > 0 else (channels_df['min_suggestion'] if channels_df['net_routed_7day'][0] == 0 and channels_df['in_percent'][0] < 25 else channels_df['fee_rate_only'])))
            channels_df['new_rate'] = 0 if channels_df['new_rate'][0] < 0 else channels_df['new_rate']
            channels_df['adjustment'] = int(channels_df['new_rate']-channels_df['local_fee_rate'])
            channels_df['new_rate'] = channels_df['local_fee_rate']-10 if channels_df['adjustment'][0]==0 and channels_df['out_percent'][0] >= 25 and channels_df['net_routed_7day'][0]==0 else channels_df['new_rate']
            channels_df['new_rate'] = channels_df['local_fee_rate']+25 if channels_df['adjustment'][0]==0 and channels_df['out_percent'][0] < 25 and channels_df['failed_out_1day'][0]>failed_htlc_limit else channels_df['new_rate']
            channels_df['new_rate'] = channels_df['max_suggestion'] if channels_df['max_suggestion'][0] > 0 and channels_df['new_rate'][0] > channels_df['max_suggestion'][0] else channels_df['new_rate']
            channels_df['new_rate'] = channels_df['min_suggestion'] if channels_df['new_rate'][0] < channels_df['min_suggestion'][0] else channels_df['new_rate']
            channels_df['new_rate'] = int(round(channels_df['new_rate']/increment, 0)*increment)
            channels_df['new_rate'] = max_rate if max_rate < channels_df['new_rate'][0] else channels_df['new_rate']
            channels_df['new_rate'] = min_rate if min_rate > channels_df['new_rate'][0] else channels_df['new_rate']
            channels_df['adjustment'] = int(channels_df['new_rate']-channels_df['local_fee_rate'])
            channels_df['inbound_can'] = ((channels_df['remote_balance']*100)/channels_df['capacity'])/channels_df['ar_in_target']
            channels_df['fee_ratio'] = 100 if channels_df['local_fee_rate'][0] == 0 else int(round(((channels_df['remote_fee_rate']/channels_df['local_fee_rate'])*1000)/10, 0))
            channels_df['fee_check'] = 1 if channels_df['ar_max_cost'][0] == 0 else int(round(((channels_df['fee_ratio']/channels_df['ar_max_cost'])*1000)/10, 0))
            channels_df = channels_df.copy()
            channels_df['steps'] = 0 if channels_df['inbound_can'][0] < 1 else int(((channels_df['in_percent']-channels_df['ar_in_target'])/((channels_df['ar_amt_target']/channels_df['capacity'])*100))+0.999)
            channels_df['apy'] = 0.0
            channels_df['apy_30day'] = 0.0
            channels_df['apy_7day'] = 0.0
            channels_df['apy_1day'] = 0.0
            channels_df['assisted_apy'] = 0.0
            channels_df['assisted_apy_30day'] = 0.0
            channels_df['assisted_apy_7day'] = 0.0
            channels_df['assisted_apy_1day'] = 0.0
            channels_df['cv'] = 0.0
            channels_df['cv_30day'] = 0.0
            channels_df['cv_7day'] = 0.0
            channels_df['cv_1day'] = 0.0
            if node_capacity > 0:
                outbound_ratio = node_outbound/node_capacity
                if start_date is not None:
                    time_delta = datetime.now() - start_date.to_pydatetime()
                    days_routing = time_delta.days + (time_delta.seconds/86400)
                    channels_df['apy'] = round(((channels_df['profits']/days_routing)*36500)/(channels_df['capacity']*outbound_ratio), 2)
                    channels_df['assisted_apy'] = round(((channels_df['revenue_assist']/days_routing)*36500)/(channels_df['capacity']*(1-outbound_ratio)), 2)
                    channels_df['cv'] = round(((channels_df['revenue']/days_routing)*36500)/(channels_df['capacity']*outbound_ratio) + channels_df['assisted_apy'], 2)
                channels_df['apy_30day'] = round((channels_df['profits_30day']*1216.6667)/(channels_df['capacity']*outbound_ratio), 2)
                channels_df['apy_7day'] = round((channels_df['profits_7day']*5214.2857)/(channels_df['capacity']*outbound_ratio), 2)
                channels_df['apy_1day'] = round((channels_df['profits_1day']*36500)/(channels_df['capacity']*outbound_ratio), 2)
                channels_df['assisted_apy_30day'] = round((channels_df['revenue_assist_30day']*1216.6667)/(channels_df['capacity']*(1-outbound_ratio)), 2)
                channels_df['assisted_apy_7day'] = round((channels_df['revenue_assist_7day']*5214.2857)/(channels_df['capacity']*(1-outbound_ratio)), 2)
                channels_df['assisted_apy_1day'] = round((channels_df['revenue_assist_1day']*36500)/(channels_df['capacity']*(1-outbound_ratio)), 2)
                channels_df['cv_30day'] = round((channels_df['revenue_30day']*1216.6667)/(channels_df['capacity']*outbound_ratio) + channels_df['assisted_apy_30day'], 2)
                channels_df['cv_7day'] = round((channels_df['revenue_7day']*5214.2857)/(channels_df['capacity']*outbound_ratio) + channels_df['assisted_apy_7day'], 2)
                channels_df['cv_1day'] = round((channels_df['revenue_1day']*36500)/(channels_df['capacity']*outbound_ratio) + channels_df['assisted_apy_1day'], 2)
        else:
            channels_df = DataFrame()
            forwards_df = DataFrame()
            payments_df = DataFrame()
            invoices_df = DataFrame()
            rebalancer_df = DataFrame()
            failed_htlc_df = DataFrame()
        context = {
            'chan_id': chan_id,
            'channel': [] if channels_df.empty else channels_df.to_dict(orient='records')[0],
            'incoming_htlcs': PendingHTLCs.objects.filter(chan_id=chan_id).filter(incoming=True).order_by('hash_lock'),
            'outgoing_htlcs': PendingHTLCs.objects.filter(chan_id=chan_id).filter(incoming=False).order_by('hash_lock'),
            'forwards': [] if forwards_df.empty else forwards_df.sort_values(by=['forward_date'], ascending=False).to_dict(orient='records')[:5],
            'payments': [] if payments_df.empty else payments_df.sort_values(by=['creation_date'], ascending=False).to_dict(orient='records')[:5],
            'invoices': [] if invoices_df.empty else invoices_df.sort_values(by=['settle_date'], ascending=False).to_dict(orient='records')[:5],
            'rebalances': [] if rebalancer_df.empty else rebalancer_df.to_dict(orient='records')[:5],
            'failed_htlcs': [] if failed_htlc_df.empty else failed_htlc_df.to_dict(orient='records')[:5],
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
        channels = Channels.objects.filter(is_active=True, is_open=True, private=False).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*1000)/Sum('capacity')).annotate(inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*1000)/Sum('capacity'))
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
        stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        block_height = stub.GetInfo(ln.GetInfoRequest()).block_height
        context = {
            'incoming_htlcs': PendingHTLCs.objects.filter(incoming=True).annotate(blocks_til_expiration=Sum('expiration_height')-block_height).annotate(hours_til_expiration=((Sum('expiration_height')-block_height)*10)/60).order_by('hash_lock'),
            'outgoing_htlcs': PendingHTLCs.objects.filter(incoming=False).annotate(blocks_til_expiration=Sum('expiration_height')-block_height).annotate(hours_til_expiration=((Sum('expiration_height')-block_height)*10)/60).order_by('hash_lock')
        }
        return render(request, 'pending_htlcs.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def failed_htlcs(request):
    if request.method == 'GET':
        context = {
            'failed_htlcs': FailedHTLCs.objects.all().order_by('-id')[:150],
        }
        return render(request, 'failed_htlcs.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def payments(request):
    if request.method == 'GET':
        context = {
            'payments': Payments.objects.filter(status=2).annotate(ppm=Round((Sum('fee')*1000000)/Sum('value'), output_field=IntegerField())).order_by('-creation_date')[:150],
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
def batch(request):
    if request.method == 'GET':
        context = {
            'iterator': range(1,11),
        }
        return render(request, 'batch.html', context)
    else:
        return redirect(request.META.get('HTTP_REFERER'))

def open_peer(peer_pubkey, stub):
    if Peers.objects.filter(pubkey=peer_pubkey, connected=True).exists():
        return True
    else:
        try:
            node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey, include_channels=False)).node
            host = node.addresses[0].addr
            ln_addr = ln.LightningAddress(pubkey=peer_pubkey, host=host)
            stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
            return True
        except:
            return False

@login_required(login_url='/lndg-admin/login/?next=/')
def batch_open(request):
    if request.method == 'POST':
        form = BatchOpenForm(request.POST)
        if form.is_valid():
            count = 0
            fail = False
            open_list = []
            stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
            if form.cleaned_data['pubkey1'] and form.cleaned_data['amt1'] and len(form.cleaned_data['pubkey1']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey1']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':peer_pubkey, 'amt':form.cleaned_data['amt1']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 1!')
            if form.cleaned_data['pubkey2'] and form.cleaned_data['amt2'] and len(form.cleaned_data['pubkey2']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey2']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey2'], 'amt':form.cleaned_data['amt2']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 2!')
            if form.cleaned_data['pubkey3'] and form.cleaned_data['amt3'] and len(form.cleaned_data['pubkey3']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey3']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey3'], 'amt':form.cleaned_data['amt3']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 3!')
            if form.cleaned_data['pubkey4'] and form.cleaned_data['amt4'] and len(form.cleaned_data['pubkey4']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey4']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey4'], 'amt':form.cleaned_data['amt4']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 4!')
            if form.cleaned_data['pubkey5'] and form.cleaned_data['amt5'] and len(form.cleaned_data['pubkey5']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey5']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey5'], 'amt':form.cleaned_data['amt5']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 5!')
            if form.cleaned_data['pubkey6'] and form.cleaned_data['amt6'] and len(form.cleaned_data['pubkey6']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey6']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey6'], 'amt':form.cleaned_data['amt6']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 6!')
            if form.cleaned_data['pubkey7'] and form.cleaned_data['amt7'] and len(form.cleaned_data['pubkey7']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey7']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey7'], 'amt':form.cleaned_data['amt7']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 7!')
            if form.cleaned_data['pubkey8'] and form.cleaned_data['amt8'] and len(form.cleaned_data['pubkey8']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey8']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey8'], 'amt':form.cleaned_data['amt8']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 8!')
            if form.cleaned_data['pubkey9'] and form.cleaned_data['amt9'] and len(form.cleaned_data['pubkey9']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey9']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey9'], 'amt':form.cleaned_data['amt9']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 9!')
            if form.cleaned_data['pubkey10'] and form.cleaned_data['amt10'] and len(form.cleaned_data['pubkey10']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey10']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey10'], 'amt':form.cleaned_data['amt10']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 10!')
            if fail == True:
                return redirect('batch')
            if len (open_list) > 0:
                try:
                    channels = []
                    for open in open_list:
                        channel_open = ln.BatchOpenChannel()
                        channel_open.node_pubkey = bytes.fromhex(open['pubkey'])
                        channel_open.local_funding_amount = open['amt']
                        channels.append(channel_open)
                    response = stub.BatchOpenChannel(ln.BatchOpenChannelRequest(channels=channels, sat_per_vbyte=form.cleaned_data['fee_rate']))
                    print(response)
                    messages.success(request, 'Batch opened channels!')
                except Exception as e:
                    error = str(e)
                    details_index = error.find('details =') + 11
                    debug_error_index = error.find('debug_error_string =') - 3
                    error_msg = error[details_index:debug_error_index]
                    messages.error(request, 'Batch open failed! Error: ' + error_msg)
            else:
                messages.error(request, 'No channels specified!')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('batch')

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
        filter_7day = datetime.now() - timedelta(days=7)
        rebalancer_7d_df = DataFrame.from_records(Rebalancer.objects.filter(stop__gte=filter_7day).order_by('-id').values())
        channels_df = DataFrame.from_records(Channels.objects.filter(is_open=True, private=False).annotate(percent_inbound=((Sum('remote_balance')+Sum('pending_inbound'))*100)/Sum('capacity')).annotate(percent_outbound=((Sum('local_balance')+Sum('pending_outbound'))*100)/Sum('capacity')).order_by('-is_active', 'percent_outbound').values())
        if channels_df.shape[0] > 0:
            channels_df['inbound_can'] = channels_df['percent_inbound'] / channels_df['ar_in_target']
            channels_df['fee_ratio'] = channels_df.apply(lambda row: 100 if row['local_fee_rate'] == 0 else int(round(((row['remote_fee_rate']/row['local_fee_rate'])*1000)/10, 0)), axis=1)
            channels_df['fee_check'] = channels_df.apply(lambda row: 1 if row['ar_max_cost'] == 0 else int(round(((row['fee_ratio']/row['ar_max_cost'])*1000)/10, 0)), axis=1)
            channels_df['steps'] = channels_df.apply(lambda row: 0 if row['inbound_can'] < 1 else int(((row['percent_inbound']-row['ar_in_target'])/((row['ar_amt_target']/row['capacity'])*100))+0.999), axis=1)
            rebalancer_count_7d_df = DataFrame() if rebalancer_7d_df.empty else rebalancer_7d_df[rebalancer_7d_df['status']>=2][rebalancer_7d_df['status']<400]
            channels_df['attempts'] = channels_df.apply(lambda row: 0 if rebalancer_count_7d_df.empty else rebalancer_count_7d_df[rebalancer_count_7d_df['last_hop_pubkey']==row.remote_pubkey].shape[0], axis=1)
            channels_df['success'] = channels_df.apply(lambda row: 0 if rebalancer_count_7d_df.empty else rebalancer_count_7d_df[rebalancer_count_7d_df['last_hop_pubkey']==row.remote_pubkey][rebalancer_count_7d_df['status']==2].shape[0], axis=1)
            channels_df['success_rate'] = channels_df.apply(lambda row: 0 if row['attempts'] == 0 else int((row['success']/row['attempts'])*100), axis=1)
            enabled_df = channels_df[channels_df['auto_rebalance']==True]
            eligible_df = enabled_df[enabled_df['is_active']==True][enabled_df['inbound_can']>=1][enabled_df['fee_check']<100]
            eligible_count = eligible_df.shape[0]
            enabled_count = enabled_df.shape[0]
        else:
            eligible_count = 0
            enabled_count = 0
        available_df = channels_df[channels_df['auto_rebalance']==False][channels_df['is_active']==True][channels_df['percent_outbound'] / channels_df['ar_out_target']>=1]
        available_count = available_df.shape[0]
        context = {
            'eligible_count': eligible_count,
            'enabled_count': enabled_count,
            'available_count': available_count,
            'channels': channels_df.to_dict(orient='records'),
            'rebalancer': Rebalancer.objects.all().annotate(ppm=Round((Sum('fee_limit')*1000000)/Sum('value'), output_field=IntegerField())).order_by('-id')[:20],
            'rebalancer_form': RebalancerForm,
            'local_settings': LocalSettings.objects.filter(key__contains='AR-').order_by('key'),
            'network': 'testnet/' if LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links()
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
            'autopilot': Autopilot.objects.all().order_by('-id')
        }
        return render(request, 'autopilot.html', context)
    else:
        return redirect('home')

@login_required(login_url='/lndg-admin/login/?next=/')
def autofees(request):
    if request.method == 'GET':
        context = {
            'autofees': Autofees.objects.all().order_by('-id')
        }
        return render(request, 'autofees.html', context)
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
                    if len(chan_ids) > 0:
                        target_alias = Channels.objects.filter(is_active=True, is_open=True, remote_pubkey=form.cleaned_data['last_hop_pubkey'])[0].alias if Channels.objects.filter(is_active=True, is_open=True, remote_pubkey=form.cleaned_data['last_hop_pubkey']).exists() else ''
                        fee_limit = round(form.cleaned_data['fee_limit']*form.cleaned_data['value']*0.000001, 3)
                        Rebalancer(value=form.cleaned_data['value'], fee_limit=fee_limit, outgoing_chan_ids=str(chan_ids).replace('\'', ''), last_hop_pubkey=form.cleaned_data['last_hop_pubkey'], target_alias=target_alias, duration=form.cleaned_data['duration'], manual=True).save()
                        messages.success(request, 'Rebalancer request created!')
                    else:
                        messages.error(request, 'You must select atleast one outgoing channel.')
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
    return redirect(request.META.get('HTTP_REFERER'))

@login_required(login_url='/lndg-admin/login/?next=/')
def update_chan_policy(request):
    if request.method == 'POST':
        form = ChanPolicyForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['new_base_fee'] is not None or form.cleaned_data['new_fee_rate'] is not None or form.cleaned_data['new_cltv'] is not None:
                try:
                    stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                    if form.cleaned_data['target_all']:
                        if form.cleaned_data['new_base_fee'] is not None and form.cleaned_data['new_fee_rate'] is not None and form.cleaned_data['new_cltv'] is not None:
                            args = {'global': True, 'base_fee_msat': form.cleaned_data['new_base_fee'], 'fee_rate': (form.cleaned_data['new_fee_rate']/1000000), 'time_lock_delta': form.cleaned_data['new_cltv']}
                            stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(**args))
                            channels = Channels.objects.filter(is_open=True)
                            channels.update(local_base_fee=form.cleaned_data['new_base_fee'])
                            channels.update(local_fee_rate=form.cleaned_data['new_fee_rate'])
                            channels.update(local_cltv=form.cleaned_data['new_cltv'])
                            channels.update(fees_updated=datetime.now())
                        else:
                            messages.error(request, 'You must specify all parameters when updating all channels.')
                            return redirect('home')
                    elif len(form.cleaned_data['target_chans']) > 0:
                        for channel in form.cleaned_data['target_chans']:
                            channel_point = ln.ChannelPoint()
                            channel_point.funding_txid_bytes = bytes.fromhex(channel.funding_txid)
                            channel_point.funding_txid_str = channel.funding_txid
                            channel_point.output_index = channel.output_index
                            new_base_fee = form.cleaned_data['new_base_fee'] if form.cleaned_data['new_base_fee'] is not None else channel.local_base_fee
                            new_fee_rate = form.cleaned_data['new_fee_rate']/1000000 if form.cleaned_data['new_fee_rate'] is not None else channel.local_fee_rate/1000000
                            new_cltv = form.cleaned_data['new_cltv'] if form.cleaned_data['new_cltv'] is not None else channel.local_cltv
                            stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=new_base_fee, fee_rate=new_fee_rate, time_lock_delta=new_cltv))
                            db_channel = Channels.objects.get(chan_id=channel.chan_id)
                            db_channel.local_base_fee = new_base_fee
                            db_channel.local_fee_rate = new_fee_rate*1000000
                            db_channel.local_cltv = new_cltv
                            if form.cleaned_data['new_fee_rate'] is not None:
                                db_channel.fees_updated = datetime.now()
                            db_channel.save()
                    else:
                        messages.error(request, 'No channels were specified in the update request!')
                        return redirect('home')
                    messages.success(request, 'Channel policies updated! This will be broadcast during the next graph update!')
                except Exception as e:
                    error = str(e)
                    details_index = error.find('details =') + 11
                    debug_error_index = error.find('debug_error_string =') - 3
                    error_msg = error[details_index:debug_error_index]
                    messages.error(request, 'Error updating channel policies! Error: ' + error_msg)
            else:
                messages.error(request, 'You must specify at least one parameter.')
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
                target_percent = float(form.cleaned_data['target_percent'])
                try:
                    db_percent_target = LocalSettings.objects.get(key='AR-Target%')
                except:
                    LocalSettings(key='AR-Target%', value='5').save()
                    db_percent_target = LocalSettings.objects.get(key='AR-Target%')
                db_percent_target.value = target_percent
                db_percent_target.save()
                if form.cleaned_data['targetallchannels']:
                    Channels.objects.all().update(ar_amt_target=Round(F('capacity')*(target_percent/100), output_field=IntegerField()))
                    messages.success(request, 'Updated auto rebalancer target amount for all channels to: ' + str(target_percent))
                else:
                    messages.success(request, 'Updated auto rebalancer target amount in local settings: ' + str(target_percent))
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
                outbound_percent = int(form.cleaned_data['outbound_percent'])
                try:
                    db_outbound_target = LocalSettings.objects.get(key='AR-Outbound%')
                except:
                    LocalSettings(key='AR-Outbound%', value='75').save()
                    db_outbound_target = LocalSettings.objects.get(key='AR-Outbound%')
                db_outbound_target.value = outbound_percent
                db_outbound_target.save()
                if form.cleaned_data['targetallchannels']:
                    Channels.objects.all().update(ar_out_target=int(outbound_percent))
                    messages.success(request, 'Updated auto rebalancer target outbound percent setting for all channels to: ' + str(outbound_percent))
                else:
                    messages.success(request, 'Updated auto rebalancer target outbound percent setting in local settings to: ' + str(outbound_percent))
            if form.cleaned_data['inbound_percent'] is not None:
                inbound_percent = int(form.cleaned_data['inbound_percent'])
                try:
                    db_inbound_target = LocalSettings.objects.get(key='AR-Inbound%')
                except:
                    LocalSettings(key='AR-Inbound%', value='100').save()
                    db_inbound_target = LocalSettings.objects.get(key='AR-Inbound%')
                db_inbound_target.value = inbound_percent
                db_inbound_target.save()
                if form.cleaned_data['targetallchannels']:
                    Channels.objects.all().update(ar_out_target=int(outbound_percent))
                    messages.success(request, 'Updated auto rebalancer target inbound percent setting for all channels to: ' + str(inbound_percent))
                else:
                    messages.success(request, 'Updated auto rebalancer target inbound percent setting in local settigs to: ' + str(inbound_percent))
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
                max_cost = int(form.cleaned_data['max_cost'])
                try:
                    db_max_cost = LocalSettings.objects.get(key='AR-MaxCost%')
                except:
                    LocalSettings(key='AR-MaxCost%', value='65').save()
                    db_max_cost = LocalSettings.objects.get(key='AR-MaxCost%')
                db_max_cost.value = max_cost
                db_max_cost.save()
                if form.cleaned_data['targetallchannels']:
                    Channels.objects.all().update(ar_max_cost=int(max_cost))
                    messages.success(request, 'Updated auto rebalancer max cost setting for all channels to: ' + str(max_cost))
                else:
                    messages.success(request, 'Updated auto rebalancer max cost setting in local settings to: ' + str(max_cost))
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
            if form.cleaned_data['autopilotdays'] is not None:
                autopilotdays = form.cleaned_data['autopilotdays']
                try:
                    db_autopilotdays = LocalSettings.objects.get(key='AR-APDays')
                except:
                    LocalSettings(key='AR-APDays', value='7').save()
                    db_autopilotdays = LocalSettings.objects.get(key='AR-APDays')
                db_autopilotdays.value = autopilotdays
                db_autopilotdays.save()
                messages.success(request, 'Updated autopilot days setting to: ' + str(autopilotdays))
            if form.cleaned_data['variance'] is not None:
                variance = form.cleaned_data['variance']
                try:
                    db_variance = LocalSettings.objects.get(key='AR-Variance')
                except:
                    LocalSettings(key='AR-Variance', value='0').save()
                    db_variance = LocalSettings.objects.get(key='AR-Variance')
                db_variance.value = variance
                db_variance.save()
                messages.success(request, 'Updated variance setting to: ' + str(variance))
            if form.cleaned_data['wait_period'] is not None:
                wait_period = form.cleaned_data['wait_period']
                try:
                    db_wait_period = LocalSettings.objects.get(key='AR-WaitPeriod')
                except:
                    LocalSettings(key='AR-WaitPeriod', value='30').save()
                    db_wait_period = LocalSettings.objects.get(key='AR-WaitPeriod')
                db_wait_period.value = wait_period
                db_wait_period.save()
                messages.success(request, 'Updated wait period setting to: ' + str(wait_period))
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
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=target, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv))
                db_channel.local_base_fee = target
                db_channel.save()
                messages.success(request, 'Base fee for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
            elif update_target == 1:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                channel_point = ln.ChannelPoint()
                channel_point.funding_txid_bytes = bytes.fromhex(db_channel.funding_txid)
                channel_point.funding_txid_str = db_channel.funding_txid
                channel_point.output_index = db_channel.output_index
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(target/1000000), time_lock_delta=db_channel.local_cltv))
                db_channel.local_fee_rate = target
                db_channel.fees_updated = datetime.now()
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
                messages.success(request, 'Auto rebalancer status for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(db_channel.auto_rebalance))
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
            elif update_target == 8:
                db_channel.auto_fees = True if db_channel.auto_fees == False else False
                db_channel.save()
                messages.success(request, 'Auto fees status for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(db_channel.auto_fees))
            elif update_target == 9:
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                channel_point = ln.ChannelPoint()
                channel_point.funding_txid_bytes = bytes.fromhex(db_channel.funding_txid)
                channel_point.funding_txid_str = db_channel.funding_txid
                channel_point.output_index = db_channel.output_index
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=target))
                db_channel.local_cltv = target
                db_channel.save()
                messages.success(request, 'CLTV for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
            elif update_target == 10:
                db_channel.closing_costs = target
                db_channel.save()
                messages.success(request, 'Closing costs for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(db_channel.closing_costs))
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
                target_percent = float(value)
                try:
                    db_percent_target = LocalSettings.objects.get(key='AR-Target%')
                except:
                    LocalSettings(key='AR-Target%', value='5').save()
                    db_percent_target = LocalSettings.objects.get(key='AR-Target%')
                db_percent_target.value = target_percent
                db_percent_target.save()
                messages.success(request, 'Updated auto rebalancer target amount to: ' + str(target_percent))
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
                outbound_percent = int(value)
                try:
                    db_outbound_target = LocalSettings.objects.get(key='AR-Outbound%')
                except:
                    LocalSettings(key='AR-Outbound%', value='75').save()
                    db_outbound_target = LocalSettings.objects.get(key='AR-Outbound%')
                db_outbound_target.value = outbound_percent
                db_outbound_target.save()
                messages.success(request, 'Updated auto rebalancer target outbound percent setting: ' + str(outbound_percent))
            elif key == 'AR-Inbound%':
                inbound_percent = int(value)
                try:
                    db_inbound_target = LocalSettings.objects.get(key='AR-Inbound%')
                except:
                    LocalSettings(key='AR-Inbound%', value='100').save()
                    db_inbound_target = LocalSettings.objects.get(key='AR-Inbound%')
                db_inbound_target.value = inbound_percent
                db_inbound_target.save()
                messages.success(request, 'Updated auto rebalancer target inbound percent setting: ' + str(inbound_percent))
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
                max_cost = int(value)
                try:
                    db_max_cost = LocalSettings.objects.get(key='AR-MaxCost%')
                except:
                    LocalSettings(key='AR-MaxCost%', value='65').save()
                    db_max_cost = LocalSettings.objects.get(key='AR-MaxCost%')
                db_max_cost.value = max_cost
                db_max_cost.save()
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
            elif key == 'AR-APDays':
                apdays = int(value)
                try:
                    db_apdays = LocalSettings.objects.get(key='AR-APDays')
                except:
                    LocalSettings(key='AR-APDays', value='7').save()
                    db_apdays = LocalSettings.objects.get(key='AR-APDays')
                db_apdays.value = apdays
                db_apdays.save()
                messages.success(request, 'Updated Autopilot Days setting to: ' + str(apdays))                
            elif key == 'AR-Variance':
                variance = int(value)
                try:
                    db_variance = LocalSettings.objects.get(key='AR-Variance')
                except:
                    LocalSettings(key='AR-Variance', value='0').save()
                    db_variance = LocalSettings.objects.get(key='AR-Variance')
                db_variance.value = variance
                db_variance.save()
                messages.success(request, 'Updated variance setting to: ' + str(variance))
            elif key == 'AR-WaitPeriod':
                wait_period = int(value)
                try:
                    db_wait_period = LocalSettings.objects.get(key='AR-WaitPeriod')
                except:
                    LocalSettings(key='AR-WaitPeriod', value='0').save()
                    db_wait_period = LocalSettings.objects.get(key='AR-WaitPeriod')
                db_wait_period.value = wait_period
                db_wait_period.save()
                messages.success(request, 'Updated wait period setting to: ' + str(wait_period))
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
            elif key == 'ALL-oRate':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                channels = Channels.objects.filter(is_open=True)
                for db_channel in channels:
                    channel_point = ln.ChannelPoint()
                    channel_point.funding_txid_bytes = bytes.fromhex(db_channel.funding_txid)
                    channel_point.funding_txid_str = db_channel.funding_txid
                    channel_point.output_index = db_channel.output_index
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(target/1000000), time_lock_delta=db_channel.local_cltv))
                    db_channel.local_fee_rate = target
                    db_channel.fees_updated = datetime.now()
                    db_channel.save()
                messages.success(request, 'Fee rate for all open channels updated to a value of: ' + str(target))
            elif key == 'ALL-oBase':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                channels = Channels.objects.filter(is_open=True)
                for db_channel in channels:
                    stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                    channel_point = ln.ChannelPoint()
                    channel_point.funding_txid_bytes = bytes.fromhex(db_channel.funding_txid)
                    channel_point.funding_txid_str = db_channel.funding_txid
                    channel_point.output_index = db_channel.output_index
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=target, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv))
                    db_channel.local_base_fee = target
                    db_channel.save()
                messages.success(request, 'Base fee for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-CLTV':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                channels = Channels.objects.filter(is_open=True)
                for db_channel in channels:
                    stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
                    channel_point = ln.ChannelPoint()
                    channel_point.funding_txid_bytes = bytes.fromhex(db_channel.funding_txid)
                    channel_point.funding_txid_str = db_channel.funding_txid
                    channel_point.output_index = db_channel.output_index
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=target))
                    db_channel.local_cltv = target
                    db_channel.save()
                messages.success(request, 'CLTV for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-Amts':
                target = int(value)
                channels = Channels.objects.filter(is_open=True).update(ar_amt_target=target)
                messages.success(request, 'AR target amounts for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-MaxCost':
                target = int(value)
                channels = Channels.objects.filter(is_open=True).update(ar_max_cost=target)
                messages.success(request, 'AR max cost %s for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-oTarget':
                target = int(value)
                channels = Channels.objects.filter(is_open=True).update(ar_out_target=target)
                messages.success(request, 'AR outbound liquidity target %s for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-iTarget':
                target = int(value)
                channels = Channels.objects.filter(is_open=True).update(ar_in_target=target)
                messages.success(request, 'AR inbound liquidity target %s for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-AR':
                target = int(value)
                channels = Channels.objects.filter(is_open=True).update(auto_rebalance=target)
                messages.success(request, 'Auto-Rebalance targeting for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-AF':
                target = int(value)
                channels = Channels.objects.filter(is_open=True, private=False).update(auto_fees=target)
                messages.success(request, 'Auto Fees setting for all channels updated to a value of: ' + str(target))
            elif key == 'AF-Enabled':
                enabled = int(value)
                try:
                    db_enabled = LocalSettings.objects.get(key='AF-Enabled')
                except:
                    LocalSettings(key='AF-Enabled', value='0').save()
                    db_enabled = LocalSettings.objects.get(key='AF-Enabled')
                db_enabled.value = enabled
                db_enabled.save()
                messages.success(request, 'Updated autofees enabled setting to: ' + str(enabled))
            elif key == 'AF-MaxRate':
                enabled = int(value)
                try:
                    db_enabled = LocalSettings.objects.get(key='AF-MaxRate')
                except:
                    LocalSettings(key='AF-MaxRate', value='2500').save()
                    db_enabled = LocalSettings.objects.get(key='AF-MaxRate')
                db_enabled.value = enabled
                db_enabled.save()
                messages.success(request, 'Updated autofees max rate setting to: ' + str(enabled))
            elif key == 'AF-MinRate':
                enabled = int(value)
                try:
                    db_enabled = LocalSettings.objects.get(key='AF-MinRate')
                except:
                    LocalSettings(key='AF-MinRate', value='0').save()
                    db_enabled = LocalSettings.objects.get(key='AF-MinRate')
                db_enabled.value = enabled
                db_enabled.save()
                messages.success(request, 'Updated autofees min rate setting to: ' + str(enabled))
            elif key == 'AF-Increment':
                enabled = int(value)
                try:
                    db_enabled = LocalSettings.objects.get(key='AF-Increment')
                except:
                    LocalSettings(key='AF-Increment', value='5').save()
                    db_enabled = LocalSettings.objects.get(key='AF-Increment')
                db_enabled.value = enabled
                db_enabled.save()
                messages.success(request, 'Updated autofees fee increment setting to: ' + str(enabled))
            elif key == 'AF-Multiplier':
                enabled = int(value)
                try:
                    db_enabled = LocalSettings.objects.get(key='AF-Multiplier')
                except:
                    LocalSettings(key='AF-Multiplier', value='5').save()
                    db_enabled = LocalSettings.objects.get(key='AF-Multiplier')
                db_enabled.value = enabled
                db_enabled.save()
                messages.success(request, 'Updated autofees fee multiplier setting to: ' + str(enabled))
            elif key == 'AF-FailedHTLCs':
                enabled = int(value)
                try:
                    db_enabled = LocalSettings.objects.get(key='AF-FailedHTLCs')
                except:
                    LocalSettings(key='AF-FailedHTLCs', value='25').save()
                    db_enabled = LocalSettings.objects.get(key='AF-FailedHTLCs')
                db_enabled.value = enabled
                db_enabled.save()
                messages.success(request, 'Updated autofees daily failed HTLC trigger limit setting to: ' + str(enabled))
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

class ClosuresViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Closures.objects.all()
    serializer_class = ClosuresSerializer

class ResolutionsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Resolutions.objects.all()
    serializer_class = ResolutionsSerializer

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

@api_view(['GET'])
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

@api_view(['GET'])
def get_info(request):
    try:
        stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        response = stub.GetInfo(ln.GetInfoRequest())
        target = {'identity_pubkey':response.identity_pubkey, 'alias':response.alias, 'num_active_channels':response.num_active_channels, 'num_peers':response.num_peers, 'block_height':response.block_height, 'block_hash':response.block_hash,'synced_to_chain':response.synced_to_chain,'testnet':response.testnet,'uris':[uri for uri in response.uris],'best_header_timestamp':response.best_header_timestamp,'version':response.version,'num_inactive_channels':response.num_inactive_channels,'chains':[{'chain':response.chains[i].chain,'network':response.chains[i].network} for i in range(0,len(response.chains))],'color':response.color,'synced_to_graph':response.synced_to_graph}
        return Response({'message': 'success', 'data':target})
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_error_index = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_error_index]
        return Response({'error': 'Failed to call getinfo! Error: ' + error_msg})

@api_view(['GET'])
def api_balances(request):
    try:
        stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        response = stub.WalletBalance(ln.WalletBalanceRequest())
        target = {'total_balance':response.confirmed_balance, 'confirmed_balance':response.confirmed_balance}
        return Response({'message': 'success', 'data':target})
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_error_index = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_error_index]
        return Response({'error': 'Failed to get wallet balances! Error: ' + error_msg})

@api_view(['GET'])
def pending_channels(request):
    try:
        stub = lnrpc.LightningStub(lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER))
        response = stub.PendingChannels(ln.PendingChannelsRequest())
        if response.pending_open_channels or response.pending_closing_channels or response.pending_force_closing_channels or response.waiting_close_channels or response.total_limbo_balance:
            target = {}
            if response.pending_open_channels:
                target_resp = response.pending_open_channels
                peers = Peers.objects.all()
                pending_open_channels = {'pending_open':[{'alias':peers.filter(pubkey=target_resp[i].channel.remote_node_pub)[0].alias if peers.filter(pubkey=target_resp[i].channel.remote_node_pub).exists() else None,'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'commit_fee':target_resp[i].commit_fee,'commit_weight':target_resp[i].commit_weight,'fee_per_kw':target_resp[i].fee_per_kw} for i in range(0,len(target_resp))]}
                target.update(pending_open_channels)
            if response.pending_closing_channels:
                target_resp = response.pending_closing_channels
                channels = Channels.objects.all()
                pending_closing_channels = {'pending_closing':[{'chan_id':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].chan_id if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'alias':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].alias if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'limbo_balance':target_resp[i].limbo_balance} for i in range(0,len(target_resp))]}
                target.update(pending_closing_channels)
            if response.pending_force_closing_channels:
                target_resp = response.pending_force_closing_channels
                channels = Channels.objects.all()
                pending_force_closing_channels = {'pending_force_closing':[{'chan_id':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].chan_id if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'alias':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].alias if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'closing_txid':target_resp[i].closing_txid,'limbo_balance':target_resp[i].limbo_balance,'maturity_height':target_resp[i].maturity_height,'blocks_til_maturity':target_resp[i].blocks_til_maturity,'maturity_datetime':(datetime.now()+timedelta(minutes=(10*target_resp[i].blocks_til_maturity)))} for i in range(0,len(target_resp))]}
                target.update(pending_force_closing_channels)
            if response.waiting_close_channels:
                target_resp = response.waiting_close_channels
                channels = Channels.objects.all()
                waiting_close_channels = {'waiting_close':[{'chan_id':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].chan_id if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'alias':channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1])[0].alias if channels.filter(funding_txid=target_resp[i].channel.channel_point.split(':')[0], output_index=target_resp[i].channel.channel_point.split(':')[1]).exists() else None,'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'limbo_balance':target_resp[i].limbo_balance} for i in range(0,len(target_resp))]}
                target.update(waiting_close_channels)
            if response.total_limbo_balance:
                total_limbo_balance = {'total_limbo_balance':response.total_limbo_balance}
                target.update(total_limbo_balance)
            return Response({'message': 'success', 'data':target})
        else:
            return Response({'message': 'success', 'data':None})
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_error_index = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_error_index]
        return Response({'error': 'Failed to get pending channels! Error: ' + error_msg})
