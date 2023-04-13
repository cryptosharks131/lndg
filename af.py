import django, time
from django.db.models import Sum
from datetime import datetime, timedelta
from os import environ
from pandas import DataFrame
environ['DJANGO_SETTINGS_MODULE'] = 'lndg.settings'
django.setup()
from gui.models import Payments, Invoices, Forwards, Channels, LocalSettings, FailedHTLCs

def main():
    start = time.time()
    channels = Channels.objects.filter(is_open=True, is_active=True, private=False, auto_fees=True)
    channels_df = DataFrame.from_records(channels.values())
    filter_1day = datetime.now() - timedelta(days=1)
    filter_7day = datetime.now() - timedelta(days=7)
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
        if LocalSettings.objects.filter(key='AF-UpdateHours').exists():
            update_hours = int(LocalSettings.objects.filter(key='AF-UpdateHours')[0].value)
        else:
            LocalSettings(key='AF-UpdateHours', value='24').save()
            update_hours = 24
        channels_df['eligible'] = channels_df.apply(lambda row: (datetime.now()-row['fees_updated']).total_seconds() > (update_hours*3600), axis=1)
        failed_htlc_df = DataFrame.from_records(FailedHTLCs.objects.exclude(wire_failure=99).filter(timestamp__gte=filter_1day).order_by('-id').values())
        if failed_htlc_df.shape[0] > 0:
            failed_htlc_df = failed_htlc_df[(failed_htlc_df['wire_failure']==15) & (failed_htlc_df['failure_detail']==6) & (failed_htlc_df['amount']>failed_htlc_df['chan_out_liq']+failed_htlc_df['chan_out_pending'])]
        forwards = Forwards.objects.filter(forward_date__gte=filter_7day, amt_out_msat__gte=1000000)
        if forwards.exists():
            forwards_df_in_7d_sum = DataFrame.from_records(forwards.values('chan_id_in').annotate(amt_out_msat=Sum('amt_out_msat'), fee=Sum('fee')), 'chan_id_in')
            forwards_df_out_7d_sum = DataFrame.from_records(forwards.values('chan_id_out').annotate(amt_out_msat=Sum('amt_out_msat'), fee=Sum('fee')), 'chan_id_out')
        else:
            forwards_df_in_7d_sum = DataFrame()
            forwards_df_out_7d_sum = DataFrame()
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
        invoices = Invoices.objects.filter(state=1).filter(r_hash__in=payments.values_list('payment_hash'))
        payments_df_7d_sum = DataFrame() if not payments.exists() else DataFrame.from_records(payments.values('rebal_chan').annotate(fee=Sum('fee')), 'rebal_chan')
        invoices_df_7d_sum = DataFrame() if not invoices.exists() else DataFrame.from_records(payments.values('chan_in').annotate(amt_paid=Sum('amt_paid')), 'chan_in')
        channels_df['amt_rebal_in_7day'] = channels_df.apply(lambda row: int(invoices_df_7d_sum.loc[row.chan_id].amt_paid) if invoices_df_7d_sum.empty == False and (invoices_df_7d_sum.index == row.chan_id).any() else 0, axis=1)
        channels_df['costs_7day'] = channels_df.apply(lambda row: 0 if row['amt_rebal_in_7day'] == 0 else (int(payments_df_7d_sum.loc[row.chan_id]['fee']) if payments_df_7d_sum.empty == False and (payments_df_7d_sum.index == row.chan_id).any() else 0), axis=1)
        channels_df['rebal_ppm'] = channels_df.apply(lambda row: int((row['costs_7day']/row['amt_rebal_in_7day'])*1000000) if row['amt_rebal_in_7day'] > 0 else 0, axis=1)
        channels_df['profit_margin'] = channels_df.apply(lambda row: row['out_rate']*((100-row['ar_max_cost'])/100), axis=1)
        channels_df['full'] = channels_df.apply(lambda row: 1 if row['out_percent'] >= 80 else 0, axis=1)
        channels_df['depleted'] = channels_df.apply(lambda row: 1 if row['out_percent'] <= 20 else 0, axis=1)
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
        update_df = channels_df[channels_df['adjustment']!=0]
        print(update_df)
        print('Time taken:', str(round(time.time()-start,3))+'s')

if __name__ == '__main__':
    main()