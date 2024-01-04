import json
import traceback
from django.db import connections

from config.celery import celery_app
from circle.models import CircleActionLogModel, CircleMessageBodyModel
from ding_talk.models import DingAppTokenModel
from fosun_circle.libs.log import task_logger as logger


@celery_app.task
def notify_star_or_comment(is_cron=False, **kwargs):
    """
    :param is_cron: bool, 是否是定时任务
    :param kwargs:
    :return:
    """
    logger.info("notify_star_or_comment ==>> is_cron:%s, kwargs:%s", is_cron, kwargs)

    if not is_cron:
        # 评论或点赞即时通知
        queryset = CircleActionLogModel.create_objects(**kwargs)
        # 非定时任务的就立即推送
        queryset = [obj for obj in queryset if obj.push_strategy == 1]
    else:
        # 定时通知(早上九点推送)
        filter_kw = dict(push_strategy=2, is_del=False, is_anonymous=False, is_pushed=False)
        queryset = CircleActionLogModel.objects.filter(**filter_kw).all()

        # 已经删除的帖子不需要通知
        conn = connections["bbs_user"]
        cursor = conn.cursor()
        circle_ids_str = ",".join([str(obj.circle_id) for obj in queryset if obj.circle_id])

        if circle_ids_str:
            cursor.execute('SELECT id FROM "starCircle_starcircle" where id in (%s) and is_delete=true' % circle_ids_str)
            deleted_circle_ids = [item[0] for item in cursor.fetchall()]
        else:
            deleted_circle_ids = []

        CircleActionLogModel.objects.filter(circle_id__in=deleted_circle_ids).update(is_del=True)

        # 需要发送的筒子的帖子
        queryset = [obj for obj in queryset if obj.circle_id not in deleted_circle_ids]

    for action_obj in queryset:
        if action_obj.is_anonymous or action_obj.is_pushed:
            continue

        try:
            app_obj = DingAppTokenModel.objects.filter(app_name="星圈", is_del=False).first()
            data = CircleMessageBodyModel.send_ding_message(
                message_id=action_obj.message_id,
                receiver_mobile=action_obj.mobile,
                app_token=app_obj.app_token,
                url_params=json.loads(action_obj.url_params) if action_obj.url_params else None
            )

            if data.get("data", {}).get("code") == 200:
                CircleActionLogModel.objects.filter(id=action_obj.id).update(is_pushed=True)

            logger.info("notify_star_or_comment ==>> Send Dingding ret:%s", data)
        except Exception as e:
            logger.error("notify_star_or_comment ==>> err: %s", e)
            logger.error(traceback.format_exc())
