import os, sys
import django

os.environ.setdefault("APP_ENV", "PROD")
os.environ.setdefault("DEPLOY", "DOCKER")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()

import logging
import traceback
import requests
from django.db import connections
from ding_talk.models import DingMsgPushLogModel, DingMessageModel
from fosun_circle.apps.ding_talk.tasks.task_recall_ding_message import recall_ding_message

HOST = "https://circle.fosun.com/"
logger = logging.getLogger('t_recall_ding_message')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
logger.addHandler(ch)


def t_recall_ding_message(app_id=1, msg_title=None, task_id=None):
    msg_title = msg_title or ''
    api = '/api/v1/circle/ding/apps/message/recall/log'
    params = dict(app_id=app_id, msg_title=msg_title, task_id=task_id)
    cursor = connections['default'].cursor()

    msg_queryset = DingMessageModel.objects \
        .filter(msg_title__icontains=msg_title, is_del=False) \
        .values_list('id', flat=True)

    message_ids = list(msg_queryset)
    log_queryset = DingMsgPushLogModel.objects\
        .filter(ding_msg_id__in=message_ids, is_success=True)\
        .values_list('task_id', flat=True)
    task_id_list = list(set(log_queryset))

    for task_id in task_id_list:
        if not task_id:
            continue

        try:
            recall_ding_message.delay(task_id=task_id, app_id=app_id)
            logger.info("RecallMsgLogApi.t_recall_ding_message => 消息撤回, task_id: %s", ",".join(task_id_list))
        except Exception as e:
            logger.error("RecallMsgLogApi.t_recall_ding_message => 消息撤回 err: %s", e)
            logger.error(traceback.format_exc())


if __name__ == '__main__':
    t_recall_ding_message()
