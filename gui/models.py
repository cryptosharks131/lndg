from django.db import models
from django.utils import timezone

# Create your models here.
class Payments(models.Model):
    creation_date = models.DateTimeField()
    payment_hash = models.CharField(max_length=64, primary_key=True)
    value = models.FloatField()
    fee = models.FloatField()
    status = models.IntegerField()
    index = models.IntegerField()
    chan_out = models.IntegerField(null=True)
    chan_out_alias = models.CharField(null=True, max_length=32)
    keysend_preimage = models.CharField(null=True, max_length=64)
    message = models.CharField(null=True, max_length=255)
    class Meta:
        app_label = 'gui'

class PaymentHops(models.Model):
    payment_hash = models.ForeignKey('Payments', on_delete=models.CASCADE)
    attempt_id = models.IntegerField()
    step = models.IntegerField()
    chan_id = models.IntegerField()
    alias = models.CharField(max_length=32)
    chan_capacity = models.BigIntegerField()
    node_pubkey = models.CharField(max_length=66)
    amt = models.FloatField()
    fee = models.FloatField()
    cost_to = models.FloatField()
    class Meta:
        app_label = 'gui'
        unique_together = (('payment_hash', 'attempt_id', 'step'),)

class Invoices(models.Model):
    creation_date = models.DateTimeField()
    settle_date = models.DateTimeField(null=True, default=None)
    r_hash = models.CharField(max_length=64, primary_key=True)
    value = models.FloatField()
    amt_paid = models.BigIntegerField()
    state = models.IntegerField()
    chan_in = models.IntegerField(null=True)
    chan_in_alias = models.CharField(null=True, max_length=32)
    keysend_preimage = models.CharField(null=True, max_length=64)
    message = models.CharField(null=True, max_length=255)
    index = models.IntegerField()
    class Meta:
        app_label = 'gui'

class Forwards(models.Model):
    forward_date = models.DateTimeField()
    chan_id_in = models.IntegerField()
    chan_id_out = models.IntegerField()
    chan_in_alias = models.CharField(null=True, max_length=32)
    chan_out_alias = models.CharField(null=True, max_length=32)
    amt_in_msat = models.BigIntegerField()
    amt_out_msat = models.BigIntegerField()
    fee = models.FloatField()
    class Meta:
        app_label = 'gui'

class Channels(models.Model):
    remote_pubkey = models.CharField(max_length=66)
    chan_id = models.IntegerField(primary_key=True)
    funding_txid = models.CharField(max_length=64)
    output_index = models.IntegerField()
    capacity = models.BigIntegerField()
    local_balance = models.BigIntegerField()
    remote_balance = models.BigIntegerField()
    unsettled_balance = models.BigIntegerField()
    local_commit = models.IntegerField()
    local_chan_reserve = models.IntegerField()
    num_updates = models.IntegerField()
    initiator = models.BooleanField()
    alias = models.CharField(max_length=32)
    local_base_fee = models.IntegerField()
    local_fee_rate = models.IntegerField()
    remote_base_fee = models.IntegerField()
    remote_fee_rate = models.IntegerField()
    is_active = models.BooleanField()
    is_open = models.BooleanField()
    auto_rebalance = models.BooleanField(default=False)
    ar_amt_target = models.BigIntegerField()
    ar_in_target = models.IntegerField(default=100)
    ar_out_target = models.IntegerField()

    def save(self, *args, **kwargs):
        if not self.ar_out_target:
            if LocalSettings.objects.filter(key='AR-Outbound%').exists():
                outbound_setting = float(LocalSettings.objects.filter(key='AR-Outbound%')[0].value)
            else:
                LocalSettings(key='AR-Outbound%', value='0.75').save()
                outbound_setting = 0.75
            self.ar_out_target = int(outbound_setting * 100)
        if not self.ar_amt_target:
            if LocalSettings.objects.filter(key='AR-Target%').exists():
                amt_setting = float(LocalSettings.objects.filter(key='AR-Target%')[0].value)
            else:
                LocalSettings(key='AR-Target%', value='0.05').save()
                amt_setting = 0.05
            self.ar_amt_target = int(amt_setting * self.capacity)
        super(Channels, self).save(*args, **kwargs)

    class Meta:
        app_label = 'gui'

class Peers(models.Model):
    pubkey = models.CharField(max_length=66, primary_key=True)
    address = models.CharField(max_length=100)
    sat_sent = models.BigIntegerField()
    sat_recv = models.BigIntegerField()
    inbound = models.BooleanField()
    connected = models.BooleanField()
    last_reconnected = models.DateTimeField(null=True, default=None)
    class Meta:
        app_label = 'gui'

class Rebalancer(models.Model):
    requested = models.DateTimeField(default=timezone.now)
    value = models.IntegerField()
    fee_limit = models.IntegerField()
    outgoing_chan_ids = models.TextField(default='[]')
    last_hop_pubkey = models.CharField(default='', max_length=66)
    target_alias = models.CharField(default='', max_length=32)
    duration = models.IntegerField()
    start = models.DateTimeField(null=True, default=None)
    stop = models.DateTimeField(null=True, default=None)
    status = models.IntegerField(default=0)
    payment_hash = models.CharField(max_length=64, null=True, default=None)
    class Meta:
        app_label = 'gui'

class LocalSettings(models.Model):
    key = models.CharField(primary_key=True, default=None, max_length=20)
    value = models.CharField(default=None, max_length=50)
    class Meta:
        app_label = 'gui'

class Onchain(models.Model):
    tx_hash = models.CharField(max_length=64, primary_key=True)
    amount = models.BigIntegerField()
    block_hash = models.CharField(max_length=64)
    block_height = models.IntegerField()
    time_stamp = models.DateTimeField()
    fee = models.IntegerField()
    label = models.CharField(max_length=100)
    class Meta:
        app_label = 'gui'

class PendingHTLCs(models.Model):
    chan_id = models.IntegerField()
    alias = models.CharField(max_length=32)
    incoming = models.BooleanField()
    amount = models.BigIntegerField()
    hash_lock = models.CharField(max_length=64)
    expiration_height = models.IntegerField()
    forwarding_channel = models.IntegerField()
    forwarding_alias = models.CharField(max_length=32)
    class Meta:
        app_label = 'gui'

class FailedHTLCs(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    amount = models.IntegerField()
    chan_id_in = models.IntegerField()
    chan_id_out = models.IntegerField()
    chan_in_alias = models.CharField(null=True, max_length=32)
    chan_out_alias = models.CharField(null=True, max_length=32)
    wire_failure = models.IntegerField()
    failure_detail = models.IntegerField()
    missed_fee = models.FloatField()
    class Meta:
        app_label = 'gui'

class Autopilot(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    chan_id = models.IntegerField()
    peer_alias = models.CharField(max_length=32)
    setting = models.CharField(max_length=20)
    old_value = models.IntegerField()
    new_value = models.IntegerField()
    class Meta:
        app_label = 'gui'