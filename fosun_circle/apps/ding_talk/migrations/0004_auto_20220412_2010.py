# Generated by Django 3.1.2 on 2022-04-12 20:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ding_talk', '0003_auto_20220408_1151'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dingmsgpushlogmodel',
            name='receiver_mobile',
            field=models.CharField(blank=True, db_index=True, default='', max_length=20, verbose_name='接收人手机号'),
        ),
    ]
