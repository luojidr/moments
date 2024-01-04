import re
import os
import time
import traceback
from datetime import datetime, timedelta
from operator import itemgetter
from itertools import groupby

from django.contrib.auth import get_user_model

from config.celery import celery_app
from .message_converter import MessageConverter
from fosun_circle.libs.log import task_logger as logger
from ding_talk.models import DingMsgPushLogModel, DingMessageModel
from fosun_circle.constants.enums.ding_msg_type import DingMsgTypeEnum
from fosun_circle.core.ding_talk.open_api import DingTalkMessageOpenApi


@celery_app.task(ignore_result=True)
def send_ding_message(msg_uid_list=None, alert=False, **kwargs):
    start_time = time.time()
    msg_uid_list = msg_uid_list or []
    log_msg_fields = ["msg_uid", "receiver_mobile", "receiver_job_code", "ding_msg_id"]
    log_query = dict(msg_uid__in=msg_uid_list)
    # not alert and log_query.update(is_success=False)

    log_msg_queryset = DingMsgPushLogModel.objects.filter(**log_query).values(*log_msg_fields).order_by("-ding_msg_id")
    logger.info("send_ding_message => log_msg_queryset: %s, msg_uid_list:%s", len(log_msg_queryset), msg_uid_list)

    # 钉钉微应用
    ding_msg_ids = list({item["ding_msg_id"] for item in log_msg_queryset})
    msg_queryset = DingMessageModel.objects.filter(id__in=ding_msg_ids, is_del=False).select_related("app")
    msg_mapping_dict = {msg_obj.id: msg_obj for msg_obj in msg_queryset}

    # 同应用消息分组
    for ding_msg_id, iterator in groupby(log_msg_queryset, key=itemgetter("ding_msg_id")):
        log_msg_list = list(iterator)
        push_count = len(log_msg_list)
        ding_msg = msg_mapping_dict.get(ding_msg_id)

        start_time2 = time.time()
        _log_args = (ding_msg_id, ding_msg, push_count)
        logger.info("send_ding_message => ding_msg_id: %s, ding_msg: %s, push_count: %s", *_log_args)

        if not ding_msg:
            continue

        app_obj = ding_msg.app
        msg_type_int = ding_msg.msg_type
        msg_type_mapper = dict(DingMessageModel.MSG_TYPE_CHOICES)
        ret = dict(errcode=500, errmsg="failed", task_id="", request_id="")

        ding_body_kwargs = {}
        msg_type = msg_type_mapper.get(msg_type_int)
        api_init_kwargs = dict(
            corp_id=app_obj.corp_id, app_key=app_obj.app_key,
            app_secret=app_obj.app_secret, agent_id=app_obj.agent_id,
        )

        if ding_msg.source == 1 and msg_type == DingMsgTypeEnum.MARKDOWN.msg_type:
            # 星喜积分消息
            ding_body_kwargs = MessageConverter.get_body_markdown_to_oa(ding_msg_object=ding_msg)
            msg_type = DingMsgTypeEnum.OA.msg_type if ding_body_kwargs else msg_type

        if not ding_body_kwargs:
            # 先保证 oa、markdown 的消息正确发送
            content_regex = re.compile(r"</br>", re.S | re.M)
            content = content_regex.sub("\n", ding_msg.msg_text or "")
            ding_body_kwargs.update(
                title=ding_msg.msg_title, media_id=ding_msg.msg_media or None, content=content,
                message_url=ding_msg.msg_url, pc_message_url=ding_msg.msg_pc_url,
            )

        # 推送人员列表
        push_msg_uid_list = [log_item["msg_uid"] for log_item in log_msg_list]
        mobile_list = [log_item["receiver_mobile"] for log_item in log_msg_list]
        push_job_code_list = [item["receiver_job_code"] for item in log_msg_list if item["receiver_job_code"]]

        # 推送记录中没有 jobCode, 重新查询
        if len(push_job_code_list) != len(mobile_list):
            User = get_user_model()
            push_job_code_list = User.get_job_code_list(mobile_list=mobile_list)
            logger.info("send_ding_message => User: %s, push_job_code_list:%s", User, push_job_code_list)

        try:
            userid_list = push_job_code_list
            body_kwargs = dict(ding_body_kwargs, author=app_obj.app_name)

            ding_service = DingTalkMessageOpenApi(msg_type=msg_type, **api_init_kwargs)
            task_id = ding_service.async_send(body_kwargs=body_kwargs, userid_list=userid_list)
            ret.update(errcode=0, errmsg="ok", task_id=str(task_id))
        except Exception as e:
            logger.error("Celery Task[send_ding_message] send err: %s", e)
            exc_msg = traceback.format_exc()
            logger.error(exc_msg)
            ret.update(errmsg=exc_msg[-1000:])
        finally:
            push_count = len(push_msg_uid_list)
            logger.info("send_ding_message => push_msg_uid_list: %s, Count: %s", push_msg_uid_list, push_count)
            logger.info("send_ding_message => DingTalk Api Cost time: %s", time.time() - start_time2)

            try:
                update_kwargs = dict(
                    is_success=int(ret["errcode"]) == 0, task_id=ret["task_id"],
                    traceback=ret["errmsg"], request_id=ret["request_id"]
                )

                now = datetime.now()  # datetime
                if os.environ.get("DEPLOY") == 'DOCKER':
                    now = now + timedelta(hours=8)

                update_kwargs["is_success"] and update_kwargs.update(receive_time=now)
                DingMsgPushLogModel.objects.filter(msg_uid__in=push_msg_uid_list).update(**update_kwargs)
            except Exception as e:
                logger.error("Celery Task[send_ding_message] update log err: %s", e)
                logger.error(traceback.format_exc())

            log_args = (push_job_code_list, ding_body_kwargs, ret, time.time() - start_time)
            logger.info("send_ding_message => Push DingTalk UserIds: %s, \n"
                        "body_kwargs:%s, \nresult: %s, Task All CostTime: %s", *log_args)





