from django.db import migrations, models
import django.utils.timezone

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
    ]
