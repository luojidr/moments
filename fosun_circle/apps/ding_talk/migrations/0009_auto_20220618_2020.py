# Generated by Django 3.1.2 on 2022-06-18 20:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ding_talk', '0008_auto_20220618_1946'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dingappmediamodel',
            name='app',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ding_talk.dingapptokenmodel', verbose_name='微应用id'),
        ),
    ]
