import json
import os.path
import traceback

import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from ding_talk.models import DingMsgPushLogModel, DingMessageModel
from fosun_circle.apps.ding_talk.tasks.task_send_ding_message import send_ding_message
from users.models import CircleUsersModel


def get_survey_ding_body(survey_id):
    return {
            "app_token": "qe7mbtSqMYkCoxyRAZQdw8VObradTtRYFnKQ6VPzKyS5wtxFmgDvvzMDvG4ThTjP+dc2u3W8n7hd6wEZwbKmB105"
                         "nvIfRzNjCKttpirKe8RXnyE9HpnzpRBM6rzNPEBgdoCCTtf6CyEX1tkrHsC+kddmO3been45Td0NOJ0UfvU=",
            "msg_title": "复星员工产品体验满意度调查",
            "msg_media": "@lADPDf0i3CN8ORXNASzNAu4",
            "msg_type": 6,
            "msg_text": "请根据您的亲身感受填写以下问卷，我们将抽选6位提供宝贵建议的员工，送出价值100RMB/人 的甄选卡",
            "receiver_mobile": "",
            "msg_url": "https://fosun.focuth.com/exerland/questionnaireDetail?questionnaire_id=5",
            "msg_pc_url": "https://fosun.focuth.com/exerland/questionnaireDetail?questionnaire_id=5",
            "source": 2,
            "ihcm_survey_id": survey_id,
        }


def send_survey(survey_id):
    """ 第一次全发或补发 """
    api = "https://fosunapi.focuth.com/api/v1/circle/ding/apps/message/send"
    ding_msg_obj = DingMessageModel.objects.get(ihcm_survey_id=survey_id)  # 确定只有一个
    queryset = DingMsgPushLogModel.objects.filter(ding_msg_id=ding_msg_obj.id, is_del=False)\
        .values_list("receiver_mobile", flat=True)
    existed_mobiles_set = set(queryset)

    user_queryset = CircleUsersModel.objects.filter(is_del=False).all()

    bulk_mobile_list = []
    slice_mobile_list = []

    for user in user_queryset:
        mobile = user.phone_number

        if mobile in existed_mobiles_set:
            continue

        slice_mobile_list.append(mobile)

        if len(slice_mobile_list) == 100:
            bulk_mobile_list.append(slice_mobile_list[:])
            slice_mobile_list = []

    # 最后一次可能没有100
    bulk_mobile_list.append(slice_mobile_list)

    count = 0
    for index, mobile_list in enumerate(bulk_mobile_list, 1):
        if not mobile_list:
            print("mobile_list is empty")
            continue

        data = get_survey_ding_body(survey_id)
        data["receiver_mobile"] = ",".join(mobile_list)

        try:
            res = requests.post(api, data=json.dumps(data), headers={"Content-Type": "application/json"})

            count += len(mobile_list)
            print(index, count, res.json())
        except Exception as e:
            print(traceback.format_exc())


def alert_survey_by_undone(survey_id):
    """ 问卷未完成的二次提醒 """
    api = "https://fosunapi.focuth.com/api/v1/circle/ding/apps/message/again/alert"
    ding_msg_obj = DingMessageModel.objects.get(ihcm_survey_id=survey_id)  # 确定只有一个
    queryset = DingMsgPushLogModel.objects\
        .filter(
            ding_msg_id=ding_msg_obj.id, is_del=False, is_done=False,
            # receiver_mobile__in=["13601841820", "15606100808", "18221734105", "18715124118"]
        ).values_list("msg_uid", flat=True)

    max_step = 50
    bulk_msg_uid_list = []
    slice_msg_uid_list = []

    for msg_uid in queryset:
        slice_msg_uid_list.append(msg_uid)

        if len(slice_msg_uid_list) == max_step:
            bulk_msg_uid_list.append(slice_msg_uid_list[:])
            slice_msg_uid_list = []

    # 最后一次可能没有 max_step
    bulk_msg_uid_list.append(slice_msg_uid_list)

    count = 0
    for msg_uid_list in bulk_msg_uid_list:
        count += len(msg_uid_list)
        print("alert_survey_by_undone -> count:%s" % count)

        if msg_uid_list:
            r = send_ding_message.delay(msg_uid_list=msg_uid_list, alert=True)
            print(r)


if __name__ == "__main__":
    # send_survey(survey_id=5)
    alert_survey_by_undone(survey_id=5)
