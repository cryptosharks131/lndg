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
    class Meta:
        app_label = 'gui'
        unique_together = (('payment_hash', 'attempt_id', 'step'),)

class Invoices(models.Model):
    creation_date = models.DateTimeField()
    settle_date = models.DateTimeField()
    r_hash = models.CharField(max_length=64, primary_key=True)
    value = models.FloatField()
    amt_paid = models.BigIntegerField()
    state = models.IntegerField()
    chan_in = models.IntegerField(null=True)
    chan_in_alias = models.CharField(null=True, max_length=32)
    class Meta:
        app_label = 'gui'

class Forwards(models.Model):
    forward_date = models.DateTimeField()
    chan_id_in = models.IntegerField()
    chan_id_out = models.IntegerField()
    chan_in_alias = models.CharField(max_length=32, default='Unknown')
    chan_out_alias = models.CharField(max_length=32, default='Unknown')
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
    initiator = models.BooleanField()
    alias = models.CharField(max_length=32)
    base_fee = models.IntegerField()
    fee_rate = models.IntegerField()
    is_active = models.BooleanField()
    is_open = models.BooleanField()
    auto_rebalance = models.BooleanField(default=False)
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
    duration = models.IntegerField()
    start = models.DateTimeField(null=True)
    stop = models.DateTimeField(null=True)
    status = models.IntegerField(default=0)
    class Meta:
        app_label = 'gui'

class LocalSettings(models.Model):
    key = models.CharField(primary_key=True, default=None, max_length=20)
    value = models.CharField(default=None, max_length=50)
    class Meta:
        app_label = 'gui'