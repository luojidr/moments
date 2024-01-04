import traceback
from datetime import datetime, timedelta

from django.db.models import F

from config.celery import celery_app
from fosun_circle.libs.log import task_logger as logger
from ding_talk.models import DingMsgPushLogModel
from fosun_circle.apps.ding_talk.tasks.task_send_ding_message import send_ding_message


@celery_app.task(ignore_result=True)
def compensate_message_push(**kwargs):
    """ 建议使用 celery: raise self.retry 方式进行消息的重试策略 """
    now = datetime.now() + timedelta(hours=8)
    logger.info('==>>> compensate_message_push start at %s', now)

    # 查询最近一天推送失败的消息
    query = dict(
        is_del=False, is_success=False, max_times__lt=3,
        create_time__gt=now.date().strftime("%Y-%m-%d %H:%M:%S"),
        create_time__lt=(now.date() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
    )

    try:
        queryset = DingMsgPushLogModel.objects.filter(**query).values('msg_uid', 'id')

        for item in queryset:
            push_id = item['id']
            msg_uid = item['msg_uid']

            send_ding_message.delay(msg_uid_list=[msg_uid])
            DingMsgPushLogModel.objects.filter(id=push_id).update(max_times=F('max_times') + 1)
    except Exception as e:
        logger.error("compensate_message_push err: %s", e)
        logger.error(traceback.format_exc())

