import os, sys
import django

os.environ.setdefault("APP_ENV", "PROD")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()

from datetime import datetime
from ding_talk.models import DingMsgPushLogModel, DingMessageModel
from users.models import CircleUsersModel
from fosun_circle.libs.utils.snow_flake import Snowflake


def create_ding_msg_log_by_no_mq(ihcm_survey_id, dep_id="root"):
    ding_msg = DingMessageModel.objects.filter(ihcm_survey_id=ihcm_survey_id).first()

    if not ding_msg:
        return

    # 已经存在的记录
    ding_msg_id = ding_msg.id
    ding_msg_log_queryset = DingMsgPushLogModel.objects\
        .filter(ding_msg_id=ding_msg_id)\
        .values_list("receiver_mobile", flat=True)
    existed_mobile_set = set(ding_msg_log_queryset)

    # 全员发送
    ding_msg_log_list = []
    user_queryset = CircleUsersModel.get_ding_users_by_dep_ids(dep_ids=[dep_id])
    # user_queryset = [dict(phone_number='13601841820', ding_job_code=None)]

    for user_item in user_queryset:
        mobile = user_item["phone_number"]
        ding_job_code = user_item["ding_job_code"]

        msg_log_item = dict(
            ding_msg_id=ding_msg_id, send_time=datetime.now(),
            receiver_mobile=mobile, receiver_job_code=ding_job_code,
            is_success=True, msg_uid=str(Snowflake(1, 1).get_id()),
        )

        if mobile not in existed_mobile_set:
            existed_mobile_set.add(mobile)
            ding_msg_log_list.append(DingMsgPushLogModel(**msg_log_item))

    DingMsgPushLogModel.objects.bulk_create(ding_msg_log_list)


if __name__ == "__main__":
    create_ding_msg_log_by_no_mq(ihcm_survey_id=7)



