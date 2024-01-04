import json
import os.path
import random
import time
import traceback
from multiprocessing.dummy import Pool as ThreadPool

import faker
import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from ding_talk.models import DingMsgPushLogModel, DingMessageModel


def recall_survey_with_sent(survey_id):
    api = "https://fosunapi.focuth.com/api/v1/circle/ding/apps/message/recall"
    data = {
        "app_token": "qe7mbtSqMYkCoxyRAZQdw8VObradTtRYFnKQ6VPzKyS5wtxFmgDvvzMDvG4ThTjP+dc2u3W8n7hd6wEZwbKmB105"
                     "nvIfRzNjCKttpirKe8RXnyE9HpnzpRBM6rzNPEBgdoCCTtf6CyEX1tkrHsC+kddmO3been45Td0NOJ0UfvU="
    }

    ding_msg_obj = DingMessageModel.objects.get(ihcm_survey_id=survey_id)  # 确定只有一个
    queryset = DingMsgPushLogModel.objects.filter(ding_msg_id=ding_msg_obj.id)

    for log_obj in queryset:
        try:
            task_id = log_obj.task_id
            msg_uid = log_obj.msg_uid

            body = dict(task_id=task_id, msg_uid=msg_uid, **data)
            res = requests.post(api, data=body)
            # res = requests.post(api, data=json.dumps(body), headers={"Content-Type": "application/json"})
            print(task_id, msg_uid, res.json())
        except Exception as e:
            print(traceback.format_exc())


if __name__ == "__main__":
    recall_survey_with_sent(survey_id=5)
