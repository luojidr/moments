import os, sys
import django

pkg_path = os.path.dirname(os.path.dirname(__file__))
sys.path.append(pkg_path)

os.environ.setdefault("APP_ENV", "PROD")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()

from click.exceptions import Exit
from config.celery import celery_app
from celery.apps.beat import Beat
from celery.app.log import Logging

from fosun_circle.libs.log import task_logger

# app.worker_main()


"""
celery beat v5.2.3 (dawn-chorus) is starting.
__    -    ... __   -        _
LocalTime -> 2023-02-09 13:07:29
Configuration ->
    . broker -> amqp://admin:**@127.0.0.1:5672//circle
    . loader -> celery.loaders.app.AppLoader
    . scheduler -> django_celery_beat.schedulers.DatabaseScheduler

    . logfile -> [stderr]@%INFO
    . maxinterval -> 5.00 seconds (5s)
"""
# Beat本地测试用
# 动态定时任务管理问题， 可以依据 django_celery_beat.schedulers.DatabaseScheduler 中 schedule 属性的
# self.schedule_changed() 方法，动态的将最新的定时任务单元 schedule, 重新加载到 beat 里的 scheduler （调度器）.
# 那么如何动态呢？
# self.schedule_changed() 方法每次检测 django_celery_beat.models.PeriodicTasks 表中的 last_update 字段是否修改；
# 如果已经修改， 那么调用 self.celeryall_as_schedule() 将定时任务重新加载，具体代码看
# django_celery_beat.schedulers.DatabaseScheduler:schedule 中的 elif self.schedule_changed(): 相关代码
# 那么有时什么引起 PeriodicTasks.last_update 字段被修改呢？
# 主要是Django操作表的信号，主要有这些几种（django_celery_beat.models 文件中的 signals.xxx 信号）。
# pre_delete: 在模型的 delete() 方法和查询集的 delete() 方法开始时发送。eg: obj.delete() | queryset.delete()
# pre_save: 在模型的 save() 方法开始时发送的。eg: obj.save()
# post_save: 就像 pre_save 一样，但在 save() 方法的最后发送.
# post_delete: 就像 pre_delete 一样，但在模型的 delete() 方法和查询集的 delete() 方法结束时发送。


if __name__ == "__main__":
    # The support for this usage was removed in Celery 5.0.Instead you should use `-A` as a global option:
    # celery -A celeryapp beat < ... >
    # Usage: celery beat[OPTIONS]
    # Try 'celery beat --help' for help.

    # 注意：如果启动多个 beat 服务，那么定时任务执行的次数就会beat服务的数目
    # 启动方式一
    """
    /bin/bash -c "source /home/.virtualenv/.setenv_fosun_circle.sh && 
    /home/.virtualenv/fosun_circle_running/bin/celery -A config.celery beat -l info "
    """
    celery_app.start(argv=["-A", "config.celery", "beat", "-l", "DEBUG"])

    # 启动方式二
    # print(app.connection().as_uri())
    # beat = Beat(
    #     max_interval=5, app=app, loglevel="DEBUG",
    #     # scheduler_cls="django_celery_beat.schedulers:DatabaseScheduler",
    # )
    # beat.run()



