# Generated by Django 3.1.14 on 2023-05-26 14:02

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('permissions', '0008_auto_20230526_1324'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupmodel',
            name='menu_users',
            field=models.ManyToManyField(related_name='menu_groups', through='permissions.OwnerToMenuPermissionModel', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='groupmodel',
            name='menus',
            field=models.ManyToManyField(related_name='menu_groups', through='permissions.GroupOwnedMenuModel', to='permissions.MenuModel'),
        ),
    ]
