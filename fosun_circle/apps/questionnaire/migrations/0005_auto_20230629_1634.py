# Generated by Django 3.1.14 on 2023-06-29 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questionnaire', '0004_auto_20230606_1503'),
    ]

    operations = [
        migrations.AlterField(
            model_name='questionnairemodel',
            name='is_anonymous',
            field=models.BooleanField(blank=True, default=True, verbose_name='是否匿名'),
        ),
    ]