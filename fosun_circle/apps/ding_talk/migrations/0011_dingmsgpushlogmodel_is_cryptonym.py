# Generated by Django 3.1.2 on 2022-06-24 14:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ding_talk', '0010_auto_20220620_1045'),
    ]

    operations = [
        migrations.AddField(
            model_name='dingmsgpushlogmodel',
            name='is_cryptonym',
            field=models.BooleanField(blank=True, default=False, verbose_name='是否匿名(问卷)'),
        ),
    ]
