# Generated by Django 3.1.14 on 2023-05-30 15:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lottery', '0005_auto_20230524_1428'),
    ]

    operations = [
        migrations.AddField(
            model_name='participantmodel',
            name='push_log_id',
            field=models.IntegerField(blank=True, default=None, null=True, verbose_name='推送记录ID'),
        ),
    ]
