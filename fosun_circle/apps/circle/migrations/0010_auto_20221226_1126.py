# Generated by Django 3.1.14 on 2022-12-26 11:26

from django.db import migrations, models
import fosun_circle.core.db.base


class Migration(migrations.Migration):

    dependencies = [
        ('circle', '0009_circleactionlogmodel_push_strategy'),
    ]

    operations = [
        migrations.CreateModel(
            name='CircleAnnualPersonalSummaryModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creator', models.CharField(default=fosun_circle.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('modifier', models.CharField(default=fosun_circle.core.db.base.AutoExecutor(), max_length=200, verbose_name='创建人')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_del', models.BooleanField(default=False, verbose_name='是否删除')),
                ('user_id', models.IntegerField(default=0, null=True, verbose_name='用户ID')),
                ('mobile', models.CharField(default='', max_length=200, verbose_name='用户手机')),
                ('first_login_date', models.DateField(default=None, null=True, verbose_name='第一次登陆星圈日期')),
                ('first_circle_id', models.IntegerField(default=0, null=True, verbose_name='第一个实名帖子')),
                ('first_circle_text', models.CharField(default='', max_length=1000, null=True, verbose_name='第一个实名帖子内容')),
                ('received_star_cnt', models.IntegerField(default=0, null=True, verbose_name='收到赞评数')),
                ('received_star_user_cnt', models.IntegerField(default=0, null=True, verbose_name='收到赞评的人数')),
                ('delivered_star_cnt', models.IntegerField(default=0, null=True, verbose_name='送出赞评数')),
                ('hot_circle_cnt', models.IntegerField(default=0, null=True, verbose_name='参与热门话题次数')),
                ('login_pv_cnt', models.IntegerField(default=0, null=True, verbose_name='登陆星圈pv数')),
                ('accompany_days', models.IntegerField(default=0, null=True, verbose_name='陪伴天数')),
                ('delivered_avg_star_cnt', models.IntegerField(default=0, null=True, verbose_name='送赞超过平均赞数')),
                ('post_circle_cnt', models.IntegerField(default=0, null=True, verbose_name='发帖数量(>=2)')),
                ('annual', models.IntegerField(default=None, null=True, verbose_name='年度')),
            ],
            options={
                'db_table': 'circle_annual_summary',
            },
        ),
        migrations.AlterField(
            model_name='circleactionlogmodel',
            name='action_type',
            field=models.SmallIntegerField(choices=[(1, '帖子评论'), (2, '帖子点赞'), (3, '评论点赞'), (4, '帖子审核'), (5, 'HR知乎发帖提醒'), (6, 'HR知乎评论与回复提醒')], default=0, verbose_name='操作类型'),
        ),
        migrations.AlterField(
            model_name='circlemessagebodymodel',
            name='action_type',
            field=models.SmallIntegerField(choices=[(1, '帖子评论'), (2, '帖子点赞'), (3, '评论点赞'), (4, '帖子审核'), (5, 'HR知乎发帖提醒'), (6, 'HR知乎评论与回复提醒')], default=0, unique=True, verbose_name='操作类型'),
        ),
    ]
