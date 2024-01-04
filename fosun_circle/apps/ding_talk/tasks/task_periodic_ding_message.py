import os
import json
import traceback
import itertools
from multiprocessing.dummy import Pool as ThreadPool

from celery import current_app
from django.db import transaction
from django.conf import settings
from django.http.request import HttpRequest
from django.core.handlers.wsgi import WSGIRequest
from django_celery_beat.models import PeriodicTask, PeriodicTasks

from config.celery import celery_app
from fosun_circle.libs import timezone
from fosun_circle.libs.log import task_logger as logger
from fosun_circle.apps.ding_talk.tasks.task_send_ding_message import send_ding_message
from users.models import CircleUsersModel
from ding_talk.models import DingMsgPushLogModel, DingMessageModel, DingPeriodicTaskModel
from ding_talk.views import SendDingMessageByDepartmentApi
from questionnaire.models import QuestionnaireModel


def is_running_task(task_name):
    """ 正在执行的任务 """
    running_tasks = []
    ins = current_app.control.inspect()

    try:
        for hostname, tasks in ins.active().items():
            running_tasks.extend(tasks)

            for task_item in tasks:
                if task_name == task_item['name']:
                    return True
    except Exception as e:
        logger.error("is_running_task err: %s", e)
        logger.error(traceback.format_exc())

    return False


@celery_app.task(ignore_result=True)
def monitor_all_periodic_tasks(**kwargs):
    """ 监控正在执行的所有任务 """
    base_task_queryset = DingPeriodicTaskModel.objects.filter(is_del=False).all()
    beat_periodic_ids = list(set(base_task_queryset.values_list('beat_periodic_task_id', flat=True)))

    # 获取 PeriodicTask 所有任务
    beat_query = dict(enabled=True, id__in=beat_periodic_ids)
    periodic_queryset = PeriodicTask.objects.filter(**beat_query).values('id', 'kwargs')
    periodic_dict = {item['id']: item['kwargs'] for item in periodic_queryset}

    task_queryset = base_task_queryset\
        .filter(beat_periodic_task_id__in=list(periodic_dict.keys()))\
        .values('id', 'beat_periodic_task_id', 'deadline_run_time')

    logger.info("监控任务heartbeat => task_queryset count: %s", len(task_queryset))

    for task_item in task_queryset:
        ding_periodic_id = task_item['id']
        deadline_run_time = task_item['deadline_run_time']
        beat_periodic_task_id = task_item['beat_periodic_task_id']

        # 自定义定时任务与CeleryPeriodicTask任务
        ding_periodic_obj = DingPeriodicTaskModel.objects.filter(id=ding_periodic_id).first()
        beat_periodic_obj = PeriodicTask.objects.filter(id=beat_periodic_task_id).first()
        log_argsx = (ding_periodic_id, beat_periodic_task_id)

        # 如果监测到有任务正在执行，放弃此次操作(保证定时任务的最后一次也能正常执行)
        task_name = beat_periodic_obj or beat_periodic_obj.task
        if is_running_task(task_name):
            logger.warning("自动监控 ===>>> 任务<%s>正在运行中", task_name)
            x_args = (ding_periodic_id, deadline_run_time, timezone.now())
            logger.warning("自动监控 ===>>> 任务正在执行 ding_periodic_id: %s, deadline_run_time: %s, Now: %s", *x_args)
            continue

        current_dt = timezone.now()
        try:
            if deadline_run_time:
                p_log_args = (ding_periodic_id, deadline_run_time, current_dt)
                logger.info("监控任务时间 => ding_periodic_id: %s, deadline_run_time: %s, Now: %s", *p_log_args)

                if deadline_run_time < current_dt:  # 任务最后执行的时间比当前时间小（即：任务早已经结束）
                    if ding_periodic_obj and beat_periodic_obj:
                        with transaction.atomic():
                            beat_periodic_obj.enabled = False
                            beat_periodic_obj.save()

                            ding_periodic_obj.remark = '%s（自动监控->停止）' % ding_periodic_obj.remark
                            ding_periodic_obj.save()
                            PeriodicTasks.update_changed()

                        logger.info("监控任务停止 => ding_periodic_id: %s, beat_periodic_task_id: %s", *log_argsx)
                else:  #
                    # 后续其他自动监控
                    pass
        except Exception as e:
            logger.error(traceback.format_exc())


@celery_app.task(ignore_result=True)
def send_periodic_ding_message(message_id_list=None, ding_cron_id=None, **kwargs):
    """ 周期性任务推送话题任务，动态管理定时任务
    :param message_id_list: 改造前的任务参数, 都是指向同一个话题
    :param ding_cron_id: 改造后的任务参数，包含一个话题
    """
    logger.info("send_periodic_ding_message => message_id_list:%s, ding_cron_id: %s", message_id_list, ding_cron_id)

    # 改造前任务处理
    msg_query = dict(id__in=[int(mid) for mid in message_id_list or []], is_del=False)
    msg_queryset = DingMessageModel.objects.filter(**msg_query).values_list("id", flat=True)
    required_message_ids = list(msg_queryset)  # 同一个话题的消息体可能存在多条（即多个message_id）

    # 改造后任务逻辑
    ding_cron_obj = DingPeriodicTaskModel.objects.filter(id=ding_cron_id or 0, is_del=False).first()
    ding_cron_obj and required_message_ids.append(ding_cron_obj.message_id)

    if not required_message_ids:
        logger.info("send_periodic_ding_message => 未获取到任何话题")
        return

    # 获取实名问卷对应的钉钉消息
    #   实名问卷
    survey_queryset = QuestionnaireModel.objects.filter(is_anonymous=False, is_del=False).values_list("ref_id", flat=True)
    real_survey_ids = [_survey_id for _survey_id in survey_queryset if _survey_id]
    #   对应的钉钉消息
    msg_query2 = dict(id__in=required_message_ids, ihcm_survey_id__in=real_survey_ids, source=2, is_del=False)
    real_survey_message_ids = list(DingMessageModel.objects.filter(**msg_query2).values_list("id", flat=True))

    # 需要推送的所有手机号集合
    required_mobile_set = set()

    if ding_cron_obj:
        push_range_py = json.loads(ding_cron_obj.push_range)
        receiver_mobile = push_range_py.get('receiver_mobile', '')
        required_mobile_set.update([s.strip() for s in receiver_mobile.split(",") if s.strip()])

        dep_ids = push_range_py.get("dep_ids", [])
        flatten_dep_ids = list(itertools.chain(*dep_ids))

        # 通过 depid 获取部门成员
        ding_user_list = CircleUsersModel.get_ding_users_by_dep_ids(dep_ids=flatten_dep_ids)
        required_mobile_set.update([dep_user["phone_number"] for dep_user in ding_user_list])

    # (1): 不能仅通过历史记录来推送(因为历史记录会迁移)
    #      先从推送记录中获取，没有的再批量推送
    log_fields = ("msg_uid", "receiver_mobile", 'ding_msg_id', 'is_done')
    log_query = dict(ding_msg_id__in=required_message_ids, is_del=False)
    queryset = DingMsgPushLogModel.objects.filter(**log_query).values(*log_fields)
    logger.info("send_periodic_ding_message => queryset111 Count: %s, log_query: %s", queryset.count(), log_query)

    # 注意：
    # (1.1) 历史记录可能包含本次不需要推送的人员
    log_queryset = [item for item in queryset if item['receiver_mobile'] in required_mobile_set]
    # (1.2) 去除定时推送中已成功推送的实名问卷（未推送成功的问卷继续推送）
    # 2023.12.05 实名问卷已填写的不用推送, 其他即使实名未填写正常推送
    real_survey_done_mobiles = {
        item['receiver_mobile'] for item in queryset
        if item['ding_msg_id'] in real_survey_message_ids and item['is_done']
    }

    mq_step_size = 20  # 分片异步推送(size太大会推送是失败)
    msg_uid_list = [item['msg_uid'] for item in log_queryset if item['receiver_mobile'] not in real_survey_done_mobiles]
    sharding_msg_uid_list = [msg_uid_list[i: i + mq_step_size] for i in range(0, len(msg_uid_list), mq_step_size)]
    logger.info("send_periodic_ding_message => log_queryset Count: %s, log_query: %s", len(msg_uid_list), log_query)

    # 如果存在历史记录, 优先使用提醒(减少log入库), 批量发送
    if settings.IS_DOCKER:
        # K8S 环境 可能不适合多线程(猜测)
        logger.info("send_periodic_ding_message => settings.IS_DOCKER: %s, Docker to Push", settings.IS_DOCKER)
        for chunk_list in sharding_msg_uid_list:
            send_ding_message.delay(chunk_list)
    else:
        logger.info("send_periodic_ding_message => settings.IS_DOCKER: %s, Ecs to Push", settings.IS_DOCKER)
        pool = ThreadPool(processes=os.cpu_count() // 1 or 1)
        func = (lambda kw: send_ding_message.delay(**kw))
        iterable = [dict(msg_uid_list=chunk_uids, alert=True) for chunk_uids in sharding_msg_uid_list]
        pool.map(func, iterable=iterable)
        pool.close()
        pool.join()

    # (2): 其次异步批量推送(未推送过的人员)
    log_mobile_set = {item['receiver_mobile'] for item in log_queryset}
    new_mobile_list = list(required_mobile_set - log_mobile_set)  # 剩余没有发送的手机号
    message_id = required_message_ids[0]  # 即使多个 message_id, 也对应同一个推送的消息体
    message_obj = DingMessageModel.objects.filter(id=message_id, is_del=False).select_related("app").first()
    app_token = message_obj.app.app_token

    SendDingMessageByDepartmentApi().bulk_send_ding_messages(
        msg_body=dict(
            message_id=message_id, app_token=app_token,
            source=3, is_cached=False, mq_delivery_size=mq_step_size,
        ),
        mobile_list=new_mobile_list
    )
    logger.info("send_periodic_ding_message => 异步批量推送 Count: %s", len(new_mobile_list))


