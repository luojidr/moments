# Generated by Django 3.1.14 on 2022-11-17 14:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ding_talk', '0011_dingmsgpushlogmodel_is_cryptonym'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dingmessagemodel',
            name='msg_pc_url',
            field=models.CharField(blank=True, default='', max_length=1000, verbose_name='PC消息链接'),
        ),
        migrations.AlterField(
            model_name='dingmessagemodel',
            name='msg_url',
            field=models.CharField(blank=True, default='', max_length=1000, verbose_name='消息链接'),
        ),
    ]
