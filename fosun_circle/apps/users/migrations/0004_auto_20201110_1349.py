# Generated by Django 3.1.2 on 2020-11-10 13:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_auto_20201110_1313'),
    ]

    operations = [
        migrations.AlterField(
            model_name='circleusersmodel',
            name='password',
            field=models.CharField(default='guest!1234', max_length=128, verbose_name='password'),
        ),
    ]