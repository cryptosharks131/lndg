import django
from django.conf import settings
from pathlib import Path
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps.lnd_connect import lnd_connect

BASE_DIR = Path(__file__).resolve().parent
settings.configure(
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3'
        }
    }
)
django.setup()
from lndg import settings
from gui.models import Channels, FailedHTLCs

def main():
    try:
        connection = lnd_connect(settings.LND_DIR_PATH, settings.LND_NETWORK, settings.LND_RPC_SERVER)
        routerstub = lnrouter.RouterStub(connection)
        for response in routerstub.SubscribeHtlcEvents(lnr.SubscribeHtlcEventsRequest()):
            if response.event_type == 3 and str(response.link_fail_event) != '':
                in_chan_id = response.incoming_channel_id
                out_chan_id = response.outgoing_channel_id
                in_chan = Channels.objects.filter(chan_id=in_chan_id)[0] if Channels.objects.filter(chan_id=in_chan_id).exists() else None
                out_chan = Channels.objects.filter(chan_id=out_chan_id)[0] if Channels.objects.filter(chan_id=out_chan_id).exists() else None
                in_chan_alias = in_chan.alias if in_chan is not None else None
                out_chan_alias = out_chan.alias if out_chan is not None else None
                amount = int(response.link_fail_event.info.outgoing_amt_msat/1000)
                wire_failure = response.link_fail_event.wire_failure
                failure_detail = response.link_fail_event.failure_detail
                missed_fee = ((amount/1000000) * out_chan.local_fee_rate) + out_chan.local_base_fee
                FailedHTLCs(amount=amount, chan_id_in=in_chan_id, chan_id_out=out_chan_id, chan_in_alias=in_chan_alias, chan_out_alias=out_chan_alias, wire_failure=wire_failure, failure_detail=failure_detail, missed_fee=missed_fee)
    except Exception as e:
        print('Error while running failed HTLC stream: ' + str(e))

if __name__ == '__main__':
    main()