# Generated by Django 3.1.14 on 2023-03-02 17:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('circle', '0012_auto_20221226_1301'),
    ]

    operations = [
        migrations.AlterField(
            model_name='circleactionlogmodel',
            name='mobile',
            field=models.CharField(default='', max_length=100, verbose_name='消息接收者手机号(帖子、评论)'),
        ),
    ]
