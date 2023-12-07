import django, json, secrets, asyncio
from time import sleep
from asgiref.sync import sync_to_async
from django.db.models import Sum, F
from datetime import datetime, timedelta
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps.lnd_connect import lnd_connect, async_lnd_connect
from os import environ
from typing import List

environ['DJANGO_SETTINGS_MODULE'] = 'lndg.settings'
django.setup()
from gui.models import Rebalancer, Channels, LocalSettings, Forwards, Autopilot

@sync_to_async
def get_out_cans(rebalance, auto_rebalance_channels):
    try:
        return list(auto_rebalance_channels.filter(auto_rebalance=False, percent_outbound__gte=F('ar_out_target')).exclude(remote_pubkey=rebalance.last_hop_pubkey).values_list('chan_id', flat=True))
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Error getting outbound cands: {str(e)}")

@sync_to_async
def save_record(record):
    try:
        record.save()
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Error saving database record: {str(e)}")

@sync_to_async
def inbound_cans_len(inbound_cans):
    try:
        return len(inbound_cans)
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Error getting inbound cands: {str(e)}")

async def run_rebalancer(rebalance, worker):
    try:
        #Reduce potential rebalance value in percent out to avoid going below AR-OUT-Target
        auto_rebalance_channels = Channels.objects.filter(is_active=True, is_open=True, private=False).annotate(percent_outbound=((Sum('local_balance')+Sum('pending_outbound')-rebalance.value)*100)/Sum('capacity')).annotate(inbound_can=(((Sum('remote_balance')+Sum('pending_inbound'))*100)/Sum('capacity'))/Sum('ar_in_target'))
        outbound_cans = await get_out_cans(rebalance, auto_rebalance_channels)
        if len(outbound_cans) == 0 and rebalance.manual == False:
            print(f"{datetime.now().strftime('%c')} : [Rebalancer] : No outbound_cans")
            rebalance.status = 406
            rebalance.start = datetime.now()
            rebalance.stop = datetime.now()
            await save_record(rebalance)
            return None
        elif str(outbound_cans).replace('\'', '') != rebalance.outgoing_chan_ids and rebalance.manual == False:
            rebalance.outgoing_chan_ids = str(outbound_cans).replace('\'', '')
        rebalance.start = datetime.now()
        try:
            #Open connection with lnd via grpc
            stub = lnrpc.LightningStub(lnd_connect())
            routerstub = lnrouter.RouterStub(async_lnd_connect())
            chan_ids = json.loads(rebalance.outgoing_chan_ids)
            timeout = rebalance.duration * 60
            invoice_response = stub.AddInvoice(ln.Invoice(value=rebalance.value, expiry=timeout))
            print(f"{datetime.now().strftime('%c')} : [Rebalancer] : {worker} starting rebalance for {rebalance.target_alias} {rebalance.last_hop_pubkey} for {rebalance.value} sats and duration {rebalance.duration}, using {len(chan_ids)} outbound channels")
            async for payment_response in routerstub.SendPaymentV2(lnr.SendPaymentRequest(payment_request=str(invoice_response.payment_request), fee_limit_msat=int(rebalance.fee_limit*1000), outgoing_chan_ids=chan_ids, last_hop_pubkey=bytes.fromhex(rebalance.last_hop_pubkey), timeout_seconds=(timeout-5), allow_self_payment=True), timeout=(timeout+60)):
                if payment_response.status == 1 and rebalance.status == 0:
                    #IN-FLIGHT
                    rebalance.payment_hash = payment_response.payment_hash
                    rebalance.status = 1
                    await save_record(rebalance)
                elif payment_response.status == 2:
                    #SUCCESSFUL
                    rebalance.status = 2
                    rebalance.fees_paid = payment_response.fee_msat/1000
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
                print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Error while sending payment: {str(e)}")
        finally:
            rebalance.stop = datetime.now()
            await save_record(rebalance)
            print(f"{datetime.now().strftime('%c')} : [Rebalancer] : {worker} completed payment attempts for: {rebalance.payment_hash}")
            original_alias = rebalance.target_alias
            inc=1.21
            dec=2
            if rebalance.status ==2:
                await update_channels(stub, rebalance.last_hop_pubkey, successful_out)
                #Reduce potential rebalance value in percent out to avoid going below AR-OUT-Target
                auto_rebalance_channels = Channels.objects.filter(is_active=True, is_open=True, private=False).annotate(percent_outbound=((Sum('local_balance')+Sum('pending_outbound')-rebalance.value*inc)*100)/Sum('capacity')).annotate(inbound_can=(((Sum('remote_balance')+Sum('pending_inbound'))*100)/Sum('capacity'))/Sum('ar_in_target'))
                inbound_cans = auto_rebalance_channels.filter(remote_pubkey=rebalance.last_hop_pubkey).filter(auto_rebalance=True, inbound_can__gte=1)
                outbound_cans = await get_out_cans(rebalance, auto_rebalance_channels)
                if await inbound_cans_len(inbound_cans) > 0 and len(outbound_cans) > 0:
                    next_rebalance = Rebalancer(value=int(rebalance.value*inc), fee_limit=round(rebalance.fee_limit*inc, 3), outgoing_chan_ids=str(outbound_cans).replace('\'', ''), last_hop_pubkey=rebalance.last_hop_pubkey, target_alias=original_alias, duration=1)
                    await save_record(next_rebalance)
                    print(f"{datetime.now().strftime('%c')} : [Rebalancer] : RapidFire increase for {next_rebalance.target_alias} from {next_rebalance.value} to {rebalance.value}")
                else:
                    next_rebalance = None
            # For failed rebalances, try in rapid fire with reduced balances until give up.
            elif rebalance.status > 2 and rebalance.value > 69420:
                #Previous Rapidfire with increased value failed, try with lower value up to 69420.
                if rebalance.duration > 1:
                    next_value = await estimate_liquidity ( payment_response )
                    if next_value < 1000:
                        next_rebalance = None
                        return next_rebalance
                else:
                    next_value = rebalance.value/dec

                inbound_cans = auto_rebalance_channels.filter(remote_pubkey=rebalance.last_hop_pubkey).filter(auto_rebalance=True, inbound_can__gte=1)
                if await inbound_cans_len(inbound_cans) > 0 and len(outbound_cans) > 0:
                    next_rebalance = Rebalancer(value=int(next_value), fee_limit=round(rebalance.fee_limit/(rebalance.value/next_value), 3), outgoing_chan_ids=str(outbound_cans).replace('\'', ''), last_hop_pubkey=rebalance.last_hop_pubkey, target_alias=original_alias, duration=1)
                    await save_record(next_rebalance)
                    print(f"{datetime.now().strftime('%c')} : [Rebalancer] : RapidFire decrease for {next_rebalance.target_alias} from {next_rebalance.value} to {rebalance.value}")
                else:
                    next_rebalance = None
            else:
                next_rebalance = None
            return next_rebalance
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Error running rebalance attempt: {str(e)}")

@sync_to_async
def estimate_liquidity( payment ):
    try:
        estimated_liquidity = 0
        if payment.status == 3:
            attempt = None
            for attempt in payment.htlcs:
                total_hops=len(attempt.route.hops)
                if attempt.failure.failure_source_index == total_hops:
                    #Failure from last hop indicating liquidity available
                    estimated_liquidity = attempt.route.total_amt if attempt.route.total_amt > estimated_liquidity else estimated_liquidity
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Estimated Liquidity {estimated_liquidity} for payment {payment.payment_hash} with status {payment.status} and reason {payment.failure_reason}")
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Error estimating liquidity: {str(e)}")
        estimated_liquidity = 0

    return estimated_liquidity

@sync_to_async
def update_channels(stub, incoming_channel, outgoing_channel):
    try:
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
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Error updating channel balances: {str(e)}")

@sync_to_async
def auto_schedule() -> List[Rebalancer]:
    try:
        #No rebalancer jobs have been scheduled, lets look for any channels with an auto_rebalance flag and make the best request if we find one
        to_schedule = []
        if LocalSettings.objects.filter(key='AR-Enabled').exists():
            enabled = int(LocalSettings.objects.filter(key='AR-Enabled')[0].value)
        else:
            LocalSettings(key='AR-Enabled', value='0').save()
            enabled = 0
        if enabled == 0:
            return []
        
        auto_rebalance_channels = Channels.objects.filter(is_active=True, is_open=True, private=False).annotate(percent_outbound=((Sum('local_balance')+Sum('pending_outbound'))*100)/Sum('capacity')).annotate(inbound_can=(((Sum('remote_balance')+Sum('pending_inbound'))*100)/Sum('capacity'))/Sum('ar_in_target'))
        if len(auto_rebalance_channels) == 0:
            return []
        
        if not LocalSettings.objects.filter(key='AR-Outbound%').exists():
            LocalSettings(key='AR-Outbound%', value='75').save()
        if not LocalSettings.objects.filter(key='AR-Inbound%').exists():
            LocalSettings(key='AR-Inbound%', value='90').save()
        outbound_cans = list(auto_rebalance_channels.filter(auto_rebalance=False, percent_outbound__gte=F('ar_out_target')).values_list('chan_id', flat=True))
        already_scheduled = Rebalancer.objects.exclude(last_hop_pubkey='').filter(status=0).values_list('last_hop_pubkey')
        inbound_cans = auto_rebalance_channels.filter(auto_rebalance=True, inbound_can__gte=1).exclude(remote_pubkey__in=already_scheduled).order_by('-inbound_can')
        if len(inbound_cans) == 0 or len(outbound_cans) == 0:
            return []
        
        if LocalSettings.objects.filter(key='AR-MaxFeeRate').exists():
            max_fee_rate = int(LocalSettings.objects.filter(key='AR-MaxFeeRate')[0].value)
        else:
            LocalSettings(key='AR-MaxFeeRate', value='500').save()
            max_fee_rate = 500
        if LocalSettings.objects.filter(key='AR-Variance').exists():
            variance = int(LocalSettings.objects.filter(key='AR-Variance')[0].value)
        else:
            LocalSettings(key='AR-Variance', value='0').save()
            variance = 0
        if LocalSettings.objects.filter(key='AR-WaitPeriod').exists():
            wait_period = int(LocalSettings.objects.filter(key='AR-WaitPeriod')[0].value)
        else:
            LocalSettings(key='AR-WaitPeriod', value='30').save()
            wait_period = 30
        if not LocalSettings.objects.filter(key='AR-Target%').exists():
            LocalSettings(key='AR-Target%', value='3').save()
        if not LocalSettings.objects.filter(key='AR-MaxCost%').exists():
            LocalSettings(key='AR-MaxCost%', value='65').save()
        for target in inbound_cans:
            target_fee_rate = int(target.local_fee_rate * (target.ar_max_cost/100))
            if target_fee_rate > 0 and target_fee_rate > target.remote_fee_rate:
                target_value = int(target.ar_amt_target+(target.ar_amt_target*((secrets.choice(range(-1000,1001))/1000)*variance/100)))
                target_fee = round(target_fee_rate*target_value*0.000001, 3) if target_fee_rate <= max_fee_rate else round(max_fee_rate*target_value*0.000001, 3)
                if target_fee == 0:
                    continue
            
                if LocalSettings.objects.filter(key='AR-Time').exists():
                    target_time = int(LocalSettings.objects.filter(key='AR-Time')[0].value)
                else:
                    LocalSettings(key='AR-Time', value='5').save()
                    target_time = 5
                # TLDR: willing to pay 1 sat for every value_per_fee sats moved
                if Rebalancer.objects.filter(last_hop_pubkey=target.remote_pubkey).exclude(status=0).exists():
                    last_rebalance = Rebalancer.objects.filter(last_hop_pubkey=target.remote_pubkey).exclude(status=0).order_by('-id')[0]
                    if not (last_rebalance.status == 2 or (last_rebalance.status > 2 and (int((datetime.now() - last_rebalance.stop).total_seconds() / 60) > wait_period)) or (last_rebalance.status == 1 and ((int((datetime.now() - last_rebalance.start).total_seconds() / 60) - last_rebalance.duration) > wait_period))):
                        continue
                print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Creating Auto Rebalance Request for: {target.chan_id}")
                print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Value: {target_value} / {target.ar_amt_target} | Fee: {target_fee} | Duration: {target_time}")
                print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Request routing outbound via: {outbound_cans}")
                new_rebalance = Rebalancer(value=target_value, fee_limit=target_fee, outgoing_chan_ids=str(outbound_cans).replace('\'', ''), last_hop_pubkey=target.remote_pubkey, target_alias=target.alias, duration=target_time)
                new_rebalance.save()
                to_schedule.append(new_rebalance)
        return to_schedule
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Error scheduling rebalances: {str(e)}")
        return to_schedule

@sync_to_async
def auto_enable():
    try:
        if LocalSettings.objects.filter(key='AR-Autopilot').exists():
            enabled = int(LocalSettings.objects.filter(key='AR-Autopilot')[0].value)
        else:
            LocalSettings(key='AR-Autopilot', value='0').save()
            enabled = 0
        if LocalSettings.objects.filter(key='AR-APDays').exists():
            apdays = int(LocalSettings.objects.filter(key='AR-APDays')[0].value)
        else:
            LocalSettings(key='AR-APDays', value='7').save()
            apdays = 7
        if enabled == 1:
            lookup_channels=Channels.objects.filter(is_active=True, is_open=True, private=False)
            channels = lookup_channels.values('remote_pubkey').annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*1000)/Sum('capacity')).annotate(inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*1000)/Sum('capacity')).order_by()
            filter_day = datetime.now() - timedelta(days=apdays)
            forwards = Forwards.objects.filter(forward_date__gte=filter_day)
            for channel in channels:
                outbound_percent = int(round(channel['outbound_percent']/10, 0))
                inbound_percent = int(round(channel['inbound_percent']/10, 0))
                chan_list = lookup_channels.filter(remote_pubkey=channel['remote_pubkey']).values('chan_id')
                routed_in_apday = forwards.filter(chan_id_in__in=chan_list).count()
                routed_out_apday = forwards.filter(chan_id_out__in=chan_list).count()
                iapD = 0 if routed_in_apday == 0 else int(forwards.filter(chan_id_in__in=chan_list).aggregate(Sum('amt_in_msat'))['amt_in_msat__sum']/10000000)/100
                oapD = 0 if routed_out_apday == 0 else int(forwards.filter(chan_id_out__in=chan_list).aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/10000000)/100
                for peer_channel in lookup_channels.filter(chan_id__in=chan_list):
                    if peer_channel.ar_out_target == 100 and peer_channel.auto_rebalance == True:
                        #Special Case for LOOP, Wos, etc. Always Auto Rebalance if enabled to keep outbound full.
                        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Skipping AR enabled and 100% oTarget channel: {peer_channel.alias} {peer_channel.chan_id}")
                        pass
                    elif oapD > (iapD*1.10) and outbound_percent > 75:
                        #print('Case 1: Pass')
                        pass
                    elif oapD > (iapD*1.10) and inbound_percent > 75 and peer_channel.auto_rebalance == False:
                        #print('Case 2: Enable AR - o7D > i7D AND Inbound Liq > 75%')
                        peer_channel.auto_rebalance = True
                        peer_channel.save()
                        Autopilot(chan_id=peer_channel.chan_id, peer_alias=peer_channel.alias, setting='Enabled', old_value=0, new_value=1).save()
                        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Auto Pilot Enabled for {peer_channel.alias} {peer_channel.chan_id}: {oapD} {iapD}")
                    elif oapD < (iapD*1.10) and outbound_percent > 75 and peer_channel.auto_rebalance == True:
                        #print('Case 3: Disable AR - o7D < i7D AND Outbound Liq > 75%')
                        peer_channel.auto_rebalance = False
                        peer_channel.save()
                        Autopilot(chan_id=peer_channel.chan_id, peer_alias=peer_channel.alias, setting='Enabled', old_value=1, new_value=0).save()
                        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Auto Pilot Disabled for {peer_channel.alias} {peer_channel.chan_id}: {oapD} {iapD}" )
                    elif oapD < (iapD*1.10) and inbound_percent > 75:
                        #print('Case 4: Pass')
                        pass
                    else:
                        #print('Case 5: Pass')
                        pass
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Error during auto channel enabling: {str(e)}")

@sync_to_async
def get_pending_rebals():
    try:
        rebalances = Rebalancer.objects.filter(status=0).order_by('id')
        return rebalances, len(rebalances)
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Error getting pending rebalances: {str(e)}")

async def async_queue_manager(rebalancer_queue):
    global scheduled_rebalances, active_rebalances, shutdown_rebalancer
    print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Queue manager is starting...")
    try:
        while True:
            if shutdown_rebalancer == True:
                return
            print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Queue currently has {rebalancer_queue.qsize()} items...")
            print(f"{datetime.now().strftime('%c')} : [Rebalancer] : There are currently {len(active_rebalances)} tasks in progress...")
            print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Queue manager is checking for more work...")
            pending_rebalances, rebal_count = await get_pending_rebals()
            if rebal_count > 0:
                for rebalance in pending_rebalances:
                    if rebalance.id not in (scheduled_rebalances + active_rebalances):
                        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Found a pending job to schedule with id: {rebalance.id}")
                        scheduled_rebalances.append(rebalance.id)
                        await rebalancer_queue.put(rebalance)
            await auto_enable()
            scheduled = await auto_schedule()
            if len(scheduled) > 0:
                print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Scheduling {len(scheduled)} more jobs...")
                for rebalance in scheduled:
                    scheduled_rebalances.append(rebalance.id)
                    await rebalancer_queue.put(rebalance)
            elif rebalancer_queue.qsize() == 0 and len(active_rebalances) == 0:
                print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Queue is still empty, stoping the rebalancer...")
                shutdown_rebalancer = True
                return
            await asyncio.sleep(30)
    except Exception as e:
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Queue manager exception: {str(e)}")
        shutdown_rebalancer = True
    finally:
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Queue manager has shut down...")

async def async_run_rebalancer(worker, rebalancer_queue):
    global scheduled_rebalances, active_rebalances, shutdown_rebalancer
    while True:
        if not rebalancer_queue.empty() and not shutdown_rebalancer:
            rebalance = await rebalancer_queue.get()
            print(f"{datetime.now().strftime('%c')} : [Rebalancer] : {worker} is starting a new request...")
            active_rebalance_id = None
            if rebalance != None:
                active_rebalance_id = rebalance.id
                active_rebalances.append(active_rebalance_id)
                scheduled_rebalances.remove(active_rebalance_id)
            while rebalance != None:
                rebalance = await run_rebalancer(rebalance, worker)
            if active_rebalance_id != None:
                active_rebalances.remove(active_rebalance_id)
            print(f"{datetime.now().strftime('%c')} : [Rebalancer] : {worker} completed its request...")
        else:
            if shutdown_rebalancer == True:
                return
        await asyncio.sleep(3)

async def start_queue(worker_count=1):
    rebalancer_queue = asyncio.Queue()
    manager = asyncio.create_task(async_queue_manager(rebalancer_queue))
    workers = [asyncio.create_task(async_run_rebalancer("Worker " + str(worker_num+1), rebalancer_queue)) for worker_num in range(worker_count)]
    await asyncio.gather(manager, *workers)
    print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Manager and workers have stopped...")

@sync_to_async
def get_worker_count():
    if LocalSettings.objects.filter(key='AR-Workers').exists():
        return int(LocalSettings.objects.filter(key='AR-Workers')[0].value)
    else:
        return 1

async def update_worker_count():
    global worker_count, shutdown_rebalancer
    while True:
        updated_worker_count = await get_worker_count()
        if updated_worker_count != worker_count:
            worker_count = updated_worker_count
            shutdown_rebalancer = True
            print(f"{datetime.now().strftime('%c')} : [Rebalancer] : New worker count detected...restarting rebalancer")
        await asyncio.sleep(20)

def main():
    global scheduled_rebalances, active_rebalances, shutdown_rebalancer, worker_count
    if LocalSettings.objects.filter(key='AR-Workers').exists():
        worker_count = int(LocalSettings.objects.filter(key='AR-Workers')[0].value)
    else:
        LocalSettings(key='AR-Workers', value='1').save()
        worker_count = 1
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(update_worker_count())
    while True:
        shutdown_rebalancer = False
        scheduled_rebalances = []
        active_rebalances = []
        if Rebalancer.objects.filter(status=1).exists():
            unknown_errors = Rebalancer.objects.filter(status=1)
            for unknown_error in unknown_errors:
                unknown_error.status = 400
                unknown_error.stop = datetime.now()
                unknown_error.save()
        loop.run_until_complete(start_queue(worker_count))
        print(f"{datetime.now().strftime('%c')} : [Rebalancer] : Rebalancer successfully exited...sleeping for 20 seconds")
        sleep(20)

if __name__ == '__main__':
    main()