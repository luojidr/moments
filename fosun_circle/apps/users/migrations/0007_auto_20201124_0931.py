# Generated by Django 3.1.2 on 2020-11-24 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_auto_20201123_1033'),
    ]

    operations = [
        migrations.AlterField(
            model_name='circleusersmodel',
            name='avatar',
            field=models.CharField(default='http://exerland-bbs.oss-cn-shanghai.aliyuncs.com/default-profile.png', max_length=500, verbose_name='头像链接'),
        ),
    ]