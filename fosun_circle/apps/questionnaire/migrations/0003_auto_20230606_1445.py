# Generated by Django 3.1.14 on 2023-06-06 14:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questionnaire', '0002_auto_20230605_1529'),
    ]

    operations = [
        migrations.AddField(
            model_name='questionnairemodel',
            name='ref_id',
            field=models.IntegerField(blank=True, default=None, null=True, verbose_name='非my问卷ID'),
        ),
        migrations.AddField(
            model_name='questionnairemodel',
            name='ref_md5',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='问卷MD5'),
        ),
        migrations.AlterField(
            model_name='questionnairemodel',
            name='save_time',
            field=models.DateTimeField(blank=True, default=None, null=True, verbose_name='保存时间'),
        ),
        migrations.AlterField(
            model_name='selectionmodel',
            name='type',
            field=models.SmallIntegerField(blank=True, choices=[(1, '单选题'), (2, '多选题'), (3, '单项文本题'), (4, '多项文本题'), (5, '打分题'), (6, '矩阵题')], default=0, verbose_name='题型'),
        ),
    ]
