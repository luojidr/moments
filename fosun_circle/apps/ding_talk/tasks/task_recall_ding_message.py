import json
import traceback
from datetime import datetime
from operator import itemgetter
from itertools import groupby

from config.celery import celery_app
from fosun_circle.libs.log import task_logger as logger
from ding_talk.models import DingMsgPushLogModel, DingAppTokenModel, DingMsgRecallLogModel
from fosun_circle.core.ding_talk.open_api import DingTalkMessageOpenApi


@celery_app.task(ignore_result=False)
def recall_ding_message(task_id=None, app_id=None, msg_uid=None, **kwargs):
    """ 单个或批量消息撤回 """
    logger.info("Task recall_ding_message => 消息撤回 task_id: %s, app_id: %s, msg_uid: %s", task_id, app_id, msg_uid)

    task_id = task_id or ""
    msg_uid = msg_uid or ""

    if not task_id and not msg_uid:
        raise ValueError

    is_recall_ok = False
    app_obj = DingAppTokenModel.objects.get(id=app_id, is_del=False)
    log_queryset = DingMsgPushLogModel.objects.filter(is_del=False).all()

    if task_id:
        log_queryset = log_queryset.filter(task_id=task_id).all()

    if msg_uid:
        log_queryset = log_queryset.filter(msg_uid=msg_uid).all()

    log_queryset2 = log_queryset.order_by("-ding_msg_id").values("ding_msg_id", "id", "msg_uid")

    try:
        ding_service = DingTalkMessageOpenApi(
            corp_id=app_obj.corp_id, app_key=app_obj.app_key,
            app_secret=app_obj.app_secret, agent_id=app_obj.agent_id
        )
        recall_ret = json.dumps(ding_service.recall(msg_task_id=task_id))
        is_recall_ok = True
    except Exception as e:
        logger.error("Task recall_ding_message => 消息撤回 err1: %s", e)
        exc_msg = traceback.format_exc()
        logger.error(exc_msg)
        recall_ret = exc_msg[-1500:]

    for ding_msg_id, iterator in groupby(log_queryset2, key=itemgetter("ding_msg_id")):
        log_list = list(iterator)
        recall_time = datetime.now()
        msg_uid = log_list[0]["msg_uid"] if len(log_list) else msg_uid

        try:
            query_kwargs = dict(ding_msg_id=ding_msg_id, task_id=task_id, app_id=app_id, msg_uid=msg_uid)
            recall_obj = DingMsgRecallLogModel.objects.filter(is_del=False, **query_kwargs).first()
            recall_kwargs = dict(
                app_id=app_id, ding_msg_id=ding_msg_id, task_id=task_id, recall_time=recall_time,
                msg_uid=msg_uid, recall_cnt=len(log_list), is_recall_ok=is_recall_ok, recall_ret=recall_ret
            )

            if recall_obj is None:
                DingMsgRecallLogModel.objects.create(**recall_kwargs)
            else:
                recall_obj.save_attributes(force_update=True, **recall_kwargs)

            log_args = (task_id, ding_msg_id, recall_ret)
            logger.info("Task recall_ding_message => 消息撤回 task_id<%s>, ding_msg_id: %s, recall_ret: %s", *log_args)
        except Exception as e:
            logger.error("Task recall_ding_message => 消息撤回 err2: %s", e)
            logger.error(traceback.format_exc())
    else:
        is_recall_ok and log_queryset.update(is_recall=True, recall_time=datetime.now())

