# Generated by Django 3.1.2 on 2020-11-10 13:13

import django.contrib.auth.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20201110_1037'),
    ]

    operations = [
        migrations.AlterField(
            model_name='circleusersmodel',
            name='phone_number',
            field=models.CharField(default='', max_length=20, unique=True, verbose_name='手机号码'),
        ),
        migrations.AlterField(
            model_name='circleusersmodel',
            name='username',
            field=models.CharField(default='', error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username'),
        ),
    ]
