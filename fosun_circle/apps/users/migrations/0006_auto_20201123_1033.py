# Generated by Django 3.1.2 on 2020-11-23 10:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_auto_20201119_1425'),
    ]

    operations = [
        migrations.AlterField(
            model_name='circleusersmodel',
            name='department_chz',
            field=models.CharField(default='', max_length=500, verbose_name='部门中文名'),
        ),
        migrations.AlterField(
            model_name='circleusersmodel',
            name='department_eng',
            field=models.CharField(default='', max_length=500, verbose_name='部门英文名'),
        ),
    ]