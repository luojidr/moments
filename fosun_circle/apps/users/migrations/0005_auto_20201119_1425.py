# Generated by Django 3.1.2 on 2020-11-19 14:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_auto_20201110_1349'),
    ]

    operations = [
        migrations.AlterField(
            model_name='circleusersmodel',
            name='position_chz',
            field=models.CharField(default='', max_length=500, verbose_name='职位中文名'),
        ),
        migrations.AlterField(
            model_name='circleusersmodel',
            name='position_eng',
            field=models.CharField(default='', max_length=500, verbose_name='职位英文名'),
        ),
    ]
