import os, codecs, django, grpc, json, pandas, datetime
from django.conf import settings
from django.utils import timezone
from django.db.models import Max
from pathlib import Path
from datetime import datetime
import rpc_pb2 as ln
import rpc_pb2_grpc_jobs as lnrpc
import router_pb2_rebalancer as lnr
import router_pb2_grpc_rebalancer as lnrouter

BASE_DIR = Path(__file__).resolve().parent.parent
settings.configure(
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3'
        }
    },
    TIME_ZONE = 'America/New_York'
)
django.setup()
from models import Rebalancer, Channels, LocalSettings

#Define lnd connection for repeated use
def lnd_connect():
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
    return channel

def run_rebalancer(rebalance):
    if Rebalancer.objects.filter(status=1).exists():
        unknown_errors = Rebalancer.objects.filter(status=1)
        for unknown_error in unknown_errors:
            unknown_error.status = 400
            unknown_error.stop = timezone.now()
            unknown_error.save()
    rebalance.start = timezone.now()
    rebalance.save()
    try:
        #Open connection with lnd via grpc
        stub = lnrpc.LightningStub(lnd_connect())
        routerstub = lnrouter.RouterStub(lnd_connect())
        chan_ids = json.loads(rebalance.outgoing_chan_ids)
        timeout = rebalance.duration * 60
        response = stub.AddInvoice(ln.Invoice(value=rebalance.value, expiry=timeout))
        for response in routerstub.SendPaymentV2(lnr.SendPaymentRequest(payment_request=str(response.payment_request), fee_limit_sat=rebalance.fee_limit, outgoing_chan_ids=chan_ids, last_hop_pubkey=bytes.fromhex(rebalance.last_hop_pubkey), timeout_seconds=(timeout-15), allow_self_payment=True)):
            if response.status == 1 and rebalance.status == 0:
                #IN-FLIGHT
                rebalance.status = 1
                rebalance.save()
            elif response.status == 2:
                #SUCCESSFUL
                rebalance.status = 2
            elif response.status == 3:
                #FAILURE
                if response.failure_reason == 1:
                    #FAILURE_REASON_TIMEOUT
                    rebalance.status = 3
                elif response.failure_reason == 2:
                    #FAILURE_REASON_NO_ROUTE
                    rebalance.status = 4
                elif response.failure_reason == 3:
                    #FAILURE_REASON_ERROR
                    rebalance.status = 5
                elif response.failure_reason == 4:
                    #FAILURE_REASON_INCORRECT_PAYMENT_DETAILS
                    rebalance.status = 6
                elif response.failure_reason == 5:
                    #FAILURE_REASON_INSUFFICIENT_BALANCE
                    rebalance.status = 7
    except Exception as e:
        rebalance.status = 400
        error = str(e)
        print(error)
    finally:
        rebalance.stop = timezone.now()
        rebalance.save()

def auto_schedule():
    #No rebalancer jobs have been scheduled, lets look for any channels with an auto_rebalance flag and make the best request if we find one
    if LocalSettings.objects.filter(key='AR-Enabled').exists():
        enabled = int(LocalSettings.objects.filter(key='AR-Enabled')[0].value)
    else:
        LocalSettings(key='AR-Enabled', value='0').save()
        enabled = 0
    if enabled == 1:
        auto_rebalance_channels = Channels.objects.filter(auto_rebalance=True, is_active=True, is_open=True)
        if len(auto_rebalance_channels) > 0:
            if LocalSettings.objects.filter(key='AR-Outbound%').exists():
                outbound_percent = float(LocalSettings.objects.filter(key='AR-Outbound%')[0].value)
            else:
                LocalSettings(key='AR-Outbound%', value='0.85').save()
                outbound_percent = 0.85
            if LocalSettings.objects.filter(key='AR-Inbound%').exists():
                inbound_percent = float(LocalSettings.objects.filter(key='AR-Inbound%')[0].value)
            else:
                LocalSettings(key='AR-Inbound%', value='0.85').save()
                inbound_percent = 0.85
            auto_rebalance_data = {}
            chan_id_list = []
            inbound_liq_list = []
            outbound_liq_list = []
            outbound_cans = []
            for channel in auto_rebalance_channels:
                chan_id_list.append(channel.chan_id)
                outbound_liq_list.append(channel.local_balance)
                inbound_liq_list.append(channel.remote_balance)
                if (channel.local_balance / (channel.local_balance + channel.remote_balance)) > outbound_percent:
                    outbound_cans.append(channel.chan_id)
            auto_rebalance_data['chan_id'] = chan_id_list
            auto_rebalance_data['outbound_liq'] = outbound_liq_list
            auto_rebalance_data['inbound_liq'] = inbound_liq_list
            df = pandas.DataFrame(auto_rebalance_data, columns=['chan_id', 'outbound_liq', 'inbound_liq'])
            df['total_liq'] = df.inbound_liq + df.outbound_liq
            df['%inbound'] = df.inbound_liq / df.total_liq
            df['%outbound'] = df.outbound_liq / df.total_liq
            df = df.sort_values('%inbound', ascending=False, ignore_index=True)
            if df['%inbound'][0] > inbound_percent and len(outbound_cans) > 0:
                if LocalSettings.objects.filter(key='AR-Target%').exists():
                    target_percent = float(LocalSettings.objects.filter(key='AR-Target%')[0].value)
                else:
                    LocalSettings(key='AR-Target%', value='0.35').save()
                    target_percent = 0.35
                if LocalSettings.objects.filter(key='AR-MaxFeeRate').exists():
                    max_fee_rate = int(LocalSettings.objects.filter(key='AR-MaxFeeRate')[0].value)
                else:
                    LocalSettings(key='AR-MaxFeeRate', value='10').save()
                    max_fee_rate = 10
                # TLDR: lets target a custom % of the amount that would bring us back to a 50/50 channel balance using the MaxFeerate to calculate sat fee intervals
                value_per_fee = int(1 / (max_fee_rate / 1000000))
                target_value = int(((df['total_liq'][0] * 0.5) * target_percent) / value_per_fee) * value_per_fee
                if target_value >= value_per_fee:
                    if LocalSettings.objects.filter(key='AR-Time').exists():
                        target_time = int(LocalSettings.objects.filter(key='AR-Time')[0].value)
                    else:
                        LocalSettings(key='AR-Time', value='20').save()
                        target_time = 20
                    inbound_pubkey = Channels.objects.filter(chan_id=df['chan_id'][0])[0]
                    # TLDR: willing to pay 1 sat for every value_per_fee sats moved
                    target_fee = int(target_value * (1 / value_per_fee))
                    if Rebalancer.objects.exclude(status=0).exists():
                        last_rebalance = Rebalancer.objects.exclude(status=0).order_by('-id')[0]
                        if last_rebalance.last_hop_pubkey != inbound_pubkey.remote_pubkey or last_rebalance.outgoing_chan_ids != str(outbound_cans) or last_rebalance.value != target_value or last_rebalance.status in [2, 6] or (last_rebalance.status in [3, 4] and (int((datetime.now() - last_rebalance.stop).total_seconds() / 60) > 30)):
                            print('Creating Auto Rebalance Request')
                            print('Request for:', df['chan_id'][0])
                            print('Request routing through:', outbound_cans)
                            print('Target % Of Value:', target_percent)
                            print('Target Value:', target_value)
                            print('Target Fee:', target_fee)
                            print('Target Time:', target_time)
                            Rebalancer(value=target_value, fee_limit=target_fee, outgoing_chan_ids=outbound_cans, last_hop_pubkey=inbound_pubkey.remote_pubkey, duration=target_time).save()
                    else:
                        print('Creating Auto Rebalance Request')
                        print('Request for:', df['chan_id'][0])
                        print('Request routing through:', outbound_cans)
                        print('Target % Of Value:', target_percent)
                        print('Target Value:', target_value)
                        print('Target Fee:', target_fee)
                        print('Target Time:', target_time)
                        Rebalancer(value=target_value, fee_limit=target_fee, outgoing_chan_ids=outbound_cans, last_hop_pubkey=inbound_pubkey.remote_pubkey, duration=target_time).save()

def main():
    rebalances = Rebalancer.objects.filter(status=0).order_by('id')
    if len(rebalances) == 0:
        auto_schedule()
    else:
        run_rebalancer(rebalances[0])

if __name__ == '__main__':
    main()