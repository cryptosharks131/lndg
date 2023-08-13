import django
from django.db.models import Sum
from datetime import datetime, timedelta
from os import environ
from pandas import DataFrame, concat
environ['DJANGO_SETTINGS_MODULE'] = 'lndg.settings'
django.setup()
from gui.models import Forwards, Channels, Groups, Settings, FailedHTLCs

def main(group: Groups, chan_id=''):
    if len(chan_id) > 0:
        channels_df = DataFrame.from_records(group.channels.filter(chan_id=chan_id).values())
    else:
        channels_df = DataFrame.from_records(group.channels.filter(is_open=True, private=False).values())
        
    filter_1day = datetime.now() - timedelta(days=1)
    filter_7day = datetime.now() - timedelta(days=7)
    if channels_df.shape[0] > 0:
        max_rate = int(group.settings_set.filter(key='AF-MaxRate')[0].value if group.settings_set.filter(key='AF-MaxRate').exists() else Settings.objects.filter(group_id=0,key='AF-MaxRate')[0].value)
        min_rate = int(group.settings_set.filter(key='AF-MinRate')[0].value if group.settings_set.filter(key='AF-MinRate').exists() else Settings.objects.filter(group_id=0,key='AF-MinRate')[0].value)
        increment = int(group.settings_set.filter(key='AF-Increment')[0].value if group.settings_set.filter(key='AF-Increment').exists() else Settings.objects.filter(group_id=0,key='AF-Increment')[0].value)
        multiplier = int(group.settings_set.filter(key='AF-Multiplier')[0].value if group.settings_set.filter(key='AF-Multiplier').exists() else Settings.objects.filter(group_id=0,key='AF-Multiplier')[0].value)
        failed_htlc_limit = int(group.settings_set.filter(key='AF-FailedHTLCs')[0].value if group.settings_set.filter(key='AF-FailedHTLCs').exists() else Settings.objects.filter(group_id=0,key='AF-FailedHTLCs')[0].value)
        update_hours = int(group.settings_set.filter(key='AF-UpdateHours').get().value if group.settings_set.filter(key='AF-UpdateHours').exists() else Settings.objects.filter(group_id=0,key='AF-UpdateHours')[0].value)
        lowliq_limit = int(group.settings_set.filter(key='AF-LowLiqLimit').get().value if group.settings_set.filter(key='AF-LowLiqLimit').exists() else Settings.objects.filter(group_id=0,key='AF-LowLiqLimit')[0].value)
        excess_limit = int(group.settings_set.filter(key='AF-ExcessLimit').get().value if group.settings_set.filter(key='AF-ExcessLimit').exists() else Settings.objects.filter(group_id=0,key='AF-ExcessLimit')[0].value)

        if lowliq_limit >= excess_limit:
            print('Invalid thresholds detected, using defaults...')
            lowliq_limit = 5
            excess_limit = 95
        forwards = Forwards.objects.filter(forward_date__gte=filter_7day, amt_out_msat__gte=1000000)
        forwards_1d = forwards.filter(forward_date__gte=filter_1day)
        if forwards_1d.exists():
            forwards_df_in_1d_sum = DataFrame.from_records(forwards_1d.values('chan_id_in').annotate(amt_out_msat=Sum('amt_out_msat'), fee=Sum('fee')), 'chan_id_in')
            if forwards.exists():
                forwards_df_in_7d_sum = DataFrame.from_records(forwards.values('chan_id_in').annotate(amt_out_msat=Sum('amt_out_msat'), fee=Sum('fee')), 'chan_id_in')
                forwards_df_out_7d_sum = DataFrame.from_records(forwards.values('chan_id_out').annotate(amt_out_msat=Sum('amt_out_msat'), fee=Sum('fee')), 'chan_id_out')
            else:
                forwards_df_in_7d_sum = DataFrame()
                forwards_df_out_7d_sum = DataFrame()
        else:
            forwards_df_in_1d_sum = DataFrame()
            forwards_df_in_7d_sum = DataFrame()
            forwards_df_out_7d_sum = DataFrame()
        channels_df['amt_routed_in_1day'] = channels_df.apply(lambda row: int(forwards_df_in_1d_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_in_1d_sum.index == row.chan_id).any() else 0, axis=1)
        channels_df['amt_routed_in_7day'] = channels_df.apply(lambda row: int(forwards_df_in_7d_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_in_7d_sum.index == row.chan_id).any() else 0, axis=1)
        channels_df['amt_routed_out_7day'] = channels_df.apply(lambda row: int(forwards_df_out_7d_sum.loc[row.chan_id].amt_out_msat/1000) if (forwards_df_out_7d_sum.index == row.chan_id).any() else 0, axis=1)
        channels_df['net_routed_7day'] = channels_df.apply(lambda row: round((row['amt_routed_out_7day']-row['amt_routed_in_7day'])/row['capacity'], 1), axis=1)
        channels_df['local_balance'] = channels_df.apply(lambda row: row.local_balance + row.pending_outbound, axis=1)
        channels_df['remote_balance'] = channels_df.apply(lambda row: row.remote_balance + row.pending_inbound, axis=1)
        channels_df['in_percent'] = channels_df.apply(lambda row: int(round((row['remote_balance']/row['capacity'])*100, 0)), axis=1)
        channels_df['out_percent'] = channels_df.apply(lambda row: int(round((row['local_balance']/row['capacity'])*100, 0)), axis=1)
        channels_df['eligible'] = channels_df.apply(lambda row: (datetime.now()-row['fees_updated']).total_seconds() > (update_hours*3600), axis=1)

        # Low Liquidity
        lowliq_df = channels_df[channels_df['out_percent'] <= lowliq_limit].copy()
        failed_htlc_df = DataFrame.from_records(FailedHTLCs.objects.exclude(wire_failure=99).filter(timestamp__gte=filter_1day).order_by('-id').values())
        if failed_htlc_df.shape[0] > 0:
            failed_htlc_df = failed_htlc_df[(failed_htlc_df['wire_failure']==15) & (failed_htlc_df['failure_detail']==6) & (failed_htlc_df['amount']>failed_htlc_df['chan_out_liq']+failed_htlc_df['chan_out_pending'])]
        lowliq_df['failed_out_1day'] = 0 if failed_htlc_df.empty else lowliq_df.apply(lambda row: len(failed_htlc_df[failed_htlc_df['chan_id_out']==row.chan_id]), axis=1)
        # INCREASE IF (failed htlc > threshhold) && (flow in == 0)
        lowliq_df['new_rate'] = lowliq_df.apply(lambda row: row['local_fee_rate']+(5*multiplier) if row['failed_out_1day']>failed_htlc_limit and row['amt_routed_in_1day'] == 0 else row['local_fee_rate'], axis=1)

        # Balanced Liquidity
        balanced_df = channels_df[(channels_df['out_percent'] > lowliq_limit) & (channels_df['out_percent'] < excess_limit)].copy()
        # IF NO FLOW THEN DECREASE FEE AND IF HIGH FLOW THEN SLOWLY INCREASE FEE
        balanced_df['new_rate'] = balanced_df.apply(lambda row: row['local_fee_rate']+((2*multiplier)*(1+(row['net_routed_7day']/row['capacity']))) if row['net_routed_7day'] > row['capacity'] else row['local_fee_rate'], axis=1)
        balanced_df['new_rate'] = balanced_df.apply(lambda row: row['local_fee_rate']-(3*multiplier) if (row['amt_routed_in_7day']+row['amt_routed_out_7day']) == 0 else row['local_fee_rate'], axis=1)

        # Excess Liquidity
        excess_df = channels_df[channels_df['out_percent'] >= excess_limit].copy()
        excess_df['revenue_7day'] = excess_df.apply(lambda row: int(forwards_df_out_7d_sum.loc[row.chan_id].fee) if forwards_df_out_7d_sum.empty == False and (forwards_df_out_7d_sum.index == row.chan_id).any() else 0, axis=1)
        excess_df['revenue_assist_7day'] = excess_df.apply(lambda row: int(forwards_df_in_7d_sum.loc[row.chan_id].fee) if forwards_df_in_7d_sum.empty == False and (forwards_df_in_7d_sum.index == row.chan_id).any() else 0, axis=1)
        # DECREASE IF (assisting channel or stagnant liq)
        excess_df['new_rate'] = excess_df.apply(lambda row: row['local_fee_rate']-(5*multiplier) if row['net_routed_7day'] < 0 and row['revenue_assist_7day'] > (row['revenue_7day']*10) else row['local_fee_rate'], axis=1)
        excess_df['new_rate'] = excess_df.apply(lambda row: row['local_fee_rate']-(5*multiplier) if (row['amt_routed_in_7day']+row['amt_routed_out_7day']) == 0 else row['local_fee_rate'], axis=1)

        #Merge back results
        result_df = concat([lowliq_df, balanced_df, excess_df])
        result_df['new_rate'] = result_df.apply(lambda row: int(round(row['new_rate']/increment, 0)*increment), axis=1)
        result_df['new_rate'] = result_df.apply(lambda row: max_rate if max_rate < row['new_rate'] else row['new_rate'], axis=1)
        result_df['new_rate'] = result_df.apply(lambda row: min_rate if min_rate > row['new_rate'] else row['new_rate'], axis=1)
        result_df['adjustment'] = result_df.apply(lambda row: int(row['new_rate']-row['local_fee_rate']), axis=1)
        return result_df
    else:
        return DataFrame()


if __name__ == '__main__':
    print(main(Channels.objects.filter(is_open=True)))