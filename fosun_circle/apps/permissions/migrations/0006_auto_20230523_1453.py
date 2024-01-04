# Generated by Django 3.1.14 on 2023-05-23 14:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('permissions', '0005_remove_menumodel_submenu_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='menumodel',
            name='is_hidden',
            field=models.BooleanField(blank=True, default=False, verbose_name='Hidden'),
        ),
        migrations.AddField(
            model_name='menumodel',
            name='remark',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Remark'),
        ),
    ]