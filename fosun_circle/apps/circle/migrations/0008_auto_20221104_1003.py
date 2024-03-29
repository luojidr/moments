# Generated by Django 3.1.14 on 2022-11-04 10:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('circle', '0007_auto_20221104_1002'),
    ]

    operations = [
        migrations.AlterField(
            model_name='circleactionlogmodel',
            name='action_type',
            field=models.SmallIntegerField(choices=[(1, '帖子评论'), (2, '帖子点赞'), (3, '评论点赞'), (4, '帖子审核'), (5, '人事专区发帖提醒'), (6, '人事专区评论与回复提醒')], default=0, verbose_name='操作类型'),
        ),
        migrations.AlterField(
            model_name='circlemessagebodymodel',
            name='action_type',
            field=models.SmallIntegerField(choices=[(1, '帖子评论'), (2, '帖子点赞'), (3, '评论点赞'), (4, '帖子审核'), (5, '人事专区发帖提醒'), (6, '人事专区评论与回复提醒')], default=0, unique=True, verbose_name='操作类型'),
        ),
    ]
