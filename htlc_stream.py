import django
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps.lnd_connect import lnd_connect
from os import environ
from time import sleep
environ['DJANGO_SETTINGS_MODULE'] = 'lndg.settings'
django.setup()
from gui.models import Channels, FailedHTLCs

def main():
    try:
        connection = lnd_connect()
        routerstub = lnrouter.RouterStub(connection)
        for response in routerstub.SubscribeHtlcEvents(lnr.SubscribeHtlcEventsRequest()):
            if response.event_type == 3 and str(response.link_fail_event) != '':
                in_chan_id = response.incoming_channel_id
                out_chan_id = response.outgoing_channel_id
                in_chan = Channels.objects.filter(chan_id=in_chan_id)[0] if Channels.objects.filter(chan_id=in_chan_id).exists() else None
                out_chan = Channels.objects.filter(chan_id=out_chan_id)[0] if Channels.objects.filter(chan_id=out_chan_id).exists() else None
                in_chan_alias = in_chan.alias if in_chan is not None else None
                out_chan_alias = out_chan.alias if out_chan is not None else None
                out_chan_liq = out_chan.local_balance if out_chan is not None else None
                out_chan_pending = out_chan.pending_outbound if out_chan is not None else None
                amount = int(response.link_fail_event.info.outgoing_amt_msat/1000)
                wire_failure = response.link_fail_event.wire_failure
                failure_detail = response.link_fail_event.failure_detail
                missed_fee = (response.link_fail_event.info.incoming_amt_msat - response.link_fail_event.info.outgoing_amt_msat)/1000
                FailedHTLCs(amount=amount, chan_id_in=in_chan_id, chan_id_out=out_chan_id, chan_in_alias=in_chan_alias, chan_out_alias=out_chan_alias, chan_out_liq=out_chan_liq, chan_out_pending=out_chan_pending, wire_failure=wire_failure, failure_detail=failure_detail, missed_fee=missed_fee).save()
    except Exception as e:
        print('Error while running failed HTLC stream: ' + str(e))
        sleep(20)

if __name__ == '__main__':
    main()