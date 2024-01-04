# Generated by Django 3.1.2 on 2022-02-24 09:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_auto_20220224_0851'),
    ]

    operations = [
        migrations.AlterField(
            model_name='circledepartmentmodel',
            name='batch_no',
            field=models.CharField(default='', max_length=200, verbose_name='同步批号'),
        ),
        migrations.AlterField(
            model_name='circledepartmentmodel',
            name='dep_en_name',
            field=models.CharField(default='', max_length=200, verbose_name='部门英文名称'),
        ),
        migrations.AlterField(
            model_name='circledepartmentmodel',
            name='dep_id',
            field=models.CharField(default='', max_length=200, verbose_name='部门唯一标识'),
        ),
        migrations.AlterField(
            model_name='circledepartmentmodel',
            name='dep_name',
            field=models.CharField(default='', max_length=200, verbose_name='部门名称'),
        ),
        migrations.AlterField(
            model_name='circledepartmentmodel',
            name='dep_only_code',
            field=models.CharField(default='', max_length=200, verbose_name='部门 Only Code'),
        ),
        migrations.AlterField(
            model_name='circledepartmentmodel',
            name='display_order',
            field=models.IntegerField(default=0, verbose_name='部门在钉钉展示顺序'),
        ),
        migrations.AlterField(
            model_name='circledepartmentmodel',
            name='name_path',
            field=models.CharField(default='', max_length=200, verbose_name='部门唯一路径'),
        ),
        migrations.AlterField(
            model_name='circledepartmentmodel',
            name='parent_dep_id',
            field=models.CharField(default='', max_length=200, verbose_name='上一级部门唯一标识'),
        ),
    ]
