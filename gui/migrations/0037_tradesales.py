# Generated by Django 4.2.6 on 2023-11-08 20:52

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('gui', '0036_peers'),
    ]

    operations = [
        migrations.CreateModel(
            name='TradeSales',
            fields=[
                ('id', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('creation_date', models.DateField(default=django.utils.timezone.now)),
                ('expiry', models.DateTimeField(null=True)),
                ('description', models.CharField(max_length=100)),
                ('price', models.BigIntegerField()),
                ('sale_type', models.IntegerField()),
                ('secret', models.CharField(max_length=1000, null=True)),
                ('sale_limit', models.IntegerField(null=True)),
                ('sale_count', models.IntegerField(default=0)),
            ],
        ),
    ]
