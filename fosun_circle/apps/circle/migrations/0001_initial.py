# Generated by Django 3.1.14 on 2022-10-10 10:54

from django.db import migrations, models
import fosun_circle.core.db.base


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DissDingPushLogModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creator', models.CharField(default=fosun_circle.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('modifier', models.CharField(default=fosun_circle.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_del', models.BooleanField(default=False, verbose_name='是否删除')),
                ('diss_id', models.IntegerField(db_index=True, default=0, verbose_name='吐槽ID')),
                ('send_id', models.IntegerField(default=0, verbose_name='推送者id')),
                ('receive_id', models.IntegerField(default=2, verbose_name='接受者id')),
                ('push_status', models.SmallIntegerField(verbose_name='推送状态')),
            ],
            options={
                'db_table': 'circle_diss_push_log',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DissFeedbackModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creator', models.CharField(default=fosun_circle.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('modifier', models.CharField(default=fosun_circle.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_del', models.BooleanField(default=False, verbose_name='是否删除')),
                ('diss_id', models.IntegerField(default=0, verbose_name='吐槽ID')),
                ('user_id', models.IntegerField(default=0, verbose_name='吐槽的反馈者')),
                ('mobile', models.CharField(default='', max_length=11, verbose_name='用户手机号')),
                ('state', models.IntegerField(choices=[(0, '待处理'), (1, '已处理'), (2, '非管辖范围')], default=0, verbose_name='吐槽处理状态')),
                ('remark', models.CharField(default='', max_length=1000, verbose_name='吐槽备注')),
                ('is_snapshot', models.BooleanField(default=False, verbose_name='是否快照')),
            ],
            options={
                'db_table': 'circle_diss_feedback',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='CircleActionLogModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creator', models.CharField(default=fosun_circle.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('modifier', models.CharField(default=fosun_circle.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_del', models.BooleanField(default=False, verbose_name='是否删除')),
                ('circle_id', models.IntegerField(default=None, verbose_name='帖子id')),
                ('comment_id', models.IntegerField(default=None, verbose_name='评论id')),
                ('action_type', models.SmallIntegerField(choices=[(1, '帖子评论'), (2, '帖子点赞'), (3, '评论点赞')], default=0, verbose_name='操作类型')),
                ('action_cn', models.CharField(default='', max_length=200, verbose_name='操作描述')),
                ('mobile', models.CharField(default='', max_length=20, verbose_name='手机号(帖子拥有者)')),
                ('is_pushed', models.BooleanField(default=False, verbose_name='是否已推送')),
            ],
            options={
                'db_table': 'circle_action_log',
            },
        ),
    ]
