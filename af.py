import django
from django.db.models import Sum
from datetime import datetime, timedelta
from os import environ
from pandas import DataFrame, Series
environ['DJANGO_SETTINGS_MODULE'] = 'lndg.settings'
django.setup()
from gui.models import Forwards, Channels, LocalSettings, FailedHTLCs

def main(channels):
    channels_df = DataFrame.from_records(channels.values())
    if channels_df.shape[0] == 0:
        return DataFrame()
    filter_1day = datetime.now() - timedelta(days=1)
    filter_7day = datetime.now() - timedelta(days=7)
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
    if LocalSettings.objects.filter(key='AF-UpdateHours').exists():
        update_hours = int(LocalSettings.objects.filter(key='AF-UpdateHours').get().value)
    else:
        LocalSettings(key='AF-UpdateHours', value='24').save()
        update_hours = 24
    if LocalSettings.objects.filter(key='AF-LowLiqLimit').exists():
        lowliq_limit = int(LocalSettings.objects.filter(key='AF-LowLiqLimit').get().value)
    else:
        LocalSettings(key='AF-LowLiqLimit', value='15').save()
        lowliq_limit = 5
    if LocalSettings.objects.filter(key='AF-ExcessLimit').exists():
        excess_limit = int(LocalSettings.objects.filter(key='AF-ExcessLimit').get().value)
    else:
        LocalSettings(key='AF-ExcessLimit', value='95').save()
        excess_limit = 95
    if lowliq_limit >= excess_limit:
        print('Invalid thresholds detected, using defaults...')
        lowliq_limit = 5
        excess_limit = 95

    # Fetch forwarding data
    forwards = Forwards.objects.filter(forward_date__gte=filter_7day, amt_out_msat__gte=1000000)
    forwards_1d = forwards.filter(forward_date__gte=filter_1day)
    
    forwards_df_in_1d_sum = DataFrame.from_records(
        forwards_1d.values('chan_id_in').annotate(amt_out_msat=Sum('amt_out_msat'), fee=Sum('fee')), 
        index='chan_id_in'
    ) if forwards_1d.exists() else DataFrame()
    
    forwards_df_in_7d_sum = DataFrame.from_records(
        forwards.values('chan_id_in').annotate(amt_out_msat=Sum('amt_out_msat'), fee=Sum('fee')), 
        index='chan_id_in'
    ) if forwards.exists() else DataFrame()
    
    forwards_df_out_7d_sum = DataFrame.from_records(
        forwards.values('chan_id_out').annotate(amt_out_msat=Sum('amt_out_msat'), fee=Sum('fee')), 
        index='chan_id_out'
    ) if forwards.exists() else DataFrame()

    # Compute per-channel metrics
    if not forwards_df_in_1d_sum.empty:
        channels_df['amt_routed_in_1day'] = channels_df['chan_id'].map(
            forwards_df_in_1d_sum['amt_out_msat'].floordiv(1000)
        ).fillna(0).astype(int)
    else:
        channels_df['amt_routed_in_1day'] = 0
    if not forwards_df_in_7d_sum.empty:
        channels_df['amt_routed_in_7day'] = channels_df['chan_id'].map(
            forwards_df_in_7d_sum['amt_out_msat'].floordiv(1000)
        ).fillna(0).astype(int)
    else:
        channels_df['amt_routed_in_7day'] = 0
    if not forwards_df_out_7d_sum.empty:
        channels_df['amt_routed_out_7day'] = channels_df['chan_id'].map(
            forwards_df_out_7d_sum['amt_out_msat'].floordiv(1000)
        ).fillna(0).astype(int)
    else:
        channels_df['amt_routed_out_7day'] = 0

    channels_df['net_routed_7day'] = (
        (channels_df['amt_routed_out_7day'] - channels_df['amt_routed_in_7day']) / channels_df['capacity']
    ).round(1)
    
    channels_df['local_balance'] = channels_df['local_balance'] + channels_df['pending_outbound']
    channels_df['remote_balance'] = channels_df['remote_balance'] + channels_df['pending_inbound']
    channels_df['out_percent'] = ((channels_df['local_balance'] / channels_df['capacity']) * 100).round(0).astype(int)
    channels_df['in_percent'] = ((channels_df['remote_balance'] / channels_df['capacity']) * 100).round(0).astype(int)
    channels_df['eligible'] = (datetime.now() - channels_df['fees_updated']).dt.total_seconds() > (update_hours * 3600)

    # Compute failed HTLCs per channel
    failed_htlc_df = DataFrame.from_records(
        FailedHTLCs.objects.filter(timestamp__gte=filter_1day, wire_failure=15, failure_detail=6).values()
    )
    if not failed_htlc_df.empty:
        failed_htlc_df = failed_htlc_df[
            failed_htlc_df['amount'] > (failed_htlc_df['chan_out_liq'] + failed_htlc_df['chan_out_pending'])
        ]
        failed_out_1day_series = failed_htlc_df['chan_id_out'].value_counts()
    else:
        failed_out_1day_series = Series(dtype='int64')
    channels_df['failed_out_1day'] = channels_df['chan_id'].map(failed_out_1day_series).fillna(0).astype(int)

    # Compute revenue metrics
    if not forwards_df_in_7d_sum.empty:
        channels_df['revenue_assist_7day'] = channels_df['chan_id'].map(
            forwards_df_in_7d_sum['fee']
        ).fillna(0).astype(float)
    else:
        channels_df['revenue_assist_7day'] = 0.0

    if not forwards_df_out_7d_sum.empty:
        channels_df['revenue_7day'] = channels_df['chan_id'].map(
            forwards_df_out_7d_sum['fee']
        ).fillna(0).astype(float)
    else:
        channels_df['revenue_7day'] = 0.0

    # Aggregate data by remote_pubkey
    group_df = channels_df.groupby('remote_pubkey').agg({
        'local_balance': 'sum',
        'capacity': 'sum',
        'failed_out_1day': 'sum',
        'amt_routed_in_1day': 'sum',
        'amt_routed_in_7day': 'sum',
        'amt_routed_out_7day': 'sum',
        'revenue_7day': 'sum',
        'revenue_assist_7day': 'sum'
    }).rename(columns={
        'local_balance': 'total_local_balance',
        'capacity': 'total_capacity',
        'failed_out_1day': 'total_failed_out_1day',
        'amt_routed_in_1day': 'total_amt_routed_in_1day',
        'amt_routed_in_7day': 'total_amt_routed_in_7day',
        'amt_routed_out_7day': 'total_amt_routed_out_7day',
        'revenue_7day': 'total_revenue_7day',
        'revenue_assist_7day': 'total_revenue_assist_7day'
    })

    group_df['overall_out_percent'] = (
        (group_df['total_local_balance'] / group_df['total_capacity']) * 100
    ).where(group_df['total_capacity'] > 0, 0)

    group_df['group_net_routed_7day'] = (
        (group_df['total_amt_routed_out_7day'] - group_df['total_amt_routed_in_7day']) / group_df['total_capacity']
    ).where(group_df['total_capacity'] > 0, 0)

    # Define outbound adjustment calculation function
    def compute_outbound_adjustment(row):
        if row['overall_out_percent'] <= lowliq_limit:
            return (5 * multiplier) if (row['total_failed_out_1day'] > failed_htlc_limit and 
                                    row['total_amt_routed_in_1day'] == 0) else 0
        elif row['overall_out_percent'] < excess_limit:
            if row['total_amt_routed_in_7day'] + row['total_amt_routed_out_7day'] == 0:
                return -3 * multiplier
            elif row['group_net_routed_7day'] > 1:
                return (2 * multiplier) * (1 + row['group_net_routed_7day'])
            else:
                return 0
        else:
            if row['total_amt_routed_in_7day'] + row['total_amt_routed_out_7day'] == 0:
                return -5 * multiplier
            elif (row['group_net_routed_7day'] < 0 and 
                row['total_revenue_assist_7day'] > row['total_revenue_7day'] * 10):
                return -5 * multiplier
            else:
                return 0

    group_df['adjustment'] = group_df.apply(compute_outbound_adjustment, axis=1)

    # Define inbound adjustment calculation function
    def compute_inbound_adjustment(row):
        if row['overall_out_percent'] <= lowliq_limit:
            return (-12 * multiplier) if (row['total_failed_out_1day'] > failed_htlc_limit and 
                                    row['total_amt_routed_in_1day'] == 0) else 0
        elif row['overall_out_percent'] < excess_limit: 
            if row['total_amt_routed_in_7day'] + row['total_amt_routed_out_7day'] == 0:
                return 7 * multiplier
            elif row['group_net_routed_7day'] > 1:
                return (-5 * multiplier) * (1 + row['group_net_routed_7day'])
            else:
                return 0
        else:
            if row['total_amt_routed_in_7day'] + row['total_amt_routed_out_7day'] == 0:
                return 12 * multiplier
            elif (row['group_net_routed_7day'] < 0 and 
                row['total_revenue_assist_7day'] > row['total_revenue_7day'] * 10):
                return 12 * multiplier
            else:
                return 0

    group_df['inbound_adjustment'] = group_df.apply(compute_inbound_adjustment, axis=1)

    # Merge adjustments back to channels_df
    channels_df = channels_df.merge(group_df[['adjustment']], on='remote_pubkey', how='left')
    channels_df = channels_df.merge(group_df[['inbound_adjustment']], on='remote_pubkey', how='left')

    # Compute new outbound rates
    channels_df['new_rate'] = channels_df['local_fee_rate'] + channels_df['adjustment']
    channels_df['new_rate'] = (channels_df['new_rate'] / increment).round(0) * increment
    channels_df['new_rate'] = channels_df['new_rate'].clip(min_rate, max_rate)
    channels_df['adjustment'] = channels_df['new_rate'] - channels_df['local_fee_rate']

    # Compute new inbound rates
    channels_df['new_inbound_rate'] = channels_df['local_inbound_fee_rate'] + channels_df['inbound_adjustment']
    channels_df['new_inbound_rate'] = (channels_df['new_inbound_rate'] / increment).round(0) * increment
    channels_df['new_inbound_rate'] = channels_df['new_inbound_rate'].clip(-((channels_df['ar_max_cost']/100)*channels_df['local_fee_rate']), 0)
    channels_df['inbound_adjustment'] = channels_df['new_inbound_rate'] - channels_df['local_inbound_fee_rate']

    # Return results
    return channels_df


if __name__ == '__main__':
    print(main(Channels.objects.filter(is_open=True))[['chan_id', 'local_fee_rate', 'new_rate', 'adjustment', 'local_inbound_fee_rate', 'new_inbound_rate', 'inbound_adjustment']])