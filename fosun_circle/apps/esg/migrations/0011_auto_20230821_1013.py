# Generated by Django 3.1.14 on 2023-08-21 10:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('esg', '0010_auto_20230810_1503'),
    ]

    operations = [
        migrations.RenameField(
            model_name='esgtaskactionmodel',
            old_name='uid',
            new_name='task_id',
        ),
    ]
