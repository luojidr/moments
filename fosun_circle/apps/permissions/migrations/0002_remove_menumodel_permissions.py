# Generated by Django 3.1.14 on 2023-04-13 12:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('permissions', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='menumodel',
            name='permissions',
        ),
    ]
