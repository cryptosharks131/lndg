# Generated by Django 3.2.7 on 2021-09-28 15:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gui', '0004_channels_local_commit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoices',
            name='settle_date',
            field=models.DateTimeField(null=True),
        ),
    ]
