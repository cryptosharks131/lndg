from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Sum, IntegerField, Count, Max, F, Q, Case, When, Value, FloatField, ExpressionWrapper, DateTimeField, DurationField
from django.db.models.functions import Round, TruncDay, Coalesce
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django_filters import FilterSet, CharFilter, DateTimeFilter, NumberFilter
from datetime import datetime, timedelta
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .forms import *
from .serializers import *
from .models import Payments, PaymentHops, Invoices, Forwards, Channels, Rebalancer, LocalSettings, Peers, Onchain, Closures, Resolutions, PendingHTLCs, FailedHTLCs, Autopilot, Autofees, InboundFeeLog, PendingChannels, AvoidNodes, PeerEvents, HistFailedHTLC, TradeSales
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps import wtclient_pb2 as wtrpc
from gui.lnd_deps import wtclient_pb2_grpc as wtstub
from gui.lnd_deps import walletkit_pb2 as walletrpc
from gui.lnd_deps import walletkit_pb2_grpc as walletstub
from gui.lnd_deps.lnd_connect import lnd_connect
from lndg import settings
from os import path
from pandas import DataFrame, merge
from requests import get
from secrets import token_bytes
from trade import create_trade_details
import af

def graph_links():
    if LocalSettings.objects.filter(key='GUI-GraphLinks').exists():
        graph_links = str(LocalSettings.objects.filter(key='GUI-GraphLinks')[0].value)
    else:
        LocalSettings(key='GUI-GraphLinks', value='https://mempool.space/lightning').save()
        graph_links = 'https://mempool.space/lightning'
    return graph_links

def network_links():
    if LocalSettings.objects.filter(key='GUI-NetLinks').exists():
        network_links = str(LocalSettings.objects.filter(key='GUI-NetLinks')[0].value)
    else:
        LocalSettings(key='GUI-NetLinks', value='https://mempool.space').save()
        network_links = 'https://mempool.space'
    return network_links

def get_tx_fees(txid):
    base_url = network_links() + ('/testnet' if settings.LND_NETWORK == 'testnet' else '') + '/api/tx/'
    request_data = get(base_url + txid).json()
    fee = request_data['fee']
    return fee

def pending_channel_details(channel_point):
    funding_txid, output_index = channel_point.split(':')
    if Channels.objects.filter(funding_txid=funding_txid, output_index=output_index).exists():
        channel = Channels.objects.filter(funding_txid=funding_txid, output_index=output_index)[0]
        return {'short_chan_id':channel.short_chan_id,'chan_id':channel.chan_id,'alias':channel.alias}
    else:
        return {'short_chan_id':None,'chan_id':None,'alias':None}

class is_login_required(object):
    def __init__(self, dec, condition):
        self.decorator = dec
        self.condition = condition

    def __call__(self, func):
        if not self.condition:
            # No login required
            return func
        return self.decorator(func)

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def home(request):
    if request.method != 'GET':
        return redirect('home')
    try:
        stub = lnrpc.LightningStub(lnd_connect())
        node_info = stub.GetInfo(ln.GetInfoRequest())
    except Exception as e:
        try:
            error = str(e.code())
        except:
            error = str(e)
        return render(request, 'error.html', {'error': error})
    return render(request, 'home.html', {
        'node_info': {'color': node_info.color, 'alias': node_info.alias, 'version': node_info.version, 'identity_pubkey': node_info.identity_pubkey, 'uris': node_info.uris},
        'local_settings': get_local_settings('AR-'),
        'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
        'graph_links': graph_links(),
        'network_links': network_links(),
    })

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
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
            forwards_df_in_30d_sum = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
            forwards_df_out_30d_sum = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
            forwards_df_in_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
            forwards_df_out_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
            forwards_df_in_30d_count = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_in', as_index=True).count()
            forwards_df_out_30d_count = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_out', as_index=True).count()
            forwards_df_in_7d_count = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_in', as_index=True).count()
            forwards_df_out_7d_count = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_out', as_index=True).count()
            payments_df_30d = DataFrame.from_records(payments.values())
            payments_df_7d = DataFrame.from_records(payments.filter(creation_date__gte=filter_7day).values())
            payments_df_30d_sum = DataFrame() if payments_df_30d.empty else payments_df_30d.groupby('chan_out', as_index=True).sum(numeric_only=True)
            payments_df_7d_sum = DataFrame() if payments_df_7d.empty else payments_df_7d.groupby('chan_out', as_index=True).sum(numeric_only=True)
            payments_df_30d_count = DataFrame() if payments_df_30d.empty else payments_df_30d.groupby('chan_out', as_index=True).count()
            payments_df_7d_count = DataFrame() if payments_df_7d.empty else payments_df_7d.groupby('chan_out', as_index=True).count()
            invoices_df_30d = DataFrame.from_records(invoices.values())
            invoices_df_7d = DataFrame.from_records(invoices.filter(settle_date__gte=filter_7day).values())
            invoices_df_30d_sum = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True).sum(numeric_only=True)
            invoices_df_7d_sum = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).sum(numeric_only=True)
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
            'channels': [] if channels_df.empty else channels_df.sort_values(by=['cv_30day'], ascending=False).to_dict(orient='records'),
            'apy_7day': apy_7day,
            'apy_30day': apy_30day,
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
        }
        return render(request, 'channels.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def fees(request):
    if request.method == 'GET':
        channels = Channels.objects.filter(is_open=True, private=False)
        results_df = af.main(channels)
        context = {
            'channels': [] if results_df.empty else results_df.sort_values(by=['out_percent']).to_dict(orient='records'),
            'local_settings': get_local_settings('AF-'),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
        }
        return render(request, 'fee_rates.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def advanced(request):
    if request.method == 'GET':
        channels = Channels.objects.filter(is_open=True).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*1000)/Sum('capacity'), inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*1000)/Sum('capacity')).order_by('-is_active', 'outbound_percent')
        channels_df = DataFrame.from_records(channels.values())
        if channels_df.shape[0] > 0:
            channels_df['out_percent'] = channels_df.apply(lambda row: int(round(row['outbound_percent']/10, 0)), axis=1)
            channels_df['in_percent'] = channels_df.apply(lambda row: int(round(row['inbound_percent']/10, 0)), axis=1)
            channels_df['local_balance'] = channels_df.apply(lambda row: row.local_balance + row.pending_outbound, axis=1)
            channels_df['remote_balance'] = channels_df.apply(lambda row: row.remote_balance + row.pending_inbound, axis=1)
            channels_df['fee_ratio'] = channels_df.apply(lambda row: 100 if row['local_fee_rate'] == 0 else int(round(((row['remote_fee_rate']/row['local_fee_rate'])*1000)/10, 0)), axis=1)
            channels_df['local_min_htlc'] = channels_df['local_min_htlc_msat']/1000
            channels_df['local_max_htlc'] = channels_df['local_max_htlc_msat']/1000
        context = {
            'channels': channels_df.to_dict(orient='records'),
            'local_settings': get_local_settings('AF-', 'AR-', 'GUI-', 'LND-'),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
        }
        return render(request, 'advanced.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def logs(request):
    if request.method == 'GET':
        try:
            count = request.GET.get('tail', 20)
            logfile = '/var/log/lndg-controller.log'
            file_size = path.getsize(logfile)-2
            if file_size == 0:
                logs = ['Logs are empty....']
            else:
                target_size = 128*int(count)
                read_size = min(target_size, file_size)
                with open(logfile, "rb") as reader:
                    reader.seek(-read_size, 2)
                    logs = [line.decode('utf-8') for line in reader.readlines()]
            return render(request, 'logs.html', {'logs': logs})
        except Exception as e:
            return render(request, 'error.html', {'error': str(e)})
    return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def route(request):
    if request.method == 'GET':
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            block_height = stub.GetInfo(ln.GetInfoRequest()).block_height
            payment_hash = request.GET.urlencode()[1:]
            route = PaymentHops.objects.filter(payment_hash=payment_hash).annotate(ppm=Round((Sum('fee')/Sum('amt'))*1000000, output_field=IntegerField())) if PaymentHops.objects.filter(payment_hash=payment_hash).exists() else None
            total_cost = round(route.aggregate(Sum('fee'))['fee__sum'],3) if route is not None else 0
            total_ppm = int(total_cost*1000000/route.filter(step=1).aggregate(Sum('amt'))['amt__sum']) if route is not None else 0
            context = {
                'payment_hash': payment_hash,
                'total_cost': total_cost,
                'total_ppm': total_ppm,
                'route': route,
                'invoices': Invoices.objects.filter(r_hash=payment_hash),
                'incoming_htlcs': PendingHTLCs.objects.filter(incoming=True, hash_lock=payment_hash).annotate(blocks_til_expiration=Sum('expiration_height')-block_height, hours_til_expiration=((Sum('expiration_height')-block_height)*10)/60).order_by('hash_lock'),
                'outgoing_htlcs': PendingHTLCs.objects.filter(incoming=False, hash_lock=payment_hash).annotate(blocks_til_expiration=Sum('expiration_height')-block_height, hours_til_expiration=((Sum('expiration_height')-block_height)*10)/60).order_by('hash_lock')
            }
            return render(request, 'route.html', context)
        except Exception as e:
            error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def routes(request):
    if request.method == 'GET':
        try:
            pubkey = request.GET.urlencode()[1:]
            context = {
                'payment_hash': pubkey,
                'route': PaymentHops.objects.filter(payment_hash__in=PaymentHops.objects.filter(node_pubkey=pubkey).order_by('-id').values_list('payment_hash')[:69]).annotate(ppm=Round((Sum('fee')/Sum('amt'))*1000000, output_field=IntegerField()))
            }
            return render(request, 'route.html', context)
        except Exception as e:
            error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def peers(request):
    if request.method == 'GET':
        peers = Peers.objects.filter(connected=True)
        context = {
            'peers': peers,
            'num_peers': len(peers),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links()
        }
        return render(request, 'peers.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def balances(request):
    if request.method == 'GET':
        stub = walletstub.WalletKitStub(lnd_connect())
        pending_sweeps = stub.PendingSweeps(walletrpc.PendingSweepsRequest()).pending_sweeps
        sweeps = []
        for pending_sweep in pending_sweeps:
            sweep = {}
            sweep['txid_str'] = pending_sweep.outpoint.txid_bytes[::-1].hex()
            sweep['txid_index'] = pending_sweep.outpoint.output_index
            sweep['amount_sat'] = pending_sweep.amount_sat
            sweep['witness_type'] = pending_sweep.witness_type
            sweep['requested_sat_per_vbyte'] = pending_sweep.requested_sat_per_vbyte
            sweep['sat_per_vbyte'] = pending_sweep.sat_per_vbyte
            sweep['requested_conf_target'] = pending_sweep.requested_conf_target
            sweep['broadcast_attempts'] = pending_sweep.broadcast_attempts
            sweep['next_broadcast_height'] = pending_sweep.next_broadcast_height
            sweep['force'] = pending_sweep.force
            sweeps.append(sweep)
        context = {
            'utxos': stub.ListUnspent(walletrpc.ListUnspentRequest(min_confs=0, max_confs=9999999)).utxos,
            'transactions': list(Onchain.objects.filter(block_height=0)) + list(Onchain.objects.exclude(block_height=0).order_by('-block_height')),
            'pending_sweeps': sweeps,
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'network_links': network_links()
        }
        return render(request, 'balances.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def closures(request):
    if request.method == 'GET':
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            pending_channels = stub.PendingChannels(ln.PendingChannelsRequest())
            pending_closed = None
            pending_force_closed = None
            waiting_for_close = None
            if pending_channels.pending_closing_channels:
                target_resp = pending_channels.pending_closing_channels
                pending_closed = []
                for i in range(0,len(target_resp)):
                    pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
                    'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type, 'local_commit_fee_sat': target_resp[i].commitments.local_commit_fee_sat, 'limbo_balance':target_resp[i].limbo_balance, 'closing_txid':target_resp[i].closing_txid}
                    pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
                    pending_closed.append(pending_item)
            if pending_channels.pending_force_closing_channels:
                target_resp = pending_channels.pending_force_closing_channels
                pending_force_closed = []
                for i in range(0,len(target_resp)):
                    pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'initiator':target_resp[i].channel.initiator,
                    'commitment_type':target_resp[i].channel.commitment_type,'closing_txid':target_resp[i].closing_txid,'limbo_balance':target_resp[i].limbo_balance,'maturity_height':target_resp[i].maturity_height,'blocks_til_maturity':target_resp[i].blocks_til_maturity if target_resp[i].blocks_til_maturity > 0 else find_next_block_maturity(target_resp[i]),
                    'maturity_datetime':(datetime.now()+timedelta(minutes=(10*target_resp[i].blocks_til_maturity if target_resp[i].blocks_til_maturity > 0 else 10*find_next_block_maturity(target_resp[i]) )))}
                    pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
                    pending_force_closed.append(pending_item)
            if pending_channels.waiting_close_channels:
                target_resp = pending_channels.waiting_close_channels
                waiting_for_close = []
                for i in range(0,len(target_resp)):
                    pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
                    'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type, 'local_commit_fee_sat': target_resp[i].commitments.local_commit_fee_sat, 'limbo_balance':target_resp[i].limbo_balance, 'closing_txid':target_resp[i].closing_txid}
                    pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
                    waiting_for_close.append(pending_item)
            closures_df = DataFrame.from_records(Closures.objects.all().values())
            if closures_df.empty:
                merged = DataFrame()
            else:
                channels_df = DataFrame.from_records(Channels.objects.all().values('chan_id', 'short_chan_id', 'alias'))
                if channels_df.empty:
                    merged = closures_df
                    merged['alias'] = ''
                    merged['short_chan_id'] = merged.apply(lambda row: str(int(row.chan_id) >> 40) + 'x' + str(int(int(row.chan_id) >> 16) & 0xFFFFFF) + 'x' + str(int(row.chan_id) & 0xFFFF), axis=1)
                else:
                    merged = merge(closures_df, channels_df, on='chan_id', how='left')
                    merged['alias'] = merged['alias'].fillna('')
                    merged['short_chan_id'] = merged['short_chan_id'].fillna('')
                    merged['short_chan_id'] = merged.apply(lambda row: str(int(row.chan_id) >> 40) + 'x' + str(int(int(row.chan_id) >> 16) & 0xFFFFFF) + 'x' + str(int(row.chan_id) & 0xFFFF) if row.short_chan_id == '' else row.short_chan_id, axis=1)
            context = {
                'pending_closed': pending_closed,
                'pending_force_closed': pending_force_closed,
                'waiting_for_close': waiting_for_close,
                'closures': [] if merged.empty else merged.sort_values(by=['close_height'], ascending=False).to_dict(orient='records'),
                'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
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

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def towers(request):
    if request.method == 'GET':
        try:
            stub = wtstub.WatchtowerClientStub(lnd_connect())
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

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def add_tower_form(request):
    if request.method == 'POST':
        form = AddTowerForm(request.POST)
        if form.is_valid():
            try:
                stub = wtstub.WatchtowerClientStub(lnd_connect())
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

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def delete_tower_form(request):
    if request.method == 'POST':
        form = DeleteTowerForm(request.POST)
        if form.is_valid():
            try:
                stub = wtstub.WatchtowerClientStub(lnd_connect())
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

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def remove_tower_form(request):
    if request.method == 'POST':
        form = RemoveTowerForm(request.POST)
        if form.is_valid():
            try:
                stub = wtstub.WatchtowerClientStub(lnd_connect())
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

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def resolutions(request):
    if request.method == 'GET':
        chan_id = request.GET.urlencode()[1:]
        context = {
            'chan_id': chan_id,
            'resolutions': Resolutions.objects.filter(chan_id=chan_id),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'network_links': network_links()
        }
        return render(request, 'resolutions.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def income(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect())
        filter_90day = datetime.now() - timedelta(days=90)
        filter_30day = datetime.now() - timedelta(days=30)
        filter_7day = datetime.now() - timedelta(days=7)
        filter_1day = datetime.now() - timedelta(days=1)
        node_info = stub.GetInfo(ln.GetInfoRequest())
        invoices = Invoices.objects.filter(state=1, is_revenue=True)
        invoices_90day = invoices.filter(settle_date__gte=filter_90day)
        invoices_30day = invoices.filter(settle_date__gte=filter_30day)
        invoices_7day = invoices.filter(settle_date__gte=filter_7day)
        invoices_1day = invoices.filter(settle_date__gte=filter_1day)
        payments = Payments.objects.filter(status=2)
        payments_90day = payments.filter(creation_date__gte=filter_90day)
        payments_30day = payments.filter(creation_date__gte=filter_30day)
        payments_7day = payments.filter(creation_date__gte=filter_7day)
        payments_1day = payments.filter(creation_date__gte=filter_1day)
        onchain_txs = Onchain.objects.all()
        onchain_txs_90day = onchain_txs.filter(time_stamp__gte=filter_90day)
        onchain_txs_30day = onchain_txs.filter(time_stamp__gte=filter_30day)
        onchain_txs_7day = onchain_txs.filter(time_stamp__gte=filter_7day)
        onchain_txs_1day = onchain_txs.filter(time_stamp__gte=filter_1day)
        closures = Closures.objects.all()
        closures_90day = Closures.objects.filter(close_height__gte=(node_info.block_height - 12960))
        closures_30day = Closures.objects.filter(close_height__gte=(node_info.block_height - 4320))
        closures_7day = Closures.objects.filter(close_height__gte=(node_info.block_height - 1008))
        closures_1day = Closures.objects.filter(close_height__gte=(node_info.block_height - 144))
        forwards = Forwards.objects.all()
        forwards_90day = forwards.filter(forward_date__gte=filter_90day)
        forwards_30day = forwards.filter(forward_date__gte=filter_30day)
        forwards_7day = forwards.filter(forward_date__gte=filter_7day)
        forwards_1day = forwards.filter(forward_date__gte=filter_1day)
        forward_count = forwards.count()
        forward_count_90day = forwards_90day.count()
        forward_count_30day = forwards_30day.count()
        forward_count_7day = forwards_7day.count()
        forward_count_1day = forwards_1day.count()
        forward_amount = 0 if forward_count == 0 else int(forwards.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        forward_amount_90day = 0 if forward_count_90day == 0 else int(forwards_90day.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        forward_amount_30day = 0 if forward_count_30day == 0 else int(forwards_30day.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        forward_amount_7day = 0 if forward_count_7day == 0 else int(forwards_7day.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        forward_amount_1day = 0 if forward_count_1day == 0 else int(forwards_1day.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        total_revenue = 0 if forward_count == 0 else int(forwards.aggregate(Sum('fee'))['fee__sum'])
        total_revenue_90day = 0 if forward_count_90day == 0 else int(forwards_90day.aggregate(Sum('fee'))['fee__sum'])
        total_revenue_30day = 0 if forward_count_30day == 0 else int(forwards_30day.aggregate(Sum('fee'))['fee__sum'])
        total_revenue_7day = 0 if forward_count_7day == 0 else int(forwards_7day.aggregate(Sum('fee'))['fee__sum'])
        total_revenue_1day = 0 if forward_count_1day == 0 else int(forwards_1day.aggregate(Sum('fee'))['fee__sum'])
        total_received = 0 if invoices.count() == 0 else int(invoices.aggregate(Sum('amt_paid'))['amt_paid__sum'])
        total_received_90day = 0 if invoices_90day.count() == 0 else int(invoices_90day.aggregate(Sum('amt_paid'))['amt_paid__sum'])
        total_received_30day = 0 if invoices_30day.count() == 0 else int(invoices_30day.aggregate(Sum('amt_paid'))['amt_paid__sum'])
        total_received_7day = 0 if invoices_7day.count() == 0 else int(invoices_7day.aggregate(Sum('amt_paid'))['amt_paid__sum'])
        total_received_1day = 0 if invoices_1day.count() == 0 else int(invoices_1day.aggregate(Sum('amt_paid'))['amt_paid__sum'])
        total_revenue += total_received
        total_revenue_90day += total_received_90day
        total_revenue_30day += total_received_30day
        total_revenue_7day += total_received_7day
        total_revenue_1day += total_received_1day
        total_revenue_ppm = 0 if forward_amount == 0 else int(total_revenue/(forward_amount/1000000))
        total_revenue_ppm_90day = 0 if forward_amount_90day == 0 else int(total_revenue_90day/(forward_amount_90day/1000000))
        total_revenue_ppm_30day = 0 if forward_amount_30day == 0 else int(total_revenue_30day/(forward_amount_30day/1000000))
        total_revenue_ppm_7day = 0 if forward_amount_7day == 0 else int(total_revenue_7day/(forward_amount_7day/1000000))
        total_revenue_ppm_1day = 0 if forward_amount_1day == 0 else int(total_revenue_1day/(forward_amount_1day/1000000))
        total_sent = 0 if payments.count() == 0 else int(payments.aggregate(Sum('value'))['value__sum'])
        total_sent_90day = 0 if payments_90day.count() == 0 else int(payments_90day.aggregate(Sum('value'))['value__sum'])
        total_sent_30day = 0 if payments_30day.count() == 0 else int(payments_30day.aggregate(Sum('value'))['value__sum'])
        total_sent_7day = 0 if payments_7day.count() == 0 else int(payments_7day.aggregate(Sum('value'))['value__sum'])
        total_sent_1day = 0 if payments_1day.count() == 0 else int(payments_1day.aggregate(Sum('value'))['value__sum'])
        total_fees = 0 if payments.count() == 0 else int(payments.aggregate(Sum('fee'))['fee__sum'])
        total_fees_90day = 0 if payments_90day.count() == 0 else int(payments_90day.aggregate(Sum('fee'))['fee__sum'])
        total_fees_30day = 0 if payments_30day.count() == 0 else int(payments_30day.aggregate(Sum('fee'))['fee__sum'])
        total_fees_7day = 0 if payments_7day.count() == 0 else int(payments_7day.aggregate(Sum('fee'))['fee__sum'])
        total_fees_1day = 0 if payments_1day.count() == 0 else int(payments_1day.aggregate(Sum('fee'))['fee__sum'])
        total_fees_ppm = 0 if total_sent == 0 else int(total_fees/(total_sent/1000000))
        total_fees_ppm_90day = 0 if total_sent_90day == 0 else int(total_fees_90day/(total_sent_90day/1000000))
        total_fees_ppm_30day = 0 if total_sent_30day == 0 else int(total_fees_30day/(total_sent_30day/1000000))
        total_fees_ppm_7day = 0 if total_sent_7day == 0 else int(total_fees_7day/(total_sent_7day/1000000))
        total_fees_ppm_1day = 0 if total_sent_1day == 0 else int(total_fees_1day/(total_sent_1day/1000000))
        onchain_costs = 0 if onchain_txs.count() == 0 else onchain_txs.aggregate(Sum('fee'))['fee__sum']
        onchain_costs_90day = 0 if onchain_txs_90day.count() == 0 else onchain_txs_90day.aggregate(Sum('fee'))['fee__sum']
        onchain_costs_30day = 0 if onchain_txs_30day.count() == 0 else onchain_txs_30day.aggregate(Sum('fee'))['fee__sum']
        onchain_costs_7day = 0 if onchain_txs_7day.count() == 0 else onchain_txs_7day.aggregate(Sum('fee'))['fee__sum']
        onchain_costs_1day = 0 if onchain_txs_1day.count() == 0 else onchain_txs_1day.aggregate(Sum('fee'))['fee__sum']
        close_fees = closures.aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures.exists() else 0
        close_fees_90day = closures_90day.aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures_90day.exists() else 0
        close_fees_30day = closures_30day.aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures_30day.exists() else 0
        close_fees_7day = closures_7day.aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures_7day.exists() else 0
        close_fees_1day = closures_1day.aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures_1day.exists() else 0
        onchain_costs += close_fees
        onchain_costs_90day += close_fees_90day
        onchain_costs_30day += close_fees_30day
        onchain_costs_7day += close_fees_7day
        onchain_costs_1day += close_fees_1day
        profits = int(total_revenue-total_fees-onchain_costs)
        profits_90day = int(total_revenue_90day-total_fees_90day-onchain_costs_90day)
        profits_30day = int(total_revenue_30day-total_fees_30day-onchain_costs_30day)
        profits_7day = int(total_revenue_7day-total_fees_7day-onchain_costs_7day)
        profits_1day = int(total_revenue_1day-total_fees_1day-onchain_costs_1day)
        context = {
            'node_info': node_info,
            'forward_count': forward_count,
            'forward_count_90day': forward_count_90day,
            'forward_count_30day': forward_count_30day,
            'forward_count_7day': forward_count_7day,
            'forward_count_1day': forward_count_1day,
            'forward_amount': forward_amount,
            'forward_amount_90day': forward_amount_90day,
            'forward_amount_30day': forward_amount_30day,
            'forward_amount_7day': forward_amount_7day,
            'forward_amount_1day': forward_amount_1day,
            'total_revenue': total_revenue,
            'total_revenue_90day': total_revenue_90day,
            'total_revenue_30day': total_revenue_30day,
            'total_revenue_7day': total_revenue_7day,
            'total_revenue_1day': total_revenue_1day,
            'total_fees': total_fees,
            'total_fees_90day': total_fees_90day,
            'total_fees_30day': total_fees_30day,
            'total_fees_7day': total_fees_7day,
            'total_fees_1day': total_fees_1day,
            'total_fees_ppm': total_fees_ppm,
            'total_fees_ppm_90day': total_fees_ppm_90day,
            'total_fees_ppm_30day': total_fees_ppm_30day,
            'total_fees_ppm_7day': total_fees_ppm_7day,
            'total_fees_ppm_1day': total_fees_ppm_1day,
            'onchain_costs': onchain_costs,
            'onchain_costs_90day': onchain_costs_90day,
            'onchain_costs_30day': onchain_costs_30day,
            'onchain_costs_7day': onchain_costs_7day,
            'onchain_costs_1day': onchain_costs_1day,
            'total_revenue_ppm': total_revenue_ppm,
            'total_revenue_ppm_90day': total_revenue_ppm_90day,
            'total_revenue_ppm_30day': total_revenue_ppm_30day,
            'total_revenue_ppm_7day': total_revenue_ppm_7day,
            'total_revenue_ppm_1day': total_revenue_ppm_1day,
            'profits': profits,
            'profits_90day': profits_90day,
            'profits_30day': profits_30day,
            'profits_7day': profits_7day,
            'profits_1day': profits_1day,
            'profits_ppm': 0 if forward_amount == 0  else int(profits/(forward_amount/1000000)),
            'profits_ppm_90day': 0 if forward_amount_90day == 0  else int(profits_90day/(forward_amount_90day/1000000)),
            'profits_ppm_30day': 0 if forward_amount_30day == 0  else int(profits_30day/(forward_amount_30day/1000000)),
            'profits_ppm_7day': 0 if forward_amount_7day == 0  else int(profits_7day/(forward_amount_7day/1000000)),
            'profits_ppm_1day': 0 if forward_amount_1day == 0  else int(profits_1day/(forward_amount_1day/1000000)),
            'percent_cost': 0 if total_revenue == 0 else int(((total_fees+onchain_costs)/total_revenue)*100),
            'percent_cost_90day': 0 if total_revenue_90day == 0 else int(((total_fees_90day+onchain_costs_90day)/total_revenue_90day)*100),
            'percent_cost_30day': 0 if total_revenue_30day == 0 else int(((total_fees_30day+onchain_costs_30day)/total_revenue_30day)*100),
            'percent_cost_7day': 0 if total_revenue_7day == 0 else int(((total_fees_7day+onchain_costs_7day)/total_revenue_7day)*100),
            'percent_cost_1day': 0 if total_revenue_1day == 0 else int(((total_fees_1day+onchain_costs_1day)/total_revenue_1day)*100),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links()
        }
        return render(request, 'income.html', context)
    else:
        return redirect('home')

@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def chart(request):
    payments = Payments.objects.filter(status=2).annotate(dt=TruncDay('creation_date')).values('dt').annotate(cost=Sum('fee', output_field=FloatField()), revenue=Value(0, output_field=FloatField()), onchain=Value(0))
    invoices = Invoices.objects.filter(state=1, is_revenue=True).annotate(dt=TruncDay('settle_date')).values('dt').annotate(cost=Value(0, output_field=FloatField()), revenue=Sum('amt_paid', output_field=FloatField()), onchain=Value(0))
    forwards = Forwards.objects.annotate(dt=TruncDay('forward_date')).values('dt').annotate(cost=Value(0, output_field=FloatField()), revenue=Sum('fee', output_field=FloatField()), onchain=Value(0))
    onchain = Onchain.objects.annotate(dt=TruncDay('time_stamp')).values('dt').annotate(cost=Value(0, output_field=FloatField()), revenue=Value(0, output_field=FloatField()), onchain=Sum('fee'))

    # Estimate blockchain timing parameters
    first_record = Onchain.objects.order_by('time_stamp').first()
    first_date = first_record.time_stamp
    first_block = first_record.block_height
    last_record = Onchain.objects.order_by('time_stamp').last()
    last_date = last_record.time_stamp
    last_block = last_record.block_height
    time_interval_per_block = timedelta(minutes=10)
    if last_block > first_block:
        time_interval_per_block =  (last_date - first_date) / (last_block - first_block)
    offset = first_date - first_block * time_interval_per_block
    # Convert close_height to datetime
    datetime_from_blocks = TruncDay(
        ExpressionWrapper(
            offset
            + ExpressionWrapper(
                F('close_height') * time_interval_per_block,
                output_field=DurationField(),
            ),
            output_field=DateTimeField()
        )
    )
    closures = Closures.objects.annotate(dt=datetime_from_blocks).values('dt').annotate(cost=Value(0, output_field=FloatField()), revenue=Value(0, output_field=FloatField()), onchain=Sum('closing_costs'))
    balance = DataFrame.from_records(payments.union(invoices, forwards, onchain, closures).values('dt', 'cost', 'revenue', 'onchain'))
    results = balance.groupby('dt').sum().reset_index().sort_values('dt')
    return Response(results.to_dict(orient='records'))

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def channel(request):
    if request.method == 'GET':
        chan_id = request.GET.urlencode()[1:]
        if Channels.objects.filter(chan_id=chan_id).exists():
            filter_1day = datetime.now() - timedelta(days=1)
            filter_7day = datetime.now() - timedelta(days=7)
            filter_30day = datetime.now() - timedelta(days=30)
            forwards_df = DataFrame.from_records(Forwards.objects.filter(Q(chan_id_in=chan_id) | Q(chan_id_out=chan_id)).values())
            payments_df = DataFrame.from_records(Payments.objects.filter(status=2).filter(chan_out=chan_id).filter(rebal_chan__isnull=False).annotate(ppm=Round((Sum('fee')*1000000)/Sum('value'), output_field=IntegerField())).values())
            rebal_payments = Payments.objects.filter(status=2).filter(rebal_chan=chan_id)
            invoices_df = DataFrame.from_records(Invoices.objects.filter(state=1).filter(chan_in=chan_id).filter(r_hash__in=rebal_payments).values())
            channels_df = DataFrame.from_records(Channels.objects.filter(is_open=True).values())
            if channels_df.empty:
                node_outbound = 0
                node_capacity = 0
            else:
                node_outbound = channels_df['local_balance'].sum()
                node_capacity = channels_df['capacity'].sum()
            channel = Channels.objects.filter(chan_id=chan_id)
            channels_df = DataFrame.from_records(channel.values())
            rebalancer_df = DataFrame.from_records(Rebalancer.objects.filter(last_hop_pubkey=channels_df['remote_pubkey'][0]).annotate(ppm=Round((Sum('fee_limit')*1000000)/Sum('value'), output_field=IntegerField())).order_by('-id').values())
            failed_htlc_df = DataFrame.from_records(FailedHTLCs.objects.exclude(wire_failure=99).filter(Q(chan_id_in=chan_id) | Q(chan_id_out=chan_id)).order_by('-id').values())
            peer_info_df = DataFrame.from_records(Peers.objects.filter(pubkey=channels_df['remote_pubkey'][0]).values())
            channels_df['local_balance'] = channels_df['local_balance'] + channels_df['pending_outbound']
            channels_df['remote_balance'] = channels_df['remote_balance'] + channels_df['pending_inbound']
            channels_df['in_percent'] = ((channels_df['remote_balance']/channels_df['capacity'])*100).round(0).astype(int)
            channels_df['out_percent'] = ((channels_df['local_balance']/channels_df['capacity'])*100).round(0).astype(int)
            channels_df['open_block'] = channels_df['chan_id'].apply(lambda row: int(row)>>40).astype(int)
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
                channels_df['success_rate'] = 0 if channels_df['attempts'].iloc[0] == 0 else ((channels_df['success']/channels_df['attempts'])*100).astype(int)
                rebalancer_df_30d = rebalancer_df.loc[rebalancer_df['stop'] >= filter_30day]
                if rebalancer_df_30d.shape[0]> 0:
                    channels_df['attempts_30day'] = len(rebalancer_df_30d[(rebalancer_df_30d['status']>=2) & (rebalancer_df_30d['status']<400)])
                    channels_df['success_30day'] = len(rebalancer_df_30d[rebalancer_df_30d['status']==2])
                    channels_df['success_rate_30day'] = 0 if channels_df['attempts_30day'].iloc[0] == 0 else ((channels_df['success_30day']/channels_df['attempts_30day'])*100).astype(int)
                    rebalancer_df_7d = rebalancer_df_30d.loc[rebalancer_df_30d['stop'] >= filter_7day]
                    if rebalancer_df_7d.shape[0]> 0:
                        channels_df['attempts_7day'] = len(rebalancer_df_7d[(rebalancer_df_7d['status']>=2) & (rebalancer_df_7d['status']<400)])
                        channels_df['success_7day'] = len(rebalancer_df_7d[rebalancer_df_7d['status']==2])
                        channels_df['success_rate_7day'] = 0 if channels_df['attempts_7day'].iloc[0] == 0 else ((channels_df['success_7day']/channels_df['attempts_7day'])*100).astype(int)
                        rebalancer_df_1d = rebalancer_df_7d.loc[rebalancer_df_7d['stop'] >= filter_1day]
                        if rebalancer_df_1d.shape[0]> 0:
                            channels_df['attempts_1day'] = len(rebalancer_df_1d[(rebalancer_df_1d['status']>=2) & (rebalancer_df_1d['status']<400)])
                            channels_df['success_1day'] = len(rebalancer_df_1d[rebalancer_df_1d['status']==2])
                            channels_df['success_rate_1day'] = 0 if channels_df['attempts_1day'].iloc[0] == 0 else ((channels_df['success_1day']/channels_df['attempts_1day'])*100).astype(int)
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
                forwards_in_df_sum = forwards_in_df.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
                channels_df['routed_in'] = forwards_in_df_count.loc[chan_id].amt_out_msat
                channels_df['amt_routed_in'] = int(forwards_in_df_sum.loc[chan_id].amt_out_msat/1000)
                channels_df['average_in'] = 0 if channels_df['routed_in'].iloc[0] == 0 else (channels_df['amt_routed_in']/channels_df['routed_in']).astype(int)
                channels_df['revenue_assist'] = int(forwards_in_df_sum.loc[chan_id].fee) if forwards_in_df_sum.empty == False else 0
                forwards_in_df_30d = forwards_in_df.loc[forwards_in_df['forward_date'] >= filter_30day]
                if forwards_in_df_30d.shape[0] > 0:
                    forwards_in_df_30d_count = forwards_in_df_30d.groupby('chan_id_in', as_index=True).count()
                    forwards_in_df_30d_sum = forwards_in_df_30d.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
                    channels_df['routed_in_30day'] = forwards_in_df_30d_count.loc[chan_id].amt_out_msat
                    channels_df['amt_routed_in_30day'] = int(forwards_in_df_30d_sum.loc[chan_id].amt_out_msat/1000)
                    channels_df['average_in_30day'] = 0 if channels_df['routed_in_30day'].iloc[0] == 0 else (channels_df['amt_routed_in_30day']/channels_df['routed_in_30day']).astype(int)
                    channels_df['revenue_assist_30day'] = int(forwards_in_df_30d_sum.loc[chan_id].fee) if forwards_in_df_30d_sum.empty == False else 0
                    forwards_in_df_7d = forwards_in_df_30d.loc[forwards_in_df_30d['forward_date'] >= filter_7day]
                    if forwards_in_df_7d.shape[0] > 0:
                        forwards_in_df_7d_count = forwards_in_df_7d.groupby('chan_id_in', as_index=True).count()
                        forwards_in_df_7d_sum = forwards_in_df_7d.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
                        channels_df['routed_in_7day'] = forwards_in_df_7d_count.loc[chan_id].amt_out_msat
                        channels_df['amt_routed_in_7day'] = int(forwards_in_df_7d_sum.loc[chan_id].amt_out_msat/1000)
                        channels_df['average_in_7day'] = 0 if channels_df['routed_in_7day'].iloc[0] == 0 else (channels_df['amt_routed_in_7day']/channels_df['routed_in_7day']).astype(int)
                        channels_df['revenue_assist_7day'] = int(forwards_in_df_7d_sum.loc[chan_id].fee)
                        forwards_in_df_7d_sum = forwards_in_df_7d[forwards_in_df_7d['amt_out_msat']>=1000000].groupby('chan_id_in', as_index=True).sum(numeric_only=True)
                        if forwards_in_df_7d_sum.shape[0] > 0:
                            channels_df['amt_routed_in_7day_fees'] = int(forwards_in_df_7d_sum.loc[chan_id].amt_out_msat/1000)
                            channels_df['revenue_assist_7day_fees'] = int(forwards_in_df_7d_sum.loc[chan_id].fee)
                        forwards_in_df_1d = forwards_in_df_7d.loc[forwards_in_df_7d['forward_date'] >= filter_1day]
                        if forwards_in_df_1d.shape[0] > 0:
                            forwards_in_df_1d_count = forwards_in_df_1d.groupby('chan_id_in', as_index=True).count()
                            forwards_in_df_1d_sum = forwards_in_df_1d.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
                            channels_df['routed_in_1day'] = forwards_in_df_1d_count.loc[chan_id].amt_out_msat
                            channels_df['amt_routed_in_1day'] = int(forwards_in_df_1d_sum.loc[chan_id].amt_out_msat/1000)
                            channels_df['average_in_1day'] = 0 if channels_df['routed_in_1day'].iloc[0] == 0 else (channels_df['amt_routed_in_1day']/channels_df['routed_in_1day']).astype(int)
                            channels_df['revenue_assist_1day'] = int(forwards_in_df_1d_sum.loc[chan_id].fee)
            if forwards_out_df.shape[0]> 0:
                start_date = forwards_out_df['forward_date'].min()
                forwards_out_df_count = forwards_out_df.groupby('chan_id_out', as_index=True).count()
                forwards_out_df_sum = forwards_out_df.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
                channels_df['routed_out'] = forwards_out_df_count.loc[chan_id].amt_out_msat
                channels_df['amt_routed_out'] = int(forwards_out_df_sum.loc[chan_id].amt_out_msat/1000)
                channels_df['average_out'] = 0 if channels_df['routed_out'].iloc[0] == 0 else (channels_df['amt_routed_out']/channels_df['routed_out']).astype(int)
                channels_df['revenue'] = int(forwards_out_df_sum.loc[chan_id].fee) if forwards_out_df_sum.empty == False else 0
                forwards_out_df_30d = forwards_out_df.loc[forwards_out_df['forward_date'] >= filter_30day]
                if forwards_out_df_30d.shape[0] > 0:
                    forwards_out_df_30d_count = forwards_out_df_30d.groupby('chan_id_out', as_index=True).count()
                    forwards_out_df_30d_sum = forwards_out_df_30d.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
                    channels_df['routed_out_30day'] = forwards_out_df_30d_count.loc[chan_id].amt_out_msat
                    channels_df['amt_routed_out_30day'] = int(forwards_out_df_30d_sum.loc[chan_id].amt_out_msat/1000)
                    channels_df['average_out_30day'] = 0 if channels_df['routed_out_30day'].iloc[0] == 0 else (channels_df['amt_routed_out_30day']/channels_df['routed_out_30day']).astype(int)
                    channels_df['revenue_30day'] = int(forwards_out_df_30d_sum.loc[chan_id].fee) if forwards_out_df_30d_sum.empty == False else 0
                    forwards_out_df_7d = forwards_out_df_30d.loc[forwards_out_df_30d['forward_date'] >= filter_7day]
                    if forwards_out_df_7d.shape[0] > 0:
                        forwards_out_df_7d_count = forwards_out_df_7d.groupby('chan_id_out', as_index=True).count()
                        forwards_out_df_7d_sum = forwards_out_df_7d.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
                        channels_df['routed_out_7day'] = forwards_out_df_7d_count.loc[chan_id].amt_out_msat
                        channels_df['amt_routed_out_7day'] = int(forwards_out_df_7d_sum.loc[chan_id].amt_out_msat/1000)
                        channels_df['average_out_7day'] = 0 if channels_df['routed_out_7day'].iloc[0] == 0 else (channels_df['amt_routed_out_7day']/channels_df['routed_out_7day']).astype(int)
                        channels_df['revenue_7day'] = int(forwards_out_df_7d_sum.loc[chan_id].fee)
                        forwards_out_df_7d_sum = forwards_out_df_7d[forwards_out_df_7d['amt_out_msat']>=1000000].groupby('chan_id_out', as_index=True).sum(numeric_only=True)
                        if forwards_out_df_7d_sum.shape[0] > 0:
                            channels_df['amt_routed_out_7day_fees'] = int(forwards_out_df_7d_sum.loc[chan_id].amt_out_msat/1000)
                            channels_df['revenue_7day_fees'] = int(forwards_out_df_7d_sum.loc[chan_id].fee)
                        forwards_out_df_1d = forwards_out_df_7d.loc[forwards_out_df_7d['forward_date'] >= filter_1day]
                        if forwards_out_df_1d.shape[0] > 0:
                            forwards_out_df_1d_count = forwards_out_df_1d.groupby('chan_id_out', as_index=True).count()
                            forwards_out_df_1d_sum = forwards_out_df_1d.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
                            channels_df['routed_out_1day'] = forwards_out_df_1d_count.loc[chan_id].amt_out_msat
                            channels_df['amt_routed_out_1day'] = int(forwards_out_df_1d_sum.loc[chan_id].amt_out_msat/1000)
                            channels_df['average_out_1day'] = 0 if channels_df['routed_out_1day'].iloc[0] == 0 else (channels_df['amt_routed_out_1day']/channels_df['routed_out_1day']).astype(int)
                            channels_df['revenue_1day'] = int(forwards_out_df_1d_sum.loc[chan_id].fee)
            if payments_df.shape[0] > 0:
                payments_df_count = payments_df.groupby('chan_out', as_index=True).count()
                payments_df_sum = payments_df.groupby('chan_out', as_index=True).sum(numeric_only=True)
                channels_df['rebal_out'] = payments_df_count.loc[chan_id].value
                channels_df['amt_rebal_out'] = int(payments_df_sum.loc[chan_id].value)
                payments_df_30d = payments_df.loc[payments_df['creation_date'] >= filter_30day]
                if payments_df_30d.shape[0] > 0:
                    payments_df_30d_count = payments_df_30d.groupby('chan_out', as_index=True).count()
                    payments_df_30d_sum = payments_df_30d.groupby('chan_out', as_index=True).sum(numeric_only=True)
                    channels_df['rebal_out_30day'] = payments_df_30d_count.loc[chan_id].value
                    channels_df['amt_rebal_out_30day'] = int(payments_df_30d_sum.loc[chan_id].value)
                    payments_df_7d = payments_df_30d.loc[payments_df_30d['creation_date'] >= filter_7day]
                    if payments_df_7d.shape[0] > 0:
                        payments_df_7d_count = payments_df_7d.groupby('chan_out', as_index=True).count()
                        payments_df_7d_sum = payments_df_7d.groupby('chan_out', as_index=True).sum(numeric_only=True)
                        channels_df['rebal_out_7day'] = payments_df_7d_count.loc[chan_id].value
                        channels_df['amt_rebal_out_7day'] = int(payments_df_7d_sum.loc[chan_id].value)
                        payments_df_1d = payments_df_7d.loc[payments_df_7d['creation_date'] >= filter_1day]
                        if payments_df_1d.shape[0] > 0:
                            payments_df_1d_count = payments_df_1d.groupby('chan_out', as_index=True).count()
                            payments_df_1d_sum = payments_df_1d.groupby('chan_out', as_index=True).sum(numeric_only=True)
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
                invoices_df_sum = DataFrame() if invoices_df.empty else invoices_df.groupby('chan_in', as_index=True).sum(numeric_only=True)
                invoices_df_30d_sum = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True).sum(numeric_only=True)
                invoices_df_7d_sum = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).sum(numeric_only=True)
                invoices_df_1d_sum = DataFrame() if invoices_df_1d.empty else invoices_df_1d.groupby('chan_in', as_index=True).sum(numeric_only=True)
                channels_df['rebal_in'] = invoices_df_count.loc[chan_id].amt_paid if invoices_df_count.empty == False else 0
                channels_df['rebal_in_30day'] = invoices_df_30d_count.loc[chan_id].amt_paid if invoices_df_30d_count.empty == False else 0
                channels_df['rebal_in_7day'] = invoices_df_7d_count.loc[chan_id].amt_paid if invoices_df_7d_count.empty == False else 0
                channels_df['rebal_in_1day'] = invoices_df_1d_count.loc[chan_id].amt_paid if invoices_df_1d_count.empty == False else 0
                channels_df['amt_rebal_in'] = int(invoices_df_sum.loc[chan_id].amt_paid) if invoices_df_count.empty == False else 0
                channels_df['amt_rebal_in_30day'] = int(invoices_df_30d_sum.loc[chan_id].amt_paid) if invoices_df_30d_count.empty == False else 0
                channels_df['amt_rebal_in_7day'] = int(invoices_df_7d_sum.loc[chan_id].amt_paid) if invoices_df_7d_count.empty == False else 0
                channels_df['amt_rebal_in_1day'] = int(invoices_df_1d_sum.loc[chan_id].amt_paid) if invoices_df_1d_count.empty == False else 0
                rebal_payments_df = DataFrame.from_records(rebal_payments.filter(value__gte=1000).values())
                if rebal_payments_df.shape[0] > 0:
                    invoice_hashes = DataFrame() if invoices_df.empty else invoices_df.loc[invoices_df['value'] >= 1000].groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    invoice_hashes_30d = DataFrame() if invoices_df_30d.empty else invoices_df_30d.loc[invoices_df_30d['value'] >= 1000].groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    invoice_hashes_7d = DataFrame() if invoices_df_7d.empty else invoices_df_7d.loc[invoices_df_7d['value'] >= 1000].groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    invoice_hashes_1d = DataFrame() if invoices_df_1d.empty else invoices_df_1d.loc[invoices_df_1d['value'] >= 1000].groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    channels_df['costs'] = 0 if channels_df['rebal_in'][0] == 0 or invoice_hashes.empty == True else int(rebal_payments_df.set_index('payment_hash', inplace=False).loc[invoice_hashes[chan_id]]['fee'].sum())
                    channels_df['costs_30day'] = 0 if channels_df['rebal_in_30day'][0] == 0 or invoice_hashes_30d.empty == True else int(rebal_payments_df.set_index('payment_hash', inplace=False).loc[invoice_hashes_30d[chan_id]]['fee'].sum())
                    channels_df['costs_7day'] = 0 if channels_df['rebal_in_7day'][0] == 0 or invoice_hashes_7d.empty == True else int(rebal_payments_df.set_index('payment_hash', inplace=False).loc[invoice_hashes_7d[chan_id]]['fee'].sum())
                    channels_df['costs_1day'] = 0 if channels_df['rebal_in_1day'][0] == 0 or invoice_hashes_1d.empty == True else int(rebal_payments_df.set_index('payment_hash', inplace=False).loc[invoice_hashes_1d[chan_id]]['fee'].sum())
            channels_df['costs'] += Closures.objects.filter(funding_txid=channels_df['funding_txid'][0],funding_index=channels_df['output_index'][0])[0].closing_costs if Closures.objects.filter(funding_txid=channels_df['funding_txid'][0],funding_index=channels_df['output_index'][0]).exists() else 0
            channels_df['profits'] = channels_df['revenue'] - channels_df['costs']
            channels_df['profits_30day'] = channels_df['revenue_30day'] - channels_df['costs_30day']
            channels_df['profits_7day'] = channels_df['revenue_7day'] - channels_df['costs_7day']
            channels_df['profits_1day'] = channels_df['revenue_1day'] - channels_df['costs_1day']
            channels_df['profits_vol'] = 0 if channels_df['amt_routed_out'].iloc[0] == 0 else (channels_df['profits']/(channels_df['amt_routed_out']/1000000)).astype(int)
            channels_df['profits_vol_30day'] = 0 if channels_df['amt_routed_out_30day'].iloc[0] == 0 else (channels_df['profits_30day']/(channels_df['amt_routed_out_30day']/1000000)).astype(int)
            channels_df['profits_vol_7day'] = 0 if channels_df['amt_routed_out_7day'].iloc[0] == 0 else (channels_df['profits_7day']/(channels_df['amt_routed_out_7day']/1000000)).astype(int)
            channels_df['profits_vol_1day'] = 0 if channels_df['amt_routed_out_1day'].iloc[0] == 0 else (channels_df['profits_1day']/(channels_df['amt_routed_out_1day']/1000000)).astype(int)
            channels_df = channels_df.copy()
            channels_df['out_rate'] = int((channels_df['revenue_7day_fees']/channels_df['amt_routed_out_7day_fees'])*1000000) if channels_df['amt_routed_out_7day_fees'][0] > 0 else 0
            channels_df['rebal_ppm'] = int((channels_df['costs_7day']/channels_df['amt_rebal_in_7day'])*1000000) if channels_df['amt_rebal_in_7day'][0] > 0 else 0
            channels_df['assisted_ratio'] = round((channels_df['revenue_assist_7day_fees'] if channels_df['revenue_7day_fees'][0] == 0 else channels_df['revenue_assist_7day_fees']/channels_df['revenue_7day_fees']), 2)
            channels_df['inbound_can'] = ((channels_df['remote_balance']*100)/channels_df['capacity'])/channels_df['ar_in_target']
            channels_df['fee_ratio'] = 100 if channels_df['local_fee_rate'].iloc[0] == 0 else (round((channels_df['remote_fee_rate']/channels_df['local_fee_rate'])*1000/10)).astype(int)
            channels_df['fee_check'] = 1 if channels_df['ar_max_cost'].iloc[0] == 0 else (((channels_df['fee_ratio']/channels_df['ar_max_cost'])*1000)/10).round(0).astype(int)
            channels_df = channels_df.copy()
            channels_df['steps'] = 0 if channels_df['inbound_can'].iloc[0] < 1 else (((channels_df['in_percent']-channels_df['ar_in_target'])/((channels_df['ar_amt_target']/channels_df['capacity'])*100))+0.999).astype(int)
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
            autofees_df = DataFrame.from_records(Autofees.objects.filter(chan_id=chan_id).filter(timestamp__gte=filter_30day).order_by('-id').values())
            if autofees_df.shape[0]> 0:
                autofees_df['change'] = autofees_df.apply(lambda row: 0 if row.old_value == 0 else round((row.new_value-row.old_value)*100/row.old_value, 1), axis=1)
            results_df = af.main(channel)
            channels_df['new_rate'] = results_df[results_df['chan_id']==chan_id]['new_rate']
            channels_df['adjustment'] = results_df[results_df['chan_id']==chan_id]['adjustment']
            channels_df['net_routed_7day'] = results_df[results_df['chan_id']==chan_id]['net_routed_7day']
        else:
            channels_df = DataFrame()
            payments_df = DataFrame()
            invoices_df = DataFrame()
            peer_info_df = DataFrame()
            autofees_df = DataFrame()
        context = {
            'chan_id': chan_id,
            'channel': [] if channels_df.empty else channels_df.to_dict(orient='records')[0],
            'incoming_htlcs': PendingHTLCs.objects.filter(chan_id=chan_id).filter(incoming=True).order_by('hash_lock'),
            'outgoing_htlcs': PendingHTLCs.objects.filter(chan_id=chan_id).filter(incoming=False).order_by('hash_lock'),
            'peer_info': [] if peer_info_df.empty else peer_info_df.to_dict(orient='records')[0],
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links(),
            'autofees': [] if autofees_df.empty else autofees_df.to_dict(orient='records'),
        }
        try:
            return render(request, 'channel.html', context)
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def opens(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect())
        self_pubkey = stub.GetInfo(ln.GetInfoRequest()).identity_pubkey
        current_peers = Channels.objects.filter(is_open=True).values_list('remote_pubkey')
        exlcude_list = AvoidNodes.objects.values_list('pubkey')
        filter_60day = datetime.now() - timedelta(days=60)
        payments_60day = Payments.objects.filter(creation_date__gte=filter_60day, status=2).values_list('payment_hash')
        open_list = PaymentHops.objects.filter(payment_hash__in=payments_60day).exclude(node_pubkey=self_pubkey).exclude(node_pubkey__in=current_peers).exclude(node_pubkey__in=exlcude_list).values('node_pubkey').annotate(ppm=(Sum('fee')/Sum('amt'))*1000000, score=Round((Round(Count('id')/1, output_field=IntegerField())+Round(Sum('amt')/100000, output_field=IntegerField()))/10, output_field=IntegerField()), count=Count('id'), amount=Sum('amt'), fees=Sum('fee'), sum_cost_to=Sum('cost_to')/(Sum('amt')/1000000), alias=Max('alias')).exclude(score=0).order_by('-score', 'ppm')[:21]
        context = {
            'open_list': open_list,
            'avoid_list': AvoidNodes.objects.all(),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links()
        }
        return render(request, 'open_list.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def unprofitable_channels(request):
    if request.method == 'GET':
        # Get the timeframe from the request, default to 30 days
        timeframe = request.GET.get('timeframe', '30')
        timeframe_options = {
            '1': {'days': 1, 'name': '1 Day'},
            '7': {'days': 7, 'name': '7 Days'},
            '30': {'days': 30, 'name': '30 Days'},
            '90': {'days': 90, 'name': '90 Days'}
        }

        selected_timeframe = timeframe_options.get(timeframe, timeframe_options['30'])
        filter_date = datetime.now() - timedelta(days=selected_timeframe['days'])

        # Get active channels in a single query
        channels = Channels.objects.filter(is_active=True, is_open=True)
        channel_ids = [c.chan_id for c in channels]

        # Get current block height once
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            current_block_height = stub.GetInfo(ln.GetInfoRequest()).block_height
        except Exception as e:
            print(f"Error getting current block height: {e}")
            # Handle error appropriately, maybe return an error message or default height
            current_block_height = 0 # Or some other fallback

        # Define Age Thresholds and Max Bonus
        VERY_NEW_DAYS = 7
        ESTABLISHED_DAYS = 30
        MAX_AGE_BONUS = 2.0

        # Dictionary to store metrics for each channel
        channel_metrics_dict = {chan_id: {
            'routed_out_sats': 0,
            'last_routing': None,
            'last_routing_amount': 0,
            'rebalanced_out_sats': 0,
            'last_rebalance': None,
            'last_rebalance_amount': 0,
            'fee_revenue': 0,
            'rebalance_fee_cost': 0,
            'assisted_revenue': 0
        } for chan_id in channel_ids}

        # 1. Get outbound forwarding stats (routing out)
        out_forwards = Forwards.objects.filter(
            chan_id_out__in=channel_ids,
            forward_date__gte=filter_date
        )

        # Calculate total fees and amounts
        for forward in out_forwards:
            chan_id = forward.chan_id_out
            metrics = channel_metrics_dict[chan_id]

            # Update routed out sats
            metrics['routed_out_sats'] += int(forward.amt_out_msat / 1000) if forward.amt_out_msat else 0

            # Update fee revenue
            metrics['fee_revenue'] += forward.fee if forward.fee else 0

            # Track last routing event
            if metrics['last_routing'] is None or forward.forward_date > metrics['last_routing']:
                metrics['last_routing'] = forward.forward_date
                metrics['last_routing_amount'] = int(forward.amt_out_msat / 1000) if forward.amt_out_msat else 0

        # 2. Get inbound forwarding stats (assisted revenue)
        in_forwards = Forwards.objects.filter(
            chan_id_in__in=channel_ids,
            forward_date__gte=filter_date
        )

        for forward in in_forwards:
            chan_id = forward.chan_id_in
            channel_metrics_dict[chan_id]['assisted_revenue'] += forward.fee if forward.fee else 0

        # 3. Get outbound rebalance data - using chan_out to match channels view
        rebalance_payments = Payments.objects.filter(
            chan_out__in=channel_ids,  # This is the key change - using chan_out instead of rebal_chan
            creation_date__gte=filter_date,
            status=2,  # Successful payments
            rebal_chan__isnull=False  # This identifies it as a rebalance
        )

        for payment in rebalance_payments:
            chan_id = payment.chan_out  # Using chan_out for outbound rebalances
            metrics = channel_metrics_dict[chan_id]

            # Update rebalanced out sats
            metrics['rebalanced_out_sats'] += payment.value if payment.value else 0

            # Update rebalance fee cost
            metrics['rebalance_fee_cost'] += payment.fee if payment.fee else 0

            # Track last rebalance event
            if metrics['last_rebalance'] is None or payment.creation_date > metrics['last_rebalance']:
                metrics['last_rebalance'] = payment.creation_date
                metrics['last_rebalance_amount'] = payment.value if payment.value else 0

        # Calculate normalized metrics for each channel
        outbound_activities = []
        outbound_ratios = []  # NEW: Track outbound activity as a ratio of channel capacity
        assisted_revenues = []
        fee_rates = []

        for chan_id, metrics in channel_metrics_dict.items():
            # Get channel object to access capacity
            channel_obj = next((c for c in channels if c.chan_id == chan_id), None)
            if channel_obj:
                total_outbound = metrics['routed_out_sats'] + metrics['rebalanced_out_sats']
                outbound_activities.append(total_outbound)

                # Calculate outbound ratio (outbound activity / channel capacity)
                capacity = channel_obj.capacity or 1  # Avoid division by zero
                outbound_ratio = total_outbound / capacity
                outbound_ratios.append(outbound_ratio)

                assisted_revenues.append(metrics['assisted_revenue'])
                fee_rate = getattr(channel_obj, 'local_fee_rate', 0) or 0
                fee_rates.append(fee_rate)

        # Find min/max values for normalization
        max_outbound = max(outbound_activities) if outbound_activities else 1
        max_outbound_ratio = max(outbound_ratios) if outbound_ratios else 1
        max_assisted = max(assisted_revenues) if assisted_revenues else 1
        max_fee_rate = max(fee_rates) if fee_rates else 1000

        # Thresholds for high/medium/low classifications
        # NEW: Use ratio-based thresholds for activity
        high_ratio_threshold = max(max_outbound_ratio * 0.7, 0.5)  # At least 50% of capacity or 70% of max ratio
        medium_ratio_threshold = max(max_outbound_ratio * 0.3, 0.2)  # At least 20% of capacity or 30% of max ratio
        high_assisted_threshold = max_assisted * 0.7
        medium_assisted_threshold = max_assisted * 0.3
        high_fee_threshold = max(max_fee_rate, 1000) * 0.7
        medium_fee_threshold = max(max_fee_rate, 1000) * 0.3

        # Build the final channel metrics list
        channel_metrics = []

        for channel in channels:
            chan_id = channel.chan_id
            metrics = channel_metrics_dict[chan_id]

            # Calculate profit (fee revenue - rebalance costs)
            profit = metrics['fee_revenue'] - metrics['rebalance_fee_cost']

            # Format last routing and rebalance for display
            last_routing = {
                'date': metrics['last_routing'],
                'amount': metrics['last_routing_amount']
            } if metrics['last_routing'] else None

            last_rebalance = {
                'date': metrics['last_rebalance'],
                'amount': metrics['last_rebalance_amount']
            } if metrics['last_rebalance'] else None

            # Calculate local ratio (percentage of capacity that is local balance)
            local_ratio = channel.local_balance / channel.capacity if channel.capacity > 0 else 0
            local_ratio_pct = round(local_ratio * 100, 2)

            # Get activity metrics
            routing_out = metrics['routed_out_sats']
            rebalancing_out = metrics['rebalanced_out_sats']
            total_outbound = routing_out + rebalancing_out
            assisted_revenue = metrics['assisted_revenue']

            # NEW: Calculate outbound ratio (outbound activity / channel capacity)
            outbound_ratio = total_outbound / channel.capacity if channel.capacity > 0 else 0

            # Get fee rate
            local_fee_rate = getattr(channel, 'local_fee_rate', 0) or 0

            # Calculate priority score based on activity and fees
            # Lower score = better (less stuck), higher score = worse (more stuck)
            # We'll use a score from 0-7 matching your priority list

            # Start with worst score
            priority_score = 7.0

            # Check conditions using ratio-based thresholds
            if outbound_ratio > high_ratio_threshold and local_fee_rate > high_fee_threshold:
                # 1) High routing out ratio with high local_fee_rate
                priority_score = 1.0
            elif outbound_ratio > high_ratio_threshold and assisted_revenue > high_assisted_threshold:
                # 2) High rebalancing out ratio with high assisted revenue
                priority_score = 2.0
            elif outbound_ratio > medium_ratio_threshold and local_fee_rate > medium_fee_threshold:
                # 3) Medium routing out ratio with medium local_fee_rate
                priority_score = 3.0
            elif outbound_ratio > medium_ratio_threshold and assisted_revenue > medium_assisted_threshold:
                # 4) Medium rebalancing out ratio with medium assisted revenue
                priority_score = 4.0
            elif outbound_ratio > 0 and local_fee_rate > 0:
                # 5) Low routing out ratio and low local_fee_rate
                priority_score = 5.0
            elif outbound_ratio > 0 and assisted_revenue > 0:
                # 6) Low rebalancing out ratio and low assisted revenue
                priority_score = 6.0
            # else: 7) No activity and no compensation (already set as default)

            # Apply assisted revenue bonus
            if assisted_revenue > high_assisted_threshold:
                # Significant bonus for high assisted revenue
                assisted_bonus = 1.5
                priority_score = max(1.0, priority_score - assisted_bonus)
            elif assisted_revenue > medium_assisted_threshold:
                # Moderate bonus for medium assisted revenue
                assisted_bonus = 0.75
                priority_score = max(1.0, priority_score - assisted_bonus)
            elif assisted_revenue > 0:
                # Small bonus for any assisted revenue
                assisted_bonus = 0.25
                priority_score = max(1.0, priority_score - assisted_bonus)

            # Apply local liquidity adjustment
            # If local_ratio is low, reduce the penalty (improve the score)
            low_local_threshold = 0.2  # 20% or less is considered low local liquidity
            high_local_threshold = 0.8  # 80% or more is considered high local liquidity

            if local_ratio <= low_local_threshold:
                # Significant improvement for channels with very low local liquidity
                local_liquidity_adjustment = 3.0 * (1 - (local_ratio / low_local_threshold))
                priority_score = max(1.0, priority_score - local_liquidity_adjustment)
            elif local_ratio >= high_local_threshold:
                # Slight penalty for channels with very high local liquidity
                local_liquidity_adjustment = 0.5 * ((local_ratio - high_local_threshold) / (1 - high_local_threshold))
                priority_score = min(7.0, priority_score + local_liquidity_adjustment)

            age_bonus = 0.0
            if current_block_height > 0 and channel.chan_id: # Ensure we have data
                try:
                    opening_block_height = int(channel.chan_id) >> 40
                    if opening_block_height > 0: # Ensure valid opening height
                        channel_age_blocks = max(0, current_block_height - opening_block_height)
                        channel_age_days = channel_age_blocks / 144 # Approx days

                        if channel_age_days < VERY_NEW_DAYS:
                            # Max bonus for very new channels
                            age_bonus = MAX_AGE_BONUS
                        elif channel_age_days < ESTABLISHED_DAYS:
                            # Linearly decreasing bonus for channels between 7 and 30 days
                            age_progress = (channel_age_days - VERY_NEW_DAYS) / (ESTABLISHED_DAYS - VERY_NEW_DAYS)
                            age_bonus = MAX_AGE_BONUS * (1 - age_progress)
                        # else: age_bonus remains 0 for established channels

                except Exception as e:
                    # Handle potential errors during age calculation gracefully
                    print(f"Error calculating age for chan_id {channel.chan_id}: {e}")
                    channel_age_days = -1 # Indicate unknown age
            else:
                 channel_age_days = -1 # Indicate unknown age if block height or chan_id missing


            # Apply the age bonus, ensuring score doesn't go below 1.0
            priority_score = max(1.0, priority_score - age_bonus)

            # Normalize to 0-1 scale (divide by 7)
            smart_stuck_index = round(priority_score / 7.0, 2)

            # Add metrics to the list
            channel_metrics.append({
                'chan_id': chan_id,
                'alias': channel.alias or "---",
                'routed_out_sats': routing_out,
                'last_routing': last_routing,
                'rebalanced_out_sats': rebalancing_out,
                'last_rebalance': last_rebalance,
                'profit': profit,
                'assisted_revenue': assisted_revenue,
                'initiator': channel.initiator,
                'capacity': channel.capacity,
                'capacity_millions': round(channel.capacity / 1000000, 1),
                'local_balance': channel.local_balance,
                'remote_balance': channel.remote_balance,
                'local_ratio': local_ratio_pct,
                'stuck_index': smart_stuck_index,
                'local_fee_rate': local_fee_rate,
                'outbound_ratio': round(outbound_ratio * 100, 2),  # Add this to show the ratio as percentage
                'priority_rank': round(priority_score, 1),  # Shows the exact ranking with adjustment
                'age_days': round(channel_age_days) if channel_age_days >= 0 else 'N/A' # Add age for display
            })

        # Sort by profit (ascending to show least profitable first)
        channel_metrics.sort(key=lambda x: x['profit'])

        context = {
            'channels': channel_metrics,
            'timeframe': timeframe,
            'timeframe_name': selected_timeframe['name'],
            'timeframe_options': timeframe_options
        }

        return render(request, 'unprofitable_channels.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def actions(request):
    if request.method == 'GET':
        channels = Channels.objects.filter(is_active=True, is_open=True, private=False).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*1000)/Sum('capacity'), inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*1000)/Sum('capacity'))
        filter_7day = datetime.now() - timedelta(days=7)
        forwards = Forwards.objects.filter(forward_date__gte=filter_7day)
        action_list = []
        for channel in channels:
            result = {}
            result['chan_id'] = channel.chan_id
            result['short_chan_id'] = channel.short_chan_id
            result['remote_pubkey'] = channel.remote_pubkey
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
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
        }
        return render(request, 'action_list.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def pending_htlcs(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect())
        block_height = stub.GetInfo(ln.GetInfoRequest()).block_height
        context = {
            'incoming_htlcs': PendingHTLCs.objects.filter(incoming=True).annotate(blocks_til_expiration=Sum('expiration_height')-block_height, hours_til_expiration=((Sum('expiration_height')-block_height)*10)/60).order_by('expiration_height'),
            'outgoing_htlcs': PendingHTLCs.objects.filter(incoming=False).annotate(blocks_til_expiration=Sum('expiration_height')-block_height, hours_til_expiration=((Sum('expiration_height')-block_height)*10)/60).order_by('expiration_height')
        }
        return render(request, 'pending_htlcs.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def failed_htlcs(request):
    if request.method == 'GET':
        try:
            filter_7day = datetime.now() - timedelta(days=7)
            agg_failed_htlcs = FailedHTLCs.objects.filter(timestamp__gte=filter_7day, wire_failure=99).values('chan_id_in', 'chan_id_out').annotate(count=Count('id'), volume=Sum('amount'), chan_in_alias=Max('chan_in_alias'), chan_out_alias=Max('chan_out_alias')).order_by('-count')[:21]
            context = {
                'agg_failed_htlcs': agg_failed_htlcs
            }
            return render(request, 'failed_htlcs.html', context)
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def payments(request):
    if request.method == 'GET':
        context = {
            'payments': Payments.objects.exclude(status=3).annotate(ppm=Round((Sum('fee')*1000000)/Sum('value'), output_field=IntegerField())).order_by('-creation_date')[:150],
        }
        return render(request, 'payments.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def invoices(request):
    if request.method == 'GET':
        context = {
            'invoices': Invoices.objects.filter(state=1).order_by('-creation_date')[:150],
        }
        return render(request, 'invoices.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def rebalances(request):
    if request.method == 'GET':
        try:
            return render(request, 'rebalances.html')
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def batch(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect())
        context = {
            'iterator': range(1,11),
            'balances': stub.WalletBalance(ln.WalletBalanceRequest())
        }
        return render(request, 'batch.html', context)
    else:
        return redirect(request.META.get('HTTP_REFERER'))

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def trades(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect())
        context = {
            'trade_link': create_trade_details(stub)
        }
        return render(request, 'trades.html', context)
    else:
        return redirect(request.META.get('HTTP_REFERER'))

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def reset(request):
    if request.method == 'GET':
        context = {
            'tables':[
                {'name':'Forwards', 'count': Forwards.objects.count()},
                {'name':'Payments', 'count': Payments.objects.count()},
                {'name':'PaymentHops', 'count': PaymentHops.objects.count()},
                {'name':'Invoices', 'count': Invoices.objects.count()},
                {'name':'Rebalancer', 'count': Rebalancer.objects.count()},
                {'name':'Closures', 'count': Closures.objects.count()},
                {'name':'Resolutions', 'count': Resolutions.objects.count()},
                {'name':'Peers', 'count': Peers.objects.count()},
                {'name':'Channels', 'count': Channels.objects.count()},
                {'name':'PendingChannels', 'count': PendingChannels.objects.count()},
                {'name':'Onchain', 'count': Onchain.objects.count()},
                {'name':'PendingHTLCs', 'count': PendingHTLCs.objects.count()},
                {'name':'FailedHTLCs', 'count': FailedHTLCs.objects.count()},
                {'name':'HistFailedHTLC', 'count': HistFailedHTLC.objects.count()},
                {'name':'Autopilot', 'count': Autopilot.objects.count()},
                {'name':'Autofees', 'count': Autofees.objects.count()},
                {'name':'AvoidNodes', 'count': AvoidNodes.objects.count()},
                {'name':'PeerEvents', 'count': PeerEvents.objects.count()},
                {'name':'LocalSettings', 'count': LocalSettings.objects.count()}
            ]
        }
        return render(request, 'reset.html', context)
    else:
        return redirect(request.META.get('HTTP_REFERER'))

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def addresses(request):
    if request.method == 'GET':
        try:
            stub = walletstub.WalletKitStub(lnd_connect())
            address_data = stub.ListAddresses(walletrpc.ListAddressesRequest())
            context = {
                'address_data': address_data,
                'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
                'network_links': network_links()
            }
            return render(request, 'addresses.html', context)
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
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

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def batch_open(request):
    if request.method == 'POST':
        form = BatchOpenForm(request.POST)
        if form.is_valid():
            count = 0
            fail = False
            open_list = []
            stub = lnrpc.LightningStub(lnd_connect())
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

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def forwards(request):
    if request.method == 'GET':
        return render(request, 'forwards.html')
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def rebalancing(request):
    if request.method == 'GET':
        context = {
            'local_settings': get_local_settings('AR-'),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links()
        }
        return render(request, 'rebalancing.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def keysends(request):
    if request.method == 'GET':
        context = {
            'keysends': Invoices.objects.filter(keysend_preimage__isnull=False).order_by('-settle_date')
        }
        return render(request, 'keysends.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def autopilot(request):
    if request.method == 'GET':
        chan_id = request.GET.urlencode()[1:]
        filter_21d = datetime.now() - timedelta(days=21)
        autopilot = Autopilot.objects.filter(timestamp__gte=filter_21d).order_by('-id') if chan_id == "" else Autopilot.objects.filter(chan_id = chan_id).filter(timestamp__gte=filter_21d).order_by('-id')
        context = {
            'autopilot': autopilot
        }
        return render(request, 'autopilot.html', context)
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def outbound_fee_log(request):
    if request.method == 'GET':
        try:
            chan_id = request.GET.urlencode()[1:]
            filter_7d = datetime.now() - timedelta(days=7)
            outbound_fee_log_df = DataFrame.from_records(Autofees.objects.filter(timestamp__gte=filter_7d).order_by('-id').values() if chan_id == "" else Autofees.objects.filter(chan_id=chan_id).filter(timestamp__gte=filter_7d).order_by('-id').values())
            if outbound_fee_log_df.shape[0]> 0:
                outbound_fee_log_df['change'] = outbound_fee_log_df.apply(lambda row: 0 if row.old_value == 0 else round((row.new_value-row.old_value)*100/row.old_value, 1), axis=1)
            context = {
                'outbound_fee_log': [] if outbound_fee_log_df.empty else outbound_fee_log_df.to_dict(orient='records')
            }
            return render(request, 'outbound_fee_log.html', context)
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def inbound_fee_log(request):
    if request.method == 'GET':
        try:
            chan_id = request.GET.urlencode()[1:]
            filter_7d = datetime.now() - timedelta(days=7)
            inbound_fee_log_df = DataFrame.from_records(InboundFeeLog.objects.filter(timestamp__gte=filter_7d).order_by('-id').values() if chan_id == "" else InboundFeeLog.objects.filter(chan_id=chan_id).filter(timestamp__gte=filter_7d).order_by('-id').values())
            if inbound_fee_log_df.shape[0]> 0:
                inbound_fee_log_df['change'] = inbound_fee_log_df.apply(lambda row: 0 if row.old_value == 0 else round((row.new_value-row.old_value)*100/row.old_value, 1), axis=1)
            context = {
                'inbound_fee_log': [] if inbound_fee_log_df.empty else inbound_fee_log_df.to_dict(orient='records')
            }
            return render(request, 'inbound_fee_log.html', context)
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def peerevents(request):
    if request.method == 'GET':
        try:
            return render(request, 'peerevents.html')
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def open_channel_form(request):
    if request.method == 'POST':
        form = OpenChannelForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
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

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def close_channel_form(request):
    if request.method == 'POST':
        form = CloseChannelForm(request.POST)
        if form.is_valid():
            try:
                chan_id = form.cleaned_data['chan_id']
                if chan_id.count('x') == 2 and len(chan_id) >= 5:
                    target_channel = Channels.objects.filter(short_chan_id=chan_id)
                else:
                    target_channel = Channels.objects.filter(chan_id=chan_id)
                if target_channel.exists():
                    target_channel = target_channel.get()
                    funding_txid = target_channel.funding_txid
                    output_index = target_channel.output_index
                    force_close = form.cleaned_data['force']
                    target_fee = form.cleaned_data['target_fee']
                    if not force_close and not target_fee:
                        messages.error(request, 'Expected a fee rate for graceful closure. Please try again.')
                    channel_point = ln.ChannelPoint()
                    channel_point.funding_txid_bytes = bytes.fromhex(funding_txid)
                    channel_point.funding_txid_str = funding_txid
                    channel_point.output_index = output_index
                    stub = lnrpc.LightningStub(lnd_connect())
                    if force_close:
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

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def connect_peer_form(request):
    if request.method == 'POST':
        form = ConnectPeerForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
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

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def add_invoice_form(request):
    if request.method == 'POST':
        form = AddInvoiceForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
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

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def rebalance(request):
    if request.method == 'POST':
        form = RebalancerForm(request.POST)
        if form.is_valid():
            try:
                if Channels.objects.filter(is_active=True, is_open=True, remote_pubkey=form.cleaned_data['last_hop_pubkey']).exists() or form.cleaned_data['last_hop_pubkey'] == '':
                    chan_ids = [ch.chan_id for ch in form.cleaned_data['outgoing_chan_ids']]
                    if len(chan_ids) > 0:
                        if form.cleaned_data['last_hop_pubkey'] != '':
                            target_channel = Channels.objects.filter(is_active=True, is_open=True, remote_pubkey=form.cleaned_data['last_hop_pubkey']).first()
                            target_alias = target_channel.alias if target_channel.alias != '' else target_channel.remote_pubkey[:12]
                        else:
                            target_alias = ''
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

def get_local_settings(*prefixes):
    form = []
    if 'AR-' in prefixes:
        form.append({'unit': '', 'form_id': 'update_channels', 'id': 'update_channels'})
        form.append({'unit': '', 'form_id': 'enabled', 'value': 0, 'label': 'AR Enabled', 'id': 'AR-Enabled', 'title':'This enables or disables the auto-scheduling function', 'min':0, 'max':1},)
        form.append({'unit': '%', 'form_id': 'target_percent', 'value': 3.0, 'label': 'AR Target Amount', 'id': 'AR-Target%', 'title': 'The percentage of the total capacity to target as the rebalance amount. Default 3', 'min':0.1, 'max':100})
        form.append({'unit': 'min', 'form_id': 'target_time', 'value': 5, 'label': 'AR Target Time', 'id': 'AR-Time', 'title': 'The time spent in minutes for each individual rebalance attempt. Default 5', 'min':1, 'max':60})
        form.append({'unit': 'ppm', 'form_id': 'fee_rate', 'value': 500, 'label': 'AR Max Fee Rate', 'id': 'AR-MaxFeeRate', 'title': 'The max rate we can ever use to refill a channel with outbound. Default 500', 'min':1, 'max':5000})
        form.append({'unit': '%', 'form_id': 'outbound_percent', 'value': 75, 'label': 'AR Target Out Above', 'id': 'AR-Outbound%', 'title': 'Default oTarget% for new channels. When a channel is not AR enabled; the oTarget% is the minimum outbound a channel must have to be a source for refilling another channel. Default 75', 'min':1, 'max':100})
        form.append({'unit': '%', 'form_id': 'inbound_percent', 'value': 90, 'label': 'AR Target In Above', 'id': 'AR-Inbound%', 'title': 'Default iTarget% for new channels. When a channel is AR enabled; the iTarget% is the minimum inbound a channel must have before selected for auto rebalance. Default 90', 'min':1, 'max':100})
        form.append({'unit': '%', 'form_id': 'max_cost', 'value': 65, 'label': 'AR Max Cost', 'id': 'AR-MaxCost%', 'title': 'The ppm to target which is the percentage of the outbound fee rate for the channel being refilled. Default 65', 'min':1, 'max':100})
        form.append({'unit': '%', 'form_id': 'variance', 'value': 0, 'label': 'AR Variance', 'id': 'AR-Variance', 'title': 'The percentage of the target amount to be randomly varied with every rebalance attempt. Default 0', 'min':0, 'max':100})
        form.append({'unit': 'min', 'form_id': 'wait_period', 'value': 30, 'label': 'AR Wait Period', 'id': 'AR-WaitPeriod', 'title': 'The minutes we should wait after a failed attempt before trying again. Default 30', 'min':1, 'max':10080})
        form.append({'unit': '', 'form_id': 'autopilot', 'value': 0, 'label': 'Autopilot', 'id': 'AR-Autopilot', 'title': 'This enables or disables the Auto-Rebalance function for individual channels based on flow (automatically acts upon suggestions on this page: /actions)', 'min':0, 'max':1})
        form.append({'unit': 'days', 'form_id': 'autopilotdays', 'value': 7, 'label': 'Autopilot Days', 'id': 'AR-APDays', 'title': 'Number of days to consider for autopilot calculations. Default 7', 'min':0, 'max':100})
        form.append({'unit': '', 'form_id': 'workers', 'value': 1, 'label': 'Workers', 'id': 'AR-Workers', 'title': 'Number of concurrent rebalance workers to run at once (use a proper value for your hardware, this will increase the load on the lnd server). Default 1', 'min':1, 'max':12})
    if 'AF-' in prefixes:
        form.append({'unit': '', 'form_id': 'af_enabled', 'value': 0, 'label': 'Autofee', 'id': 'AF-Enabled', 'title': 'Enable/Disable All Auto-fee functionality', 'min':0, 'max':1})
        form.append({'unit': '', 'form_id': 'af_inbound', 'value': 0, 'label': 'Inbound Fees', 'id': 'AF-InboundFees', 'title': 'Enable/Disable Inbound Auto-fee functionality', 'min':0, 'max':1})
        form.append({'unit': 'ppm', 'form_id': 'af_maxRate', 'value': 2500, 'label': 'AF Max Rate', 'id': 'AF-MaxRate', 'title': 'Maximum Rate that can be adjusted to. Default 2500', 'min':0, 'max':5000})
        form.append({'unit': 'ppm', 'form_id': 'af_minRate', 'value': 0, 'label': 'AF Min Rate', 'id': 'AF-MinRate', 'title': 'Minimum Rate that can be adjusted to. Default 0', 'min':0, 'max':5000})
        form.append({'unit': 'ppm', 'form_id': 'af_increment', 'value': 5, 'label': 'AF Increment', 'id': 'AF-Increment', 'title': 'Target fee rate will always be a multiple of this value. Default 5', 'min':1, 'max':100})
        form.append({'unit': 'x', 'form_id': 'af_multiplier', 'value': 5, 'label': 'AF Multiplier', 'id': 'AF-Multiplier', 'title': 'Multiplier to be applied to Auto-Fee adjustments. Default 5', 'min':1, 'max':100})
        form.append({'unit': '', 'form_id': 'af_failedHTLCs', 'value': 25, 'label': 'AF FailedHTLCs', 'id': 'AF-FailedHTLCs', 'title': 'Failed HTLCs required since last fee update to trigger a fee increase (when chan liq% is below AR-LowLiq). Default 25', 'min':1, 'max':100})
        form.append({'unit': 'hours', 'form_id': 'af_updateHours', 'value': 24, 'label': 'AF Update', 'id': 'AF-UpdateHours', 'title': 'Minimum number of hours between fee updates for an individual channel. Default 24', 'min':1, 'max':100})
        form.append({'unit': '%', 'form_id': 'af_lowliq', 'value': 15, 'label': 'AF LowLiq', 'id': 'AF-LowLiqLimit', 'title': 'Limit for running low liq AF rules (increase when failed htlcs + no inbound). Default 15', 'min':0, 'max':100})
        form.append({'unit': '%', 'form_id': 'af_excess', 'value': 95, 'label': 'AF Excess', 'id': 'AF-ExcessLimit', 'title': 'Limit for running excess liq AF rules (decrease for stagnant channels and those with assisting revenues). Default 95', 'min':0, 'max':100})
    if 'GUI-' in prefixes:
        form.append({'unit': '', 'form_id': 'gui_graphLinks', 'value': 'https://mempool.space/lightning', 'label': 'Graph URL', 'id': 'GUI-GraphLinks', 'title': 'Preferred Graph URL. Default https://mempool.space/lightning'})
        form.append({'unit': '', 'form_id': 'gui_netLinks', 'value': 'https://mempool.space', 'label': 'NET URL', 'id': 'GUI-NetLinks', 'title': 'Preferred NET URL. Default https://mempool.space'})
    if 'LND-' in prefixes:
        form.append({'unit': '', 'form_id': 'lnd_cleanPayments', 'value': 0, 'label': 'LND Clean Payments', 'id': 'LND-CleanPayments', 'title': 'Clean LND Payments (toggles failed payment clean-up routine)', 'min':0, 'max':1})
        form.append({'unit': 'days', 'form_id': 'lnd_retentionDays', 'value': 30, 'label': 'LND Retention', 'id': 'LND-RetentionDays', 'title': 'LND Retention days for failed payment data', 'min':1, 'max':1000})

    for prefix in prefixes:
        ar_settings = LocalSettings.objects.filter(key__contains=prefix).values('key', 'value').order_by('key')
        for field in form:
            for sett in ar_settings:
                if field['id'] == sett['key']:
                    field['value'] = sett['value']
                    break
    return form

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def update_settings(request):
    if request.method == 'POST':
        template = [{'form_id': 'enabled', 'value': 0, 'parse': lambda x: int(x),'id': 'AR-Enabled'},
                    {'form_id': 'target_percent', 'value': 3.0, 'parse': lambda x: float(x),'id': 'AR-Target%'},
                    {'form_id': 'target_time', 'value': 5, 'parse': lambda x: int(x),'id': 'AR-Time'},
                    {'form_id': 'fee_rate', 'value': 500, 'parse': lambda x: int(x),'id': 'AR-MaxFeeRate'},
                    {'form_id': 'outbound_percent', 'value': 75, 'parse': lambda x: int(x),'id': 'AR-Outbound%'},
                    {'form_id': 'inbound_percent', 'value': 90, 'parse': lambda x: int(x),'id': 'AR-Inbound%'},
                    {'form_id': 'max_cost', 'value': 65, 'parse': lambda x: int(x),'id': 'AR-MaxCost%'},
                    {'form_id': 'variance', 'value': 0, 'parse': lambda x: int(x),'id': 'AR-Variance'},
                    {'form_id': 'wait_period', 'value': 30, 'parse': lambda x: int(x),'id': 'AR-WaitPeriod'},
                    {'form_id': 'autopilot', 'value': 0, 'parse': lambda x: int(x),'id': 'AR-Autopilot'},
                    {'form_id': 'autopilotdays', 'value': 7, 'parse': lambda x: int(x),'id': 'AR-APDays'},
                    {'form_id': 'workers', 'value': 1, 'parse': lambda x: int(x),'id': 'AR-Workers'},
                    #AF
                    {'form_id': 'af_enabled', 'value': 0, 'parse': lambda x: int(x),'id': 'AF-Enabled'},
                    {'form_id': 'af_inbound', 'value': 0, 'parse': lambda x: int(x),'id': 'AF-InboundFees'},
                    {'form_id': 'af_maxRate', 'value': 2500, 'parse': lambda x: int(x),'id': 'AF-MaxRate'},
                    {'form_id': 'af_minRate', 'value': 0, 'parse': lambda x: int(x),'id': 'AF-MinRate'},
                    {'form_id': 'af_increment', 'value': 5, 'parse': lambda x: int(x),'id': 'AF-Increment'},
                    {'form_id': 'af_multiplier', 'value': 5, 'parse': lambda x: int(x),'id': 'AF-Multiplier'},
                    {'form_id': 'af_failedHTLCs', 'value': 25, 'parse': lambda x: int(x),'id': 'AF-FailedHTLCs'},
                    {'form_id': 'af_updateHours', 'value': 24, 'parse': lambda x: int(x),'id': 'AF-UpdateHours'},
                    {'form_id': 'af_lowliq', 'value': 15, 'parse': lambda x: int(x),'id': 'AF-LowLiqLimit'},
                    {'form_id': 'af_excess', 'value': 95, 'parse': lambda x: int(x),'id': 'AF-ExcessLimit'},
                    #GUI
                    {'form_id': 'gui_graphLinks', 'value': 'https://mempool.space/lightning', 'parse': lambda x: str(x),'id': 'GUI-GraphLinks'},
                    {'form_id': 'gui_netLinks', 'value': 'https://mempool.space', 'parse': lambda x: str(x),'id': 'GUI-NetLinks'},
                    #LND
                    {'form_id': 'lnd_cleanPayments', 'value': 0, 'parse': lambda x: int(x), 'id': 'LND-CleanPayments'},
                    {'form_id': 'lnd_retentionDays', 'value': 30, 'parse': lambda x: int(x), 'id': 'LND-RetentionDays'},
                    ]

        form = LocalSettingsForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Invalid Request. Please try again.')
        else:
            update_channels = form.cleaned_data['update_channels']
            for field in template:
                value = form.cleaned_data[field['form_id']]
                if value is not None:
                    value = field['parse'](value)
                    try:
                        db_value = LocalSettings.objects.get(key=field['id'])
                    except:
                        LocalSettings(key=field['id'], value=field['value']).save()
                        db_value = LocalSettings.objects.get(key=field['id'])
                    if db_value.value == str(value) or len(str(value)) == 0:
                        continue
                    db_value.value = value
                    db_value.save()

                    if update_channels and field['id'] in ['AR-Target%', 'AR-Outbound%','AR-Inbound%','AR-MaxCost%']:
                        if field['id'] == 'AR-Target%':
                            Channels.objects.all().update(ar_amt_target=Round(F('capacity')*(value/100), output_field=IntegerField()))
                        elif field['id'] == 'AR-Outbound%':
                            Channels.objects.all().update(ar_out_target=value)
                        elif field['id'] == 'AR-Inbound%':
                            Channels.objects.all().update(ar_in_target=value)
                        elif field['id'] == 'AR-MaxCost%':
                            Channels.objects.all().update(ar_max_cost=value)
                        messages.success(request, 'All channels ' + field['id'] + ' updated to: ' + str(value))
                    else:
                        messages.success(request, field['id'] + ' updated to: ' + str(value))

    return redirect(request.META.get('HTTP_REFERER'))

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def update_channel(request):
    if request.method == 'POST':
        form = UpdateChannel(request.POST)
        if form.is_valid() and Channels.objects.filter(chan_id=form.cleaned_data['chan_id']).exists():
            chan_id = form.cleaned_data['chan_id']
            target = form.cleaned_data['target']
            update_target = int(form.cleaned_data['update_target'])
            db_channel = Channels.objects.get(chan_id=chan_id)
            if update_target == 0:
                stub = lnrpc.LightningStub(lnd_connect())
                channel_point = point(db_channel)
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=target, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv))
                db_channel.local_base_fee = target
                db_channel.save()
                messages.success(request, 'Base fee for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
            elif update_target == 1:
                stub = lnrpc.LightningStub(lnd_connect())
                channel_point = point(db_channel)
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(target/1000000), time_lock_delta=db_channel.local_cltv))
                old_fee_rate = db_channel.local_fee_rate
                db_channel.local_fee_rate = target
                db_channel.fees_updated = datetime.now()
                db_channel.save()
                Autofees(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, setting=(f"Manual"), old_value=old_fee_rate, new_value=db_channel.local_fee_rate).save()
                messages.success(request, 'Fee rate for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
            elif update_target == 12:
                stub = lnrpc.LightningStub(lnd_connect())
                version = stub.GetInfo(ln.GetInfoRequest()).version
                if float(version[:4]) >= 0.18:
                    channel_point = point(db_channel)
                    inbound_fee_rate = db_channel.local_inbound_fee_rate if db_channel.local_inbound_fee_rate else 0
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, inbound_fee=ln.InboundFee(base_fee_msat=target, fee_rate_ppm=inbound_fee_rate)))
                    db_channel.local_inbound_base_fee = target
                    db_channel.save()
                    messages.success(request, 'Inbound base fee for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
                else:
                    messages.error(request, f'LND version too low to set inbound fees, update to v0.18+')
            elif update_target == 13:
                stub = lnrpc.LightningStub(lnd_connect())
                version = stub.GetInfo(ln.GetInfoRequest()).version
                if float(version[:4]) >= 0.18:
                    channel_point = point(db_channel)
                    inbound_base_fee = db_channel.local_inbound_base_fee if db_channel.local_inbound_base_fee else 0
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, inbound_fee=ln.InboundFee(base_fee_msat=inbound_base_fee, fee_rate_ppm=target)))
                    db_channel.local_inbound_fee_rate = target
                    db_channel.save()
                    messages.success(request, 'Inbound fee rate for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
                else:
                    messages.error(request, f'LND version too low to set inbound fees, update to v0.18+')
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
                stub = lnrouter.RouterStub(lnd_connect())
                channel_point = point(db_channel)
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
                stub = lnrpc.LightningStub(lnd_connect())
                channel_point = point(db_channel)
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=target))
                db_channel.local_cltv = target
                db_channel.save()
                messages.success(request, 'CLTV for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(float(target)))
            elif update_target == 10:
                stub = lnrpc.LightningStub(lnd_connect())
                channel_point = point(db_channel)
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, min_htlc_msat_specified=True, min_htlc_msat=int(target*1000)))
                db_channel.local_min_htlc_msat = int(target*1000)
                db_channel.save()
                messages.success(request, 'Min HTLC for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(float(target)))
            elif update_target == 11:
                stub = lnrpc.LightningStub(lnd_connect())
                channel_point = point(db_channel)
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, max_htlc_msat=int(target*1000)))
                db_channel.local_max_htlc_msat = int(target*1000)
                db_channel.save()
                messages.success(request, 'Max HTLC for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
            else:
                messages.error(request, 'Invalid target code. Please try again.')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def update_pending(request):
    if request.method == 'POST':
        form = UpdatePending(request.POST)
        if form.is_valid():
            funding_txid = form.cleaned_data['funding_txid']
            output_index = form.cleaned_data['output_index']
            target = form.cleaned_data['target']
            update_target = int(form.cleaned_data['update_target'])
            if PendingChannels.objects.filter(funding_txid=funding_txid, output_index=output_index).exists():
                pending_channel = PendingChannels.objects.filter(funding_txid=funding_txid, output_index=output_index)[0]
            else:
                pending_channel = PendingChannels(funding_txid=funding_txid, output_index=output_index)
                pending_channel.save()
            if update_target == 0:
                pending_channel.local_base_fee = target
                pending_channel.save()
                messages.success(request, 'Base fee for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target))
            elif update_target == 1:
                pending_channel.local_fee_rate = target
                pending_channel.save()
                messages.success(request, 'Fee rate for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target))
            elif update_target == 2:
                pending_channel.ar_amt_target = target
                pending_channel.save()
                messages.success(request, 'Auto rebalancer target amount for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target))
            elif update_target == 3:
                pending_channel.ar_in_target = target
                pending_channel.save()
                messages.success(request, 'Auto rebalancer inbound target for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target) + '%')
            elif update_target == 4:
                pending_channel.ar_out_target = target
                pending_channel.save()
                messages.success(request, 'Auto rebalancer outbound target for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target) + '%')
            elif update_target == 5:
                pending_channel.auto_rebalance = True if pending_channel.auto_rebalance == False or pending_channel.auto_rebalance == None else False
                pending_channel.save()
                messages.success(request, 'Auto rebalancer status for pending pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(pending_channel.auto_rebalance))
            elif update_target == 6:
                pending_channel.ar_max_cost = target
                pending_channel.save()
                messages.success(request, 'Auto rebalancer max cost for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target) + '%')
            elif update_target == 8:
                auto_fees = int(LocalSettings.objects.filter(key='AF-Enabled')[0].value) if LocalSettings.objects.filter(key='AF-Enabled').exists() else 0
                pending_channel.auto_fees = True if pending_channel.auto_fees == False or (pending_channel.auto_fees == None and auto_fees == 0) else False
                pending_channel.save()
                messages.success(request, 'Auto fees status for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(pending_channel.auto_fees))
            elif update_target == 9:
                pending_channel.local_cltv = target
                pending_channel.save()
                messages.success(request, 'CLTV for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target))
            else:
                messages.error(request, 'Invalid target code. Please try again.')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

def point(ch: Channels):
    channel_point = ln.ChannelPoint()
    channel_point.funding_txid_bytes = bytes.fromhex(ch.funding_txid)
    channel_point.funding_txid_str = ch.funding_txid
    channel_point.output_index = ch.output_index
    return channel_point

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def update_setting(request):
    if request.method == 'POST':
        form = UpdateSetting(request.POST)
        if form.is_valid():
            key = form.cleaned_data['key']
            value = form.cleaned_data['value']
            if key == 'ALL-oRate':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect())
                channels = Channels.objects.filter(is_open=True)
                for db_channel in channels:
                    channel_point = point(db_channel)
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(target/1000000), time_lock_delta=db_channel.local_cltv))
                    old_fee_rate = db_channel.local_fee_rate
                    db_channel.local_fee_rate = target
                    db_channel.fees_updated = datetime.now()
                    db_channel.save()
                    Autofees(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, setting=(f"Manual"), old_value=old_fee_rate, new_value=db_channel.local_fee_rate).save()
                messages.success(request, 'Fee rate for all open channels updated to a value of: ' + str(target))
            elif key == 'ALL-oBase':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect())
                channels = Channels.objects.filter(is_open=True)
                for db_channel in channels:
                    channel_point = point(db_channel)
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=target, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv))
                    db_channel.local_base_fee = target
                    db_channel.save()
                messages.success(request, 'Base fee for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-iRate':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect())
                version = stub.GetInfo(ln.GetInfoRequest()).version
                if float(version[:4]) >= 0.18:
                    channels = Channels.objects.filter(is_open=True)
                    for db_channel in channels:
                        channel_point = point(db_channel)
                        inbound_base_fee = db_channel.local_inbound_base_fee if db_channel.local_inbound_base_fee else 0
                        stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, inbound_fee=ln.InboundFee(base_fee_msat=inbound_base_fee, fee_rate_ppm=target)))
                        db_channel.local_inbound_fee_rate = target
                        db_channel.save()
                    messages.success(request, 'Inbound fee rate for all open channels updated to a value of: ' + str(target))
                else:
                    messages.error(request, f'LND version too low to set inbound fees, update to v0.18+')
            elif key == 'ALL-iBase':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect())
                version = stub.GetInfo(ln.GetInfoRequest()).version
                if float(version[:4]) >= 0.18:
                    channels = Channels.objects.filter(is_open=True)
                    for db_channel in channels:
                        channel_point = point(db_channel)
                        inbound_fee_rate = db_channel.local_inbound_fee_rate if db_channel.local_inbound_fee_rate else 0
                        stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, inbound_fee=ln.InboundFee(base_fee_msat=target, fee_rate_ppm=inbound_fee_rate)))
                        db_channel.local_inbound_base_fee = target
                        db_channel.save()
                    messages.success(request, 'Inbound base fee for all channels updated to a value of: ' + str(target))
                else:
                    messages.error(request, f'LND version too low to set inbound fees, update to v0.18+')
            elif key == 'ALL-CLTV':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect())
                channels = Channels.objects.filter(is_open=True)
                for db_channel in channels:
                    channel_point = point(db_channel)
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=target))
                    db_channel.local_cltv = target
                    db_channel.save()
                messages.success(request, 'CLTV for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-minHTLC':
                target = int(float(value)*1000)
                stub = lnrpc.LightningStub(lnd_connect())
                channels = Channels.objects.filter(is_open=True)
                for db_channel in channels:
                    channel_point = point(db_channel)
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, min_htlc_msat_specified=True, min_htlc_msat=target))
                    db_channel.local_min_htlc_msat = target
                    db_channel.save()
                messages.success(request, 'Min HTLC for all channels updated to a value of: ' + str(float(value)))
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
                try:
                    db_enabled = LocalSettings.objects.get(key='AF-UpdateHours')
                except:
                    LocalSettings(key='AF-UpdateHours', value='24').save()
                    db_enabled = LocalSettings.objects.get(key='AF-UpdateHours')
                db_enabled.value = target
                db_enabled.save()
                messages.success(request, 'Updated autofees update hours setting to: ' + str(target))
            else:
                messages.error(request, 'Invalid Request. Please try again. [' + key +']')
        else:
            messages.error(request, 'Invalid Request Form. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def update_closing(request):
    if request.method == 'POST':
        form = UpdateClosing(request.POST)
        if form.is_valid() and Closures.objects.filter(funding_txid=form.cleaned_data['funding_txid'], funding_index=form.cleaned_data['funding_index']).exists():
            funding_txid = form.cleaned_data['funding_txid']
            funding_index = form.cleaned_data['funding_index']
            target = int(form.cleaned_data['target'])
            db_closing = Closures.objects.filter(funding_txid=funding_txid, funding_index=funding_index)[0]
            db_closing.closing_costs = target
            db_closing.save()
            messages.success(request, 'Updated closing costs for ' + str(funding_txid) + ':' + str(funding_index) + ' updated to a value of: ' + str(target))
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def update_keysend(request):
    if request.method == 'POST':
        form = UpdateKeysend(request.POST)
        if form.is_valid() and Invoices.objects.filter(r_hash=form.cleaned_data['r_hash']).exists():
            r_hash = form.cleaned_data['r_hash']
            db_invoice = Invoices.objects.filter(r_hash=r_hash)[0]
            db_invoice.is_revenue = not db_invoice.is_revenue
            db_invoice.save()
            messages.success(request, ('Marked' if db_invoice.is_revenue else 'Unmarked') + ' invoice ' + str(r_hash) + ' as revenue.')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def add_avoid(request):
    if request.method == 'POST':
        form = AddAvoid(request.POST)
        if form.is_valid():
            pubkey = form.cleaned_data['pubkey']
            notes = form.cleaned_data['notes']
            AvoidNodes(pubkey=pubkey, notes=notes).save()
            messages.success(request, 'Successfully added node ' + str(pubkey) + ' to the avoid list.')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def remove_avoid(request):
    if request.method == 'POST':
        form = RemoveAvoid(request.POST)
        if form.is_valid() and AvoidNodes.objects.filter(pubkey=form.cleaned_data['pubkey']).exists():
            pubkey = form.cleaned_data['pubkey']
            AvoidNodes.objects.filter(pubkey=pubkey).delete()
            messages.success(request, 'Successfully removed node ' + str(pubkey) + ' from the avoid list.')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def get_fees(request):
    if request.method == 'GET':
        missing_fees = Closures.objects.exclude(close_type__in=[4, 5]).exclude(open_initiator=2, resolution_count=0).filter(closing_costs=0)
        if missing_fees:
            for missing_fee in missing_fees:
                prior_closures = Closures.objects.filter(id__lt=missing_fee.id).values_list('chan_id', flat=True)
                swept = list(Resolutions.objects.filter(chan_id__in=prior_closures).values_list('sweep_txid', flat=True))
                try:
                    txid = missing_fee.closing_tx
                    closing_costs = get_tx_fees(txid) if missing_fee.open_initiator == 1 else 0
                    for resolution in Resolutions.objects.filter(chan_id=missing_fee.chan_id).exclude(resolution_type=2):
                        if resolution.sweep_txid not in swept:
                            closing_costs += get_tx_fees(resolution.sweep_txid)
                            swept.append(resolution.sweep_txid)
                    missing_fee.closing_costs = closing_costs
                    missing_fee.save()
                except Exception as error:
                    messages.error(request, f"Error getting closure fees: {txid=} {error=}")
                    return redirect(request.META.get('HTTP_REFERER'))
    return redirect(request.META.get('HTTP_REFERER'))

@api_view(['POST'])
@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def sign_message(request):
    serializer = SignMessageSerializer(data=request.data)
    if serializer.is_valid():
        message = serializer.validated_data['message']
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            response = stub.SignMessage(ln.SignMessageRequest(msg=message.encode('utf-8'), single_hash=False))
            return Response({'message': 'Success', 'data': str(response.signature)})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': f'Sign message failed! Error: {error_msg}'})
    else:
        return Response({'error': 'Invalid request!'})

class PaymentsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Payments.objects.all().order_by('-creation_date')
    serializer_class = PaymentSerializer
    filterset_fields = {'status':['exact','lt','gt'], 'creation_date':['lte','gte'], 'chan_out': ['exact'], 'index': ['lt']}

class PaymentHopsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = PaymentHops.objects.all()
    serializer_class = PaymentHopsSerializer

class InvoicesViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Invoices.objects.all().order_by('-creation_date')
    serializer_class = InvoiceSerializer
    filterset_fields = {'state': ['exact','lt', 'gt'], 'is_revenue': ['exact'], 'settle_date': ['gte'], 'chan_in': ['exact'], 'index': ['lt']}

    def update(self, request, pk=None):
        setting = get_object_or_404(Invoices.objects.all(), pk=pk)
        serializer = InvoiceSerializer(setting, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)

class ForwardsFilter(FilterSet):
    chan_in_or_out = CharFilter(method='filter_chan_in_or_out', label='Chan In Or Out')
    forward_date__lte = DateTimeFilter(field_name='forward_date', lookup_expr='lte')
    forward_date__gte = DateTimeFilter(field_name='forward_date', lookup_expr='gte')
    forward_date__lt = DateTimeFilter(field_name='forward_date', lookup_expr='lt')
    forward_date__gt = DateTimeFilter(field_name='forward_date', lookup_expr='gt')
    id__lt = NumberFilter(field_name='id', lookup_expr='lt')

    def filter_chan_in_or_out(self, queryset, name, value):
        return queryset.filter(
            Q(chan_id_in__exact=value) | Q(chan_id_out__exact=value)
        )

    class Meta:
        model = Forwards
        fields = ['chan_in_or_out', 'forward_date__lte', 'forward_date__gte', 'forward_date__lt', 'forward_date__gt', 'id__lt']

class ForwardsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Forwards.objects.all().order_by('-id')
    serializer_class = ForwardSerializer
    filterset_class = ForwardsFilter

class PeersViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Peers.objects.all()
    serializer_class = PeerSerializer

class OnchainViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Onchain.objects.all()
    serializer_class = OnchainSerializer
    filterset_fields = {'time_stamp': ['lte','gte']}

class ClosuresViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Closures.objects.all()
    serializer_class = ClosuresSerializer
    filterset_fields = {'close_height': ['lte','gte']}

class ResolutionsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Resolutions.objects.all()
    serializer_class = ResolutionsSerializer

class PendingHTLCViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = PendingHTLCs.objects.all()
    serializer_class = PendingHTLCSerializer

class PeerEventsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = PeerEvents.objects.all().order_by('-id')
    serializer_class = PeerEventsSerializer
    filterset_fields = {'chan_id': ['exact'], 'id': ['lt']}

class TradeSalesViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = TradeSales.objects.all()
    serializer_class = TradeSalesSerializer

    def update(self, request, pk):
        rebalance = get_object_or_404(self.queryset, pk=pk)
        serializer = self.get_serializer(rebalance, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

class FeeLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Autofees.objects.all().order_by('-id')
    serializer_class = FeeLogSerializer
    filterset_fields = {'chan_id': ['exact'], 'id': ['lt']}

class InboundFeeLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = InboundFeeLog.objects.all().order_by('-id')
    serializer_class = InboundFeeLogSerializer
    filterset_fields = {'chan_id': ['exact'], 'id': ['lt']}

class FailedHTLCFilter(FilterSet):
    chan_in_or_out = CharFilter(method='filter_chan_in_or_out', label='Chan In Or Out')
    chan_id_in = CharFilter(field_name='chan_id_in', lookup_expr='exact')
    chan_id_out = CharFilter(field_name='chan_id_out', lookup_expr='exact')
    wire_failure__lt = NumberFilter(field_name='wire_failure', lookup_expr='lt')
    wire_failure__gt = NumberFilter(field_name='wire_failure', lookup_expr='gt')
    id__lt = NumberFilter(field_name='id', lookup_expr='lt')

    def filter_chan_in_or_out(self, queryset, name, value):
        return queryset.filter(
            Q(chan_id_in__exact=value) | Q(chan_id_out__exact=value)
        )

    class Meta:
        model = FailedHTLCs
        fields = ['chan_in_or_out', 'chan_id_in', 'chan_id_out', 'wire_failure__lt', 'wire_failure__gt', 'id__lt']

class FailedHTLCViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = FailedHTLCs.objects.all().order_by('-id')
    serializer_class = FailedHTLCSerializer
    filterset_class = FailedHTLCFilter

class LocalSettingsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = LocalSettings.objects.all()
    serializer_class = LocalSettingsSerializer

    def update(self, request, pk):
        setting = get_object_or_404(self.queryset, pk=pk)
        serializer = LocalSettingsSerializer(setting, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)

class ChannelsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Channels.objects.all()
    serializer_class = ChannelSerializer
    filterset_fields = ['is_open', 'private', 'is_active', 'auto_rebalance']

    def update(self, request, pk):
        channel = get_object_or_404(self.queryset, pk=pk)
        serializer = ChannelSerializer(channel, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

class RebalancerViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Rebalancer.objects.all().order_by('-id')
    serializer_class = RebalancerSerializer
    filterset_fields = {'status':['lt','gt','exact'], 'payment_hash':['exact'], 'stop':['gt'], 'last_hop_pubkey':['exact'], 'id':['lt']}

    def create(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

    def update(self, request, pk):
        rebalance = get_object_or_404(self.queryset, pk=pk)
        serializer = RebalancerSerializer(rebalance, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            rebalance.stop = datetime.now()
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def forwards_summary(request):
    filter_1day = datetime.now() - timedelta(days=1)
    filter_7day = datetime.now() - timedelta(days=7)
    summary_out = Forwards.objects.values(chan_id=F('chan_id_out')).annotate(
        count_outgoing_1day=Count('id', filter=Q(forward_date__gte=filter_1day)),
        sum_outgoing_1day=Coalesce(Sum('amt_out_msat', filter=Q(forward_date__gte=filter_1day)), 0),
        count_outgoing_7day=Count('id', filter=Q(forward_date__gte=filter_7day)),
        sum_outgoing_7day=Coalesce(Sum('amt_out_msat', filter=Q(forward_date__gte=filter_7day)), 0),
        sum_fees_1day=Coalesce(Sum('fee', filter=Q(forward_date__gte=filter_1day)), 0.0),
        sum_fees_7day=Coalesce(Sum('fee', filter=Q(forward_date__gte=filter_7day)), 0.0),
        count_incoming_1day=Value(0),
        sum_incoming_1day=Value(0),
        count_incoming_7day=Value(0),
        sum_incoming_7day=Value(0)
    ).filter(
        Q(count_outgoing_1day__gt=0) |
        Q(sum_outgoing_1day__gt=0) |
        Q(count_outgoing_7day__gt=0) |
        Q(sum_outgoing_7day__gt=0) |
        Q(sum_fees_1day__gt=0) |
        Q(sum_fees_7day__gt=0)
    )

    summary_in = Forwards.objects.values(chan_id=F('chan_id_in')).annotate(
        count_outgoing_1day=Value(0),
        sum_outgoing_1day=Value(0),
        count_outgoing_7day=Value(0),
        sum_outgoing_7day=Value(0),
        sum_fees_1day=Value(0),
        sum_fees_7day=Value(0),
        count_incoming_1day=Count('id', filter=Q(forward_date__gte=filter_1day)),
        sum_incoming_1day=Coalesce(Sum('amt_in_msat', filter=Q(forward_date__gte=filter_1day)), 0),
        count_incoming_7day=Count('id', filter=Q(forward_date__gte=filter_7day)),
        sum_incoming_7day=Coalesce(Sum('amt_in_msat', filter=Q(forward_date__gte=filter_7day)), 0)
    ).filter(
        Q(count_incoming_1day__gt=0) |
        Q(sum_incoming_1day__gt=0) |
        Q(count_incoming_7day__gt=0) |
        Q(sum_incoming_7day__gt=0)
    )

    return Response({'results': summary_out.union(summary_in)})

def get_channeldb_file_size():
    try:
        # Create the Enable setting if it doesn't exist ---
        enabled_setting = LocalSettings.objects.filter(key='RemoteFSEnabled').first()
        if not enabled_setting:
            LocalSettings.objects.create(key='RemoteFSEnabled', value='0')  # Default: disabled
            # IMPORTANT: We do NOT create other settings here.
            # Only once enabled at /api/settings/RemoteFSEnabled/, we create the rest to avoid boilerplate
            enabled = False  # Since we just created it, it's disabled.
        else:
            # Read the Enable setting ---
            enabled = bool(int(LocalSettings.objects.get(key='RemoteFSEnabled').value))

        if enabled:
            # Only import paramiko if enabled
            import paramiko

            # Create connection settings only if enabled AND they don't exist ---
            host = LocalSettings.objects.filter(key='RemoteFSHost').first()
            if not host:
                LocalSettings.objects.create(key='RemoteFSHost', value='')
                host_value = LocalSettings.objects.get(key='RemoteFSHost').value
            else:
                host_value = host.value

            user = LocalSettings.objects.filter(key='RemoteFSUser').first()
            if not user:
                LocalSettings.objects.create(key='RemoteFSUser', value='')
                user_value = LocalSettings.objects.get(key='RemoteFSUser').value
            else:
                user_value = user.value

            port = LocalSettings.objects.filter(key='RemoteFSPort').first()
            if not port:
                LocalSettings.objects.create(key='RemoteFSPort', value='22')  # Default SSH port
                port_value = LocalSettings.objects.get(key='RemoteFSPort').value
            else:
                port_value = port.value

            db_path = LocalSettings.objects.filter(key='RemoteFSPath').first()
            if not db_path:
                default_path = '/home/admin/.lnd/data/graph/mainnet/channel.db'
                LocalSettings.objects.create(key='RemoteFSPath', value=default_path)
                db_path_value = LocalSettings.objects.get(key='RemoteFSPath').value
            else:
                db_path_value = db_path.value

            # Read the connection settings ---
            port = int(port_value)  # Ensure port is an integer
            channel_db_path = db_path_value if db_path_value else settings.LND_DATABASE_PATH # Use settings path if db path is blank

            # Check for required settings
            if not host_value or not user_value:
                print("Error: Remote file size enabled, but host or user is not set.")
                return round(path.getsize(path.expanduser(settings.LND_DATABASE_PATH))*0.000000001, 3)

            # --- Paramiko logic ---
            try:
                # Create SSH client
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Automatically add host keys

                # Connect to the remote host (eg 10.1.1.2, lnd, 22)
                ssh.connect(hostname=host_value, username=user_value, port=port)

                # Open an SFTP session
                sftp = ssh.open_sftp()

                # Get file stats
                file_stat = sftp.stat(channel_db_path)

                # Get file size
                file_size_bytes = file_stat.st_size

                # Close connections
                sftp.close()
                ssh.close()

                return round(file_size_bytes * 0.000000001, 3)

            except Exception as e:
                print(f"Error retrieving file size with paramiko: {e}")
                return round(path.getsize(path.expanduser(settings.LND_DATABASE_PATH))*0.000000001, 3) # Fallback
            # --- End Paramiko logic ---

        else:
            # Use the original default behavior (local file size)
            return round(path.getsize(path.expanduser(settings.LND_DATABASE_PATH))*0.000000001, 3)

    except Exception as e:
        # Handle exceptions
        print(f"Error retrieving channel.db file size: {e}")
        return 0

@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def node_info(request):
    stub = lnrpc.LightningStub(lnd_connect())
    node_info = stub.GetInfo(ln.GetInfoRequest())
    balances = stub.WalletBalance(ln.WalletBalanceRequest())
    pending_channels = stub.PendingChannels(ln.PendingChannelsRequest())

    limbo_balance = pending_channels.total_limbo_balance
    pending_open = None
    pending_closed = None
    pending_force_closed = None
    waiting_for_close = None
    pending_open_balance = 0
    pending_closing_balance = 0
    if pending_channels.pending_open_channels:
        target_resp = pending_channels.pending_open_channels
        peers = Peers.objects.all()
        pending_changes = PendingChannels.objects.all()
        pending_open = []
        inbound_setting = int(LocalSettings.objects.filter(key='AR-Inbound%')[0].value) if LocalSettings.objects.filter(key='AR-Inbound%').exists() else 90
        outbound_setting = int(LocalSettings.objects.filter(key='AR-Outbound%')[0].value) if LocalSettings.objects.filter(key='AR-Outbound%').exists() else 75
        amt_setting = float(LocalSettings.objects.filter(key='AR-Target%')[0].value) if LocalSettings.objects.filter(key='AR-Target%').exists() else 3
        cost_setting = int(LocalSettings.objects.filter(key='AR-MaxCost%')[0].value) if LocalSettings.objects.filter(key='AR-MaxCost%').exists() else 65
        auto_fees = int(LocalSettings.objects.filter(key='AF-Enabled')[0].value) if LocalSettings.objects.filter(key='AF-Enabled').exists() else 0
        for i in range(0,len(target_resp)):
            item = {}
            pending_open_balance += target_resp[i].channel.local_balance
            funding_txid = target_resp[i].channel.channel_point.split(':')[0]
            output_index = target_resp[i].channel.channel_point.split(':')[1]
            updated = pending_changes.filter(funding_txid=funding_txid,output_index=output_index).exists()
            item['alias'] = peers.filter(pubkey=target_resp[i].channel.remote_node_pub)[0].alias if peers.filter(pubkey=target_resp[i].channel.remote_node_pub).exists() else ''
            item['remote_node_pub'] = target_resp[i].channel.remote_node_pub
            item['channel_point'] = target_resp[i].channel.channel_point
            item['funding_txid'] = funding_txid
            item['output_index'] = output_index
            item['capacity'] = target_resp[i].channel.capacity
            item['local_balance'] = target_resp[i].channel.local_balance
            item['remote_balance'] = target_resp[i].channel.remote_balance
            item['local_chan_reserve_sat'] = target_resp[i].channel.local_chan_reserve_sat
            item['remote_chan_reserve_sat'] = target_resp[i].channel.remote_chan_reserve_sat
            item['initiator'] = target_resp[i].channel.initiator
            item['commitment_type'] = target_resp[i].channel.commitment_type
            item['commit_fee'] = target_resp[i].commit_fee
            item['commit_weight'] = target_resp[i].commit_weight
            item['fee_per_kw'] = target_resp[i].fee_per_kw
            item['local_base_fee'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].local_base_fee if updated else ''
            item['local_fee_rate'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].local_fee_rate if updated else ''
            item['local_cltv'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].local_cltv if updated else ''
            item['auto_rebalance'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].auto_rebalance if updated and pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].auto_rebalance != None else False
            item['ar_amt_target'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_amt_target if updated and pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_amt_target != None else int((amt_setting/100) * target_resp[i].channel.capacity)
            item['ar_in_target'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_in_target if updated and pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_in_target != None else inbound_setting
            item['ar_out_target'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_out_target if updated and pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_out_target != None else outbound_setting
            item['ar_max_cost'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_max_cost if updated and pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_max_cost != None else cost_setting
            item['auto_fees'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].auto_fees if updated and pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].auto_fees != None else (False if auto_fees == 0 else True)
            pending_open.append(item)
    if pending_channels.pending_closing_channels:
        target_resp = pending_channels.pending_closing_channels
        pending_closed = []
        for i in range(0,len(target_resp)):
            pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
            'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type, 'local_commit_fee_sat': target_resp[i].commitments.local_commit_fee_sat,'limbo_balance':target_resp[i].limbo_balance,'closing_txid':target_resp[i].closing_txid}
            pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
            pending_closed.append(pending_item)
    if pending_channels.pending_force_closing_channels:
        target_resp = pending_channels.pending_force_closing_channels
        pending_force_closed = []
        for i in range(0,len(target_resp)):
            pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'initiator':target_resp[i].channel.initiator,
            'commitment_type':target_resp[i].channel.commitment_type,'closing_txid':target_resp[i].closing_txid,'limbo_balance':target_resp[i].limbo_balance,'maturity_height':target_resp[i].maturity_height,'blocks_til_maturity':target_resp[i].blocks_til_maturity if target_resp[i].blocks_til_maturity > 0 else find_next_block_maturity(target_resp[i]),
            'maturity_datetime':(datetime.now()+timedelta(minutes=(10*target_resp[i].blocks_til_maturity if target_resp[i].blocks_til_maturity > 0 else 10*find_next_block_maturity(target_resp[i]) )))}
            pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
            pending_force_closed.append(pending_item)
    if pending_channels.waiting_close_channels:
        target_resp = pending_channels.waiting_close_channels
        waiting_for_close = []
        for i in range(0,len(target_resp)):
            pending_closing_balance += target_resp[i].limbo_balance
            pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
            'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type, 'local_commit_fee_sat': target_resp[i].commitments.local_commit_fee_sat, 'limbo_balance':target_resp[i].limbo_balance,'closing_txid':target_resp[i].closing_txid}
            pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
            waiting_for_close.append(pending_item)
    limbo_balance -= pending_closing_balance
    try:
        db_size = get_channeldb_file_size()
    except:
        db_size = 0
    return Response({
        'version': node_info.version,
        'num_peers': node_info.num_peers,
        'synced_to_graph': node_info.synced_to_graph,
        'synced_to_chain': node_info.synced_to_chain,
        'num_active_channels': node_info.num_active_channels,
        'num_inactive_channels': node_info.num_inactive_channels,
        'chains': [chain.chain+"-"+chain.network for chain in node_info.chains],
        'block': {'hash': node_info.block_hash, 'height': node_info.block_height},
        'balance': {
            'limbo': limbo_balance,
            'onchain': balances.total_balance,
            'confirmed': balances.confirmed_balance,
            'unconfirmed': balances.unconfirmed_balance,
            'total': balances.total_balance + pending_open_balance + limbo_balance,
        },
        'pending_open': pending_open,
        'pending_closed': pending_closed,
        'pending_force_closed': pending_force_closed,
        'waiting_for_close': waiting_for_close,
        'db_size': db_size
    })

@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def connect_peer(request):
    serializer = ConnectPeerSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            peer_id = serializer.validated_data['peer_id']
            if peer_id.count('@') == 0 and len(peer_id) == 66:
                peer_pubkey = peer_id
                node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey, include_channels=False)).node
                host = node.addresses[0].addr
            elif peer_id.count('@') == 1 and len(peer_id.split('@')[0]) == 66:
                peer_pubkey, host = peer_id.split('@')
            else:
                return Response({'error': 'Invalid peer pubkey or connection string.'})
            ln_addr = ln.LightningAddress(pubkey=peer_pubkey, host=host)
            stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
            return Response({'message': 'Connection successful!'})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Connection request failed! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'})

@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def disconnect_peer(request):
    serializer = DisconnectPeerSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            peer_id = serializer.validated_data['peer_id']
            if len(peer_id) == 66:
                peer_pubkey = peer_id
            else:
                return Response({'error': 'Invalid peer pubkey.'})
            stub.DisconnectPeer(ln.DisconnectPeerRequest(pub_key=peer_pubkey))
            if Peers.objects.filter(pubkey=peer_id).exists():
                db_peer = Peers.objects.filter(pubkey=peer_id)[0]
                db_peer.connected = False
                db_peer.save()
            return Response({'message': 'Disconnection successful!'})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Connection request failed! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'})

@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def rebalance_stats(request):
    try:
        filter_7day = datetime.now() - timedelta(days=7)
        rebalances = Rebalancer.objects.filter(stop__gt=filter_7day).values('last_hop_pubkey').annotate(attempts=Count('last_hop_pubkey'), successes=Sum(Case(When(status=2, then=1), output_field=IntegerField())))
        return Response(rebalances)
    except Exception as e:
        error = str(e)
        return Response({'error': 'Unable to fetch stats! Error: ' + error})

@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def open_channel(request):
    serializer = OpenChannelSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect())
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
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def close_channel(request):
    serializer = CloseChannelSerializer(data=request.data)
    if serializer.is_valid():
        try:
            chan_id = serializer.validated_data['chan_id']
            if chan_id.count('x') == 2 and len(chan_id) >= 5:
                target_channel = Channels.objects.filter(short_chan_id=chan_id)
            else:
                target_channel = Channels.objects.filter(chan_id=chan_id)
            if target_channel.exists():
                target_channel = target_channel.get()
                funding_txid = target_channel.funding_txid
                output_index = target_channel.output_index
                target_fee = serializer.validated_data['target_fee']
                channel_point = ln.ChannelPoint()
                channel_point.funding_txid_bytes = bytes.fromhex(funding_txid)
                channel_point.funding_txid_str = funding_txid
                channel_point.output_index = output_index
                stub = lnrpc.LightningStub(lnd_connect())
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
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def add_invoice(request):
    serializer = AddInvoiceSerializer(data=request.data)
    if serializer.is_valid() and serializer.validated_data['value'] >= 0:
        try:
            stub = lnrpc.LightningStub(lnd_connect())
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

def get_new_address(stub, legacy=False):
    version = stub.GetInfo(ln.GetInfoRequest()).version
    # Verify sufficient version to handle p2tr address creation
    if float(version[:4]) >= 0.15 and not legacy:
        response = stub.NewAddress(ln.NewAddressRequest(type=4))
    else:
        response = stub.NewAddress(ln.NewAddressRequest(type=0))
    return response

@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def new_address(request):
    serializer = NewAddressSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            response = get_new_address(stub, legacy=serializer.validated_data['legacy'])
            return Response({'message': 'Retrieved new deposit address!', 'data':str(response.address)})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Address creation failed! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'}, status=400)

@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def consolidate_utxos(request):
    serializer = ConsolidateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            self_addr = get_new_address(stub).address
            txid = stub.SendCoins(ln.SendCoinsRequest(addr=self_addr, send_all=True, sat_per_vbyte=serializer.validated_data['sat_per_vbyte'])).txid
            return Response({'message': f'Successfully consolidated UXTOs: {txid}', 'txid':txid})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Failed to consolidate utxos! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'}, status=400)

@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def update_alias(request):
    serializer = UpdateAliasSerializer(data=request.data)
    if serializer.is_valid():
        peer_pubkey = serializer.validated_data['peer_pubkey']
        if Channels.objects.filter(remote_pubkey=peer_pubkey).exists():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
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
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def get_info(request):
    try:
        stub = lnrpc.LightningStub(lnd_connect())
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
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def api_balances(request):
    try:
        stub = lnrpc.LightningStub(lnd_connect())
        balances = stub.WalletBalance(ln.WalletBalanceRequest())
        pending_channels = stub.PendingChannels(ln.PendingChannelsRequest())
        limbo_balance = pending_channels.total_limbo_balance
        pending_open_balance = 0
        if pending_channels.pending_open_channels:
            target_resp = pending_channels.pending_open_channels
            for i in range(0,len(target_resp)):
                pending_open_balance += target_resp[i].channel.local_balance
        channels = Channels.objects.filter(is_open=1)
        offchain_balance = channels.aggregate(Sum('local_balance'))['local_balance__sum'] + channels.aggregate(Sum('pending_outbound'))['pending_outbound__sum'] + pending_open_balance + limbo_balance
        target = {'total_balance':(balances.total_balance + offchain_balance),'offchain_balance':offchain_balance,'onchain_balance':balances.total_balance, 'confirmed_balance':balances.confirmed_balance, 'unconfirmed_balance':balances.unconfirmed_balance}
        return Response({'message': 'success', 'data':target})
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_error_index = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_error_index]
        return Response({'error': 'Failed to get wallet balances! Error: ' + error_msg})

@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def api_income(request):
    try:
        stub = lnrpc.LightningStub(lnd_connect())
        try:
            days = int(request.GET.urlencode()[1:])
        except:
            days = None
        day_filter = datetime.now() - timedelta(days=days) if days else None
        node_info = stub.GetInfo(ln.GetInfoRequest())
        payments = Payments.objects.filter(status=2).filter(creation_date__gte=day_filter) if day_filter else Payments.objects.filter(status=2)
        onchain_txs = Onchain.objects.filter(time_stamp__gte=day_filter) if day_filter else Onchain.objects.all()
        closures = Closures.objects.filter(close_height__gte=(node_info.block_height - (days*144))) if days else Closures.objects.all()
        forwards = Forwards.objects.filter(forward_date__gte=day_filter) if day_filter else Forwards.objects.all()
        forward_count = forwards.count()
        forward_amount = 0 if forward_count == 0 else int(forwards.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        total_revenue = 0 if forward_count == 0 else int(forwards.aggregate(Sum('fee'))['fee__sum'])
        invoices = Invoices.objects.filter(state=1, is_revenue=True).filter(settle_date__gte=day_filter) if day_filter else Invoices.objects.filter(state=1, is_revenue=True)
        total_received = 0 if invoices.count() == 0 else int(invoices.aggregate(Sum('amt_paid'))['amt_paid__sum'])
        total_revenue += total_received
        total_revenue_ppm = 0 if forward_amount == 0 else int(total_revenue/(forward_amount/1000000))
        total_sent = 0 if payments.count() == 0 else int(payments.aggregate(Sum('value'))['value__sum'])
        total_fees = 0 if payments.count() == 0 else int(payments.aggregate(Sum('fee'))['fee__sum'])
        total_fees_ppm = 0 if total_sent == 0 else int(total_fees/(total_sent/1000000))
        onchain_costs = 0 if onchain_txs.count() == 0 else onchain_txs.aggregate(Sum('fee'))['fee__sum']
        close_fees = closures.aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures.exists() else 0
        onchain_costs += close_fees
        profits = int(total_revenue-total_fees-onchain_costs)
        target = {
            'forward_count': forward_count,
            'forward_amount': forward_amount,
            'total_revenue': total_revenue,
            'total_revenue_ppm': total_revenue_ppm,
            'total_fees': total_fees,
            'total_fees_ppm': total_fees_ppm,
            'onchain_costs': onchain_costs,
            'profits': profits,
            'profits_ppm': 0 if forward_amount == 0  else int(profits/(forward_amount/1000000)),
            'percent_cost': 0 if total_revenue == 0 else int(((total_fees+onchain_costs)/total_revenue)*100),
        }
        return Response({'message': 'success', 'data':target})
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_error_index = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_error_index]
        return Response({'error': 'Failed to get revenue stats! Error: ' + error_msg})

@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def pending_channels(request):
    try:
        stub = lnrpc.LightningStub(lnd_connect())
        response = stub.PendingChannels(ln.PendingChannelsRequest())
        if response.pending_open_channels or response.pending_closing_channels or response.pending_force_closing_channels or response.waiting_close_channels or response.total_limbo_balance:
            target = {}
            if response.pending_open_channels:
                target_resp = response.pending_open_channels
                peers = Peers.objects.all()
                pending_open_channels = []
                for i in range(0,len(target_resp)):
                    pending_item = {'alias':peers.filter(pubkey=target_resp[i].channel.remote_node_pub)[0].alias if peers.filter(pubkey=target_resp[i].channel.remote_node_pub).exists() else None,
                    'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
                    'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'commit_fee':target_resp[i].commit_fee,'commit_weight':target_resp[i].commit_weight,'fee_per_kw':target_resp[i].fee_per_kw}
                    pending_open_channels.append(pending_item)
                target.update({'pending_open': pending_open_channels})
            if response.pending_closing_channels:
                target_resp = response.pending_closing_channels
                pending_closing_channels = []
                for i in range(0,len(target_resp)):
                    pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
                    'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'limbo_balance':target_resp[i].limbo_balance}
                    pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
                    pending_closing_channels.append(pending_item)
                target.update({'pending_closing':pending_closing_channels})
            if response.pending_force_closing_channels:
                target_resp = response.pending_force_closing_channels
                pending_force_closing_channels = []
                for i in range(0,len(target_resp)):
                    pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'initiator':target_resp[i].channel.initiator,
                    'commitment_type':target_resp[i].channel.commitment_type,'closing_txid':target_resp[i].closing_txid,'limbo_balance':target_resp[i].limbo_balance,'maturity_height':target_resp[i].maturity_height,'blocks_til_maturity':target_resp[i].blocks_til_maturity,'maturity_datetime':(datetime.now()+timedelta(minutes=(10*target_resp[i].blocks_til_maturity)))}
                    pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
                    pending_force_closing_channels.append(pending_item)
                target.update({'pending_force_closing':pending_force_closing_channels})
            if response.waiting_close_channels:
                target_resp = response.waiting_close_channels
                waiting_close_channels = []
                for i in range(0,len(target_resp)):
                    pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
                    'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'limbo_balance':target_resp[i].limbo_balance}
                    pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
                    waiting_close_channels.append(pending_item)
                target.update({'waiting_close':waiting_close_channels})
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

@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def bump_fee(request):
    serializer = BumpFeeSerializer(data=request.data)
    if serializer.is_valid():
        txid = serializer.validated_data['txid']
        index = serializer.validated_data['index']
        target_fee = serializer.validated_data['target_fee']
        force = serializer.validated_data['force']
        try:
            target_outpoint = ln.OutPoint()
            target_outpoint.txid_str = txid
            target_outpoint.output_index = index
            stub = walletstub.WalletKitStub(lnd_connect())
            stub.BumpFee(walletrpc.BumpFeeRequest(outpoint=target_outpoint, sat_per_vbyte=target_fee, force=force))
            return Response({'message': f'Fee bumped to {target_fee} sats/vbyte for outpoint: {txid}:{index}'})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': f'Fee bump failed! Error: {error_msg}'})
    else:
        return Response({'error': 'Invalid request!'})

@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def chan_policy(request):
    serializer = UpdateChanPolicy(data=request.data)
    if serializer.is_valid() and Channels.objects.filter(chan_id=serializer.validated_data['chan_id']).exists():
        chan_id = serializer.validated_data['chan_id']
        db_channel = Channels.objects.get(chan_id=chan_id)
        channel_point = point(db_channel)
        return_response = {}
        try:
            if serializer.validated_data['base_fee'] is not None or serializer.validated_data['fee_rate'] is not None or serializer.validated_data['cltv'] is not None or serializer.validated_data['min_htlc'] is not None or serializer.validated_data['max_htlc'] is not None or serializer.validated_data['inbound_base_fee'] is not None or serializer.validated_data['inbound_fee_rate'] is not None:
                base_fee_msat = serializer.validated_data['base_fee'] if serializer.validated_data['base_fee'] is not None else db_channel.local_base_fee
                fee_rate = (serializer.validated_data['fee_rate']/1000000) if serializer.validated_data['fee_rate'] is not None else (db_channel.local_fee_rate/1000000)
                inbound_base_fee_msat = serializer.validated_data['inbound_base_fee'] if serializer.validated_data['inbound_base_fee'] is not None else db_channel.local_inbound_base_fee
                inbound_fee_rate = serializer.validated_data['inbound_fee_rate'] if serializer.validated_data['inbound_fee_rate'] is not None else db_channel.local_inbound_fee_rate
                time_lock_delta = serializer.validated_data['cltv'] if serializer.validated_data['cltv'] is not None else db_channel.local_cltv
                min_htlc_msat = int(serializer.validated_data['min_htlc']*1000) if serializer.validated_data['min_htlc'] is not None else db_channel.local_min_htlc_msat
                max_htlc_msat = int(serializer.validated_data['max_htlc']*1000) if serializer.validated_data['max_htlc'] is not None else db_channel.local_max_htlc_msat
                stub = lnrpc.LightningStub(lnd_connect())
                version = stub.GetInfo(ln.GetInfoRequest()).version
                kwargs = {'chan_point':channel_point, 'base_fee_msat':base_fee_msat, 'fee_rate':fee_rate, 'time_lock_delta':time_lock_delta, 'min_htlc_msat_specified':True, 'min_htlc_msat':min_htlc_msat, 'max_htlc_msat':max_htlc_msat}
                if serializer.validated_data['inbound_base_fee'] or serializer.validated_data['inbound_fee_rate']:
                    if float(version[:4]) >= 0.18:
                        kwargs['inbound_fee'] = ln.InboundFee(base_fee_msat = inbound_base_fee_msat if inbound_base_fee_msat else 0, fee_rate_ppm = inbound_fee_rate if inbound_fee_rate else 0)
                    else:
                        return Response({'error': f'LND version too low to set inbound fees, update to v0.18+'})
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(**kwargs))
                if serializer.validated_data['base_fee'] is not None:
                    db_channel.local_base_fee = serializer.validated_data['base_fee']
                    db_channel.save()
                    return_response['base_fee'] = serializer.validated_data['base_fee']
                if serializer.validated_data['fee_rate'] is not None:
                    old_fee_rate = db_channel.local_fee_rate
                    db_channel.local_fee_rate = serializer.validated_data['fee_rate']
                    db_channel.fees_updated = datetime.now()
                    db_channel.save()
                    return_response['fee_rate'] = serializer.validated_data['fee_rate']
                    Autofees(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, setting=(f"Manual"), old_value=old_fee_rate, new_value=db_channel.local_fee_rate).save()
                if serializer.validated_data['inbound_base_fee'] is not None:
                    db_channel.local_inbound_base_fee = serializer.validated_data['inbound_base_fee']
                    db_channel.save()
                    return_response['inbound_base_fee'] = serializer.validated_data['inbound_base_fee']
                if serializer.validated_data['inbound_fee_rate'] is not None:
                    db_channel.local_inbound_fee_rate = serializer.validated_data['inbound_fee_rate']
                    db_channel.save()
                    return_response['inbound_fee_rate'] = serializer.validated_data['inbound_fee_rate']
                if serializer.validated_data['cltv'] is not None:
                    db_channel.local_cltv = serializer.validated_data['cltv']
                    db_channel.save()
                    return_response['cltv'] = serializer.validated_data['cltv']
                if serializer.validated_data['min_htlc'] is not None:
                    db_channel.local_min_htlc_msat = int(serializer.validated_data['min_htlc']*1000)
                    db_channel.save()
                    return_response['min_htlc'] = serializer.validated_data['min_htlc']
                if serializer.validated_data['max_htlc'] is not None:
                    db_channel.local_max_htlc_msat = int(serializer.validated_data['max_htlc']*1000)
                    db_channel.save()
                    return_response['max_htlc'] = serializer.validated_data['max_htlc']
            if serializer.validated_data['disabled'] is not None:
                stub = lnrouter.RouterStub(lnd_connect())
                stub.UpdateChanStatus(lnr.UpdateChanStatusRequest(chan_point=channel_point, action=0)) if serializer.validated_data['disabled'] == 0 else stub.UpdateChanStatus(lnr.UpdateChanStatusRequest(chan_point=channel_point, action=1))
                db_channel.local_disabled = False if serializer.validated_data['disabled'] == 0 else True
                db_channel.save()
                return_response['disabled'] = serializer.validated_data['base_fee']
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': f'Channel policy update failed! Error: {error_msg}'})
        return Response(return_response)
    else:
        return Response({'error': 'Invalid request!'})

@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def broadcast_tx(request):
    serializer = BroadcastTXSerializer(data=request.data)
    if serializer.is_valid():
        raw_tx = serializer.validated_data['raw_tx']
        try:
            stub = walletstub.WalletKitStub(lnd_connect())
            response = stub.PublishTransaction(walletrpc.Transaction(tx_hex=bytes.fromhex(raw_tx)))
            if response.publish_error == '':
                return Response({'message': f'Successfully broadcast tx!'})
            else:
                return Response({'error': f'Error while broadcasting TX: {response.publish_error}'})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': f'TX broadcast failed! Error: {error_msg}'})
    else:
        return Response({'error': 'Invalid request!'})

@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def create_trade(request):
    serializer = CreateTradeSerializer(data=request.data)
    if serializer.is_valid():
        description = serializer.validated_data['description']
        price = serializer.validated_data['price']
        sale_type = serializer.validated_data['type']
        secret = serializer.validated_data['secret']
        expiry = serializer.validated_data['expiry']
        sale_limit = serializer.validated_data['sale_limit']
        trade_id = token_bytes(32).hex()
        try:
            new_trade = TradeSales(id=trade_id, description=description, price=price, secret=secret, expiry=expiry, sale_type=sale_type, sale_limit=sale_limit)
            new_trade.save()
            return Response({'message': f'Created trade: {description}', 'id': new_trade.id, 'description': new_trade.description, 'price': new_trade.price, 'expiry': new_trade.expiry, 'sale_type': new_trade.sale_type, 'secret': new_trade.secret, 'sale_count': new_trade.sale_count, 'sale_limit': new_trade.sale_limit})
        except Exception as e:
            error = str(e)
            return Response({'error': f'Error creating trade: {error}'})
    else:
        return Response({'error': serializer.error_messages})

@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def reset_api(request):
    serializer = ResetSerializer(data=request.data)
    if serializer.is_valid():
        table = serializer.validated_data['table']
        tables = {
            'Forwards': Forwards.objects.all(),
            'Payments': Payments.objects.all(),
            'PaymentHops': PaymentHops.objects.all(),
            'Invoices': Invoices.objects.all(),
            'Rebalancer': Rebalancer.objects.all(),
            'Closures': Closures.objects.all(),
            'Resolutions': Resolutions.objects.all(),
            'Peers': Peers.objects.all(),
            'Channels': Channels.objects.all(),
            'PendingChannels': PendingChannels.objects.all(),
            'Onchain': Onchain.objects.all(),
            'PendingHTLCs': PendingHTLCs.objects.all(),
            'FailedHTLCs': FailedHTLCs.objects.all(),
            'HistFailedHTLC': HistFailedHTLC.objects.all(),
            'Autopilot': Autopilot.objects.all(),
            'Autofees': Autofees.objects.all(),
            'AvoidNodes': AvoidNodes.objects.all(),
            'PeerEvents': PeerEvents.objects.all(),
            'LocalSettings': LocalSettings.objects.all()
        }
        try:
            target_table = tables[table]
            target_table.delete()
            return Response({'message': f'Successfully deleted table: {table}'})
        except Exception as e:
            error = str(e)
            return Response({'error': f'Error deleting table: {error}'})
    else:
        return Response({'error': serializer.error_messages})

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def peer_offline_report(request):
    # Timeframe is now fixed to Month to Date
    # timeframe_options = {'MTD': 'Month to Date'} # No longer needed for a dropdown
    # selected_timeframe = 'MTD' # Implied
    
    alias_filter_query = request.GET.get('alias', '').strip()
    sort_by_query = request.GET.get('sort', '-total_offline_hours') 

    now = timezone.now()
    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    peer_stats_list = []

    open_channels = Channels.objects.filter(is_open=True)
    if alias_filter_query:
        open_channels = open_channels.filter(alias__icontains=alias_filter_query)

    for channel in open_channels:
        events = PeerEvents.objects.filter(
            chan_id=channel.chan_id,
            event='Connection',
            timestamp__gte=start_date
        ).order_by('timestamp')

        if not events.exists() and not (alias_filter_query and channel.alias.lower().__contains__(alias_filter_query.lower())):
            # Skip if no events and not specifically filtered for this alias (to show 0s)
            continue

        total_offline_duration_seconds = 0
        offline_instance_count = 0
        current_offline_start_time = None

        for i, event in enumerate(events):
            if event.new_value == 0:
                if current_offline_start_time is None:
                    current_offline_start_time = event.timestamp
                    offline_instance_count += 1
            elif event.new_value == 1:
                if current_offline_start_time is not None:
                    duration = event.timestamp - current_offline_start_time
                    total_offline_duration_seconds += duration.total_seconds()
                    current_offline_start_time = None

        if current_offline_start_time is not None:
            if not channel.is_active:
                duration = now - current_offline_start_time
                total_offline_duration_seconds += duration.total_seconds()

        current_peer_stats = {
            'chan_id': channel.chan_id,
            'channel_alias': channel.alias,
            'avg_offline_hours': 0,
            'total_offline_hours': 0,
            'offline_count': 0,
            'currently_offline': not channel.is_active,
        }

        if offline_instance_count > 0:
            avg_offline_hours = (total_offline_duration_seconds / offline_instance_count / 3600.0)
            sum_offline_hours = total_offline_duration_seconds / 3600.0
            current_peer_stats['avg_offline_hours'] = round(avg_offline_hours, 2)
            current_peer_stats['total_offline_hours'] = round(sum_offline_hours, 2)
            current_peer_stats['offline_count'] = offline_instance_count
        
        # Add to list if it had offline events OR if it was specifically filtered by alias (to show 0s)
        if offline_instance_count > 0 or (alias_filter_query and channel.alias.lower().__contains__(alias_filter_query.lower())):
            peer_stats_list.append(current_peer_stats)


    # Python-side sorting for initial load / if JS is disabled / if alias filter is used
    reverse_sort = sort_by_query.startswith('-')
    # Use the part after '-' as the key, ensure it matches dict keys
    sort_key = sort_by_query.lstrip('-') 
    
    def sort_helper(item):
        val = item.get(sort_key)
        if isinstance(val, bool):
            return (val is False, val) if reverse_sort else (val is True, val) 
        if isinstance(val, (int, float)):
            return val
        if val is None:
            return float('-inf') if not reverse_sort else float('inf') 
        return str(val).lower()

    peer_stats_list.sort(key=sort_helper, reverse=reverse_sort)

    context = {
        'peer_stats': peer_stats_list,
        'alias_filter_query': alias_filter_query,
        'page_title': 'Peer Offline Report (Month to Date)', # Updated title
        'active_menu': 'peer_offline_report',
    }
    return render(request, 'peer_offline_report.html', context)