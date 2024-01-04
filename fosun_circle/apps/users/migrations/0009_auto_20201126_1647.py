# Generated by Django 3.1.2 on 2020-11-26 16:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_auto_20201126_1643'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='circleusersresourcepermissionmodel',
            name='permission_ids',
        ),
        migrations.RemoveField(
            model_name='circleusersresourcepermissionmodel',
            name='resource_id',
        ),
        migrations.AddField(
            model_name='circleusersresourcepermissionmodel',
            name='resource_perm_id',
            field=models.IntegerField(db_index=True, default=-1, verbose_name='资源或权限权限ID'),
        ),
    ]
