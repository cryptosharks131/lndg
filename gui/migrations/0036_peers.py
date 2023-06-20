from django.db import migrations, models
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps.lnd_connect import lnd_connect

def migrate_update_channels(apps, schedma_editor):
    try:
        stub = lnrpc.LightningStub(lnd_connect())
        lnd_channels = stub.ListChannels(ln.ListChannelsRequest()).channels
        db_channels = apps.get_model('gui', 'channels')
        for channel in lnd_channels:
            if db_channels.objects.filter(chan_id=channel.chan_id).exists():
                db_channel = db_channels.objects.filter(chan_id=channel.chan_id)[0]
                db_channel.push_amt = channel.push_amount_sat
                db_channel.close_address = channel.close_address
                db_channel.save()
    except Exception as e:
        print('Unable to get current channel data:', str(e))

def revert_update_channels(apps, schedma_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('gui', '0035_histfailedhtlc'),
    ]

    operations = [
        migrations.AddField(
            model_name='peers',
            name='ping_time',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='channels',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='channels',
            name='close_address',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='channels',
            name='push_amt',
            field=models.BigIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.RunPython(migrate_update_channels, revert_update_channels),
    ]
