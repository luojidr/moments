# Generated by Django 3.1.14 on 2023-07-25 13:10

import django.contrib.auth.models
from django.db import migrations


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0022_circleusersmodel_is_required_2fa'),
    ]

    operations = [
        migrations.CreateModel(
            name='EsgUserModel',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('users.circleusersmodel',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
