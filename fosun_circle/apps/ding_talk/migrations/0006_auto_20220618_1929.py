# Generated by Django 3.1.2 on 2022-06-18 19:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ding_talk', '0005_dingappmediamodel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dingappmediamodel',
            name='app',
            field=models.ForeignKey(blank=True, default=None, on_delete=django.db.models.deletion.CASCADE, to='ding_talk.dingapptokenmodel', verbose_name='微应用id'),
        ),
        migrations.AlterField(
            model_name='dingappmediamodel',
            name='media_type',
            field=models.SmallIntegerField(blank=True, choices=[(1, 'image'), (2, 'file'), (3, 'voice')], default=1, verbose_name='媒体类型'),
        ),
    ]
