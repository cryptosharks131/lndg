# Generated by Django 3.2.7 on 2021-09-28 16:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gui', '0005_alter_invoices_settle_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='channels',
            name='local_chan_reserve',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='invoices',
            name='settle_date',
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='rebalancer',
            name='start',
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='rebalancer',
            name='stop',
            field=models.DateTimeField(default=None, null=True),
        ),
    ]
