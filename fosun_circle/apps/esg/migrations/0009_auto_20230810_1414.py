# Generated by Django 3.1.14 on 2023-08-10 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esg', '0008_esgtaskactionmodel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='esgtaskactionmodel',
            name='uid',
            field=models.CharField(default='', max_length=200, null=True, unique=True, verbose_name='任务唯一标识'),
        ),
    ]