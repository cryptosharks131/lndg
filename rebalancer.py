import django, json, datetime
from django.db.models import Sum, F
from datetime import datetime, timedelta
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps.lnd_connect import lnd_connect
from lndg import settings
from os import environ
environ['DJANGO_SETTINGS_MODULE'] = 'lndg.settings'
django.setup()
from gui.models import Rebalancer, Channels, LocalSettings, Forwards, Autopilot

def run_rebalancer(rebalance):
    if Rebalancer.objects.filter(status=1).exists():
        unknown_errors = Rebalancer.objects.filter(status=1)
        for unknown_error in unknown_errors:
            unknown_error.status = 400
            unknown_error.stop = datetime.now()
            unknown_error.save()
    auto_rebalance_channels = Channels.objects.filter(is_active=True, is_open=True, private=False).annotate(percent_outbound=((Sum('local_balance')+Sum('pending_outbound'))*100)/Sum('capacity')).annotate(inbound_can=(((Sum('remote_balance')+Sum('pending_inbound'))*100)/Sum('capacity'))/Sum('ar_in_target'))
    outbound_cans = list(auto_rebalance_channels.filter(auto_rebalance=False, percent_outbound__gte=F('ar_out_target')).values_list('chan_id', flat=True))
    if len(outbound_cans) == 0:
        return None
    elif str(outbound_cans).replace('\'', '') != rebalance.outgoing_chan_ids:
        rebalance.outgoing_chan_ids = str(outbound_cans).replace('\'', '')
    rebalance.start = datetime.now()
    try:
        #Open connection with lnd via grpc
        connection = lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER)
        stub = lnrpc.LightningStub(connection)
        routerstub = lnrouter.RouterStub(connection)
        chan_ids = json.loads(rebalance.outgoing_chan_ids)
        timeout = rebalance.duration * 60
        invoice_response = stub.AddInvoice(ln.Invoice(value=rebalance.value, expiry=timeout))
        for payment_response in routerstub.SendPaymentV2(lnr.SendPaymentRequest(payment_request=str(invoice_response.payment_request), fee_limit_sat=rebalance.fee_limit, outgoing_chan_ids=chan_ids, last_hop_pubkey=bytes.fromhex(rebalance.last_hop_pubkey), timeout_seconds=(timeout-5), allow_self_payment=True), timeout=(timeout+60)):
            if payment_response.status == 1 and rebalance.status == 0:
                #IN-FLIGHT
                rebalance.payment_hash = payment_response.payment_hash
                rebalance.status = 1
                rebalance.save()
            elif payment_response.status == 2:
                #SUCCESSFUL
                rebalance.status = 2
                successful_out = payment_response.htlcs[0].route.hops[0].pub_key
            elif payment_response.status == 3:
                #FAILURE
                if payment_response.failure_reason == 1:
                    #FAILURE_REASON_TIMEOUT
                    rebalance.status = 3
                elif payment_response.failure_reason == 2:
                    #FAILURE_REASON_NO_ROUTE
                    rebalance.status = 4
                elif payment_response.failure_reason == 3:
                    #FAILURE_REASON_ERROR
                    rebalance.status = 5
                elif payment_response.failure_reason == 4:
                    #FAILURE_REASON_INCORRECT_PAYMENT_DETAILS
                    rebalance.status = 6
                elif payment_response.failure_reason == 5:
                    #FAILURE_REASON_INSUFFICIENT_BALANCE
                    rebalance.status = 7
            elif payment_response.status == 0:
                rebalance.status = 400
    except Exception as e:
        if str(e.code()) == 'StatusCode.DEADLINE_EXCEEDED':
            rebalance.status = 408
        else:
            rebalance.status = 400
            error = str(e)
            print(error)
    finally:
        rebalance.stop = datetime.now()
        rebalance.save()
        if rebalance.status == 2:
            update_channels(stub, rebalance.last_hop_pubkey, successful_out)
            auto_rebalance_channels = Channels.objects.filter(is_active=True, is_open=True, private=False).annotate(percent_outbound=((Sum('local_balance')+Sum('pending_outbound'))*100)/Sum('capacity')).annotate(inbound_can=(((Sum('remote_balance')+Sum('pending_inbound'))*100)/Sum('capacity'))/Sum('ar_in_target'))
            inbound_cans = auto_rebalance_channels.filter(remote_pubkey=rebalance.last_hop_pubkey).filter(auto_rebalance=True, inbound_can__gte=1)
            outbound_cans = list(auto_rebalance_channels.filter(auto_rebalance=False, percent_outbound__gte=F('ar_out_target')).values_list('chan_id', flat=True))
            if len(inbound_cans) > 0 and len(outbound_cans) > 0:
                next_rebalance = Rebalancer(value=rebalance.value, fee_limit=rebalance.fee_limit, outgoing_chan_ids=str(outbound_cans).replace('\'', ''), last_hop_pubkey=rebalance.last_hop_pubkey, target_alias=rebalance.target_alias, duration=1)
                next_rebalance.save()
            else:
                next_rebalance = None
        else:
            next_rebalance = None
        return next_rebalance

def update_channels(stub, incoming_channel, outgoing_channel):
    # Incoming channel update
    channel = stub.ListChannels(ln.ListChannelsRequest(peer=bytes.fromhex(incoming_channel))).channels[0]
    db_channel = Channels.objects.filter(chan_id=channel.chan_id)[0]
    db_channel.local_balance = channel.local_balance
    db_channel.remote_balance = channel.remote_balance
    db_channel.save()
    # Outgoing channel update
    channel = stub.ListChannels(ln.ListChannelsRequest(peer=bytes.fromhex(outgoing_channel))).channels[0]
    db_channel = Channels.objects.filter(chan_id=channel.chan_id)[0]
    db_channel.local_balance = channel.local_balance
    db_channel.remote_balance = channel.remote_balance
    db_channel.save()

def auto_schedule():
    #No rebalancer jobs have been scheduled, lets look for any channels with an auto_rebalance flag and make the best request if we find one
    if LocalSettings.objects.filter(key='AR-Enabled').exists():
        enabled = int(LocalSettings.objects.filter(key='AR-Enabled')[0].value)
    else:
        LocalSettings(key='AR-Enabled', value='0').save()
        enabled = 0
    if enabled == 1:
        auto_rebalance_channels = Channels.objects.filter(is_active=True, is_open=True, private=False).annotate(percent_outbound=((Sum('local_balance')+Sum('pending_outbound'))*100)/Sum('capacity')).annotate(inbound_can=(((Sum('remote_balance')+Sum('pending_inbound'))*100)/Sum('capacity'))/Sum('ar_in_target'))
        if len(auto_rebalance_channels) > 0:
            if not LocalSettings.objects.filter(key='AR-Outbound%').exists():
                LocalSettings(key='AR-Outbound%', value='0.75').save()
            outbound_cans = list(auto_rebalance_channels.filter(auto_rebalance=False, percent_outbound__gte=F('ar_out_target')).values_list('chan_id', flat=True))
            inbound_cans = auto_rebalance_channels.filter(auto_rebalance=True, inbound_can__gte=1)
            if len(inbound_cans) > 0 and len(outbound_cans) > 0:
                if LocalSettings.objects.filter(key='AR-MaxFeeRate').exists():
                    max_fee_rate = int(LocalSettings.objects.filter(key='AR-MaxFeeRate')[0].value)
                else:
                    LocalSettings(key='AR-MaxFeeRate', value='100').save()
                    max_fee_rate = 100
                if not LocalSettings.objects.filter(key='AR-Target%').exists():
                    LocalSettings(key='AR-Target%', value='0.05').save()
                if not LocalSettings.objects.filter(key='AR-MaxCost%').exists():
                    LocalSettings(key='AR-MaxCost%', value='0.65').save()
                # TLDR: lets target a custom % of the amount that would bring us back to a 50/50 channel balance using the MaxFeerate to calculate sat fee intervals
                for target in inbound_cans:
                    target_fee_rate = int(target.local_fee_rate * (target.ar_max_cost/100))
                    if target_fee_rate > 0 and target_fee_rate > target.remote_fee_rate:
                        value_per_fee = int(1 / (target_fee_rate / 1000000)) if target_fee_rate <= max_fee_rate else int(1 / (max_fee_rate / 1000000))
                        target_value = int(target.ar_amt_target / value_per_fee) * value_per_fee
                        target_fee = int(target_value * (1 / value_per_fee))
                        if target_value >= value_per_fee and target_fee > 0:
                            if LocalSettings.objects.filter(key='AR-Time').exists():
                                target_time = int(LocalSettings.objects.filter(key='AR-Time')[0].value)
                            else:
                                LocalSettings(key='AR-Time', value='5').save()
                                target_time = 5
                            # TLDR: willing to pay 1 sat for every value_per_fee sats moved
                            if Rebalancer.objects.filter(last_hop_pubkey=target.remote_pubkey).exclude(status=0).exists():
                                last_rebalance = Rebalancer.objects.filter(last_hop_pubkey=target.remote_pubkey).exclude(status=0).order_by('-id')[0]
                                if not (last_rebalance.value != target_value or last_rebalance.status == 2 or (last_rebalance.status in [3, 4, 5, 6, 7, 400, 408] and (int((datetime.now() - last_rebalance.stop).total_seconds() / 60) > 30)) or (last_rebalance.status == 1 and (int((datetime.now() - last_rebalance.start).total_seconds() / 60) > 30))):
                                    continue
                            print('Creating Auto Rebalance Request')
                            print('Request for:', target.chan_id)
                            print('Request routing through:', outbound_cans)
                            print('Target Value:', target.ar_amt_target)
                            print('Target Fee:', target_fee)
                            print('Target Time:', target_time)
                            Rebalancer(value=target_value, fee_limit=target_fee, outgoing_chan_ids=str(outbound_cans).replace('\'', ''), last_hop_pubkey=target.remote_pubkey, target_alias=target.alias, duration=target_time).save()

def auto_enable():
    if LocalSettings.objects.filter(key='AR-Autopilot').exists():
        enabled = int(LocalSettings.objects.filter(key='AR-Autopilot')[0].value)
    else:
        LocalSettings(key='AR-Autopilot', value='0').save()
        enabled = 0
    if enabled == 1:
        channels = Channels.objects.filter(is_active=True, is_open=True, private=False).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*1000)/Sum('capacity')).annotate(inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*1000)/Sum('capacity'))
        filter_7day = datetime.now() - timedelta(days=7)
        forwards = Forwards.objects.filter(forward_date__gte=filter_7day)
        for channel in channels:
            outbound_percent = int(round(channel.outbound_percent/10, 0))
            inbound_percent = int(round(channel.inbound_percent/10, 0))
            routed_in_7day = forwards.filter(chan_id_in=channel.chan_id).count()
            routed_out_7day = forwards.filter(chan_id_out=channel.chan_id).count()
            i7D = 0 if routed_in_7day == 0 else int(forwards.filter(chan_id_in=channel.chan_id).aggregate(Sum('amt_in_msat'))['amt_in_msat__sum']/10000000)/100
            o7D = 0 if routed_out_7day == 0 else int(forwards.filter(chan_id_out=channel.chan_id).aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/10000000)/100
            if o7D > (i7D*1.10) and outbound_percent > 75:
                #print('Case 1: Pass')
                pass
            elif o7D > (i7D*1.10) and inbound_percent > 75 and channel.auto_rebalance == False:
                #print('Case 2: Enable AR - o7D > i7D AND Inbound Liq > 75%')
                channel.auto_rebalance = True
                channel.save()
                Autopilot(chan_id=channel.chan_id, peer_alias=channel.alias, setting='Enabled', old_value=0, new_value=1).save()
            elif o7D < (i7D*1.10) and outbound_percent > 75 and channel.auto_rebalance == True:
                #print('Case 3: Disable AR - o7D < i7D AND Outbound Liq > 75%')
                channel.auto_rebalance = False
                channel.save()
                Autopilot(chan_id=channel.chan_id, peer_alias=channel.alias, setting='Enabled', old_value=1, new_value=0).save()
            elif o7D < (i7D*1.10) and inbound_percent > 75:
                #print('Case 4: Pass')
                pass
            else:
                #print('Case 5: Pass')
                pass

def main():
    rebalances = Rebalancer.objects.filter(status=0).order_by('id')
    if len(rebalances) == 0:
        auto_enable()
        auto_schedule()
    else:
        rebalance = rebalances[0]
        while rebalance != None:
            rebalance = run_rebalancer(rebalance)

if __name__ == '__main__':
    main()