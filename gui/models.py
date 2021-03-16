from django.db import models

# Create your models here.
class Payments(models.Model):
    creation_date = models.DateTimeField()
    payment_hash = models.CharField(max_length=64)
    value = models.BigIntegerField()
    fee = models.IntegerField()
    status = models.IntegerField()
    index = models.IntegerField()
    class Meta:
        app_label = 'gui'

class Invoices(models.Model):
    creation_date = models.DateTimeField()
    settle_date = models.DateTimeField()
    r_hash = models.CharField(max_length=64)
    value = models.BigIntegerField()
    amt_paid = models.BigIntegerField()
    state = models.IntegerField()
    class Meta:
        app_label = 'gui'

class Forwards(models.Model):
    forward_date = models.DateTimeField()
    chan_id_in = models.CharField(max_length=18)
    chan_id_out = models.CharField(max_length=18)
    chan_in_alias = models.CharField(max_length=32, default='Unknown')
    chan_out_alias = models.CharField(max_length=32, default='Unknown')
    amt_in = models.BigIntegerField()
    amt_out = models.BigIntegerField()
    fee = models.FloatField()
    class Meta:
        app_label = 'gui'