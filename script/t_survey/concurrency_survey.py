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

from ding_talk.models import DingMsgPushLogModel

fa = faker.Faker(locale='zh_CN')


def get_survey_info():
    log_msg_queryset = DingMsgPushLogModel.objects\
        .filter(ding_msg_id=3, is_del=False)\
        .select_related("ding_msg")\
        .values("receiver_mobile", "ding_msg__ihcm_survey_id")

    return list(log_msg_queryset)


def get_select_choice(multi=False):
    ret = random.choice([True, False, False, True, False, True, False, True, True, False, True])
    return ret


def test_save_survey(kwargs):
    mobile = kwargs["mobile"]
    questionnaire_id = kwargs["questionnaire_id"]

    save_api = "https://ihcm.fosun.com/fosun/v1.0/fosun_vote/survey/answer/save?mobile={mobile}"
    done_api = "https://fosunapi.focuth.com/api/v1/circle/questionnaire/vote/done"
    headers = {"Content-Type": "application/json"}

    submit_data = {
        "questionnaire_id": 4,
        "title": "星圈使用场景调研(Test)",
        "questions": [
            {
                "question_id": 13,
                "is_required": False,
                "topic_id": 4,
                "title": "每周上几次星圈？",
                "img_url": "",
                "desc": "",
                "options": [
                    {
                        "option_id": 0,
                        "title": "",
                        "order": 1,
                        "answer": fa.paragraph(nb_sentences=3, variable_nb_sentences=True, ext_word_list=None),
                        "min_value": "",
                        "max_value": "10"
                    }
                ]
            },

            {
                "question_id": 14,
                "is_required": False,
                "topic_id": 3,
                "title": "你心里的复星同事吧是怎样的？",
                "img_url": "",
                "desc": "",
                "options": [
                    {
                        "option_id": 0,
                        "title": "",
                        "order": 1,
                        "answer": fa.paragraph(nb_sentences=3, variable_nb_sentences=True, ext_word_list=None),
                        "min_value": "",
                        "max_value": "10"
                    }
                ]
            },

            {
                "question_id": 15,
                "is_required": False,
                "topic_id": 5,
                "title": "对星圈目前的满意度感受是几份？",
                "img_url": "",
                "desc": "",
                "options": [
                    {
                        "option_id": 0,
                        "title": "",
                        "order": 1,
                        "answer": random.choice(list(range(1, 11))),
                        "min_value": "",
                        "max_value": "10"
                    }
                ]
            },

            {
                "question_id": 16,
                "is_required": False,
                "topic_id": 2,
                "title": "在星圈上主要做的事情有哪些？",
                "img_url": "",
                "desc": "",
                "options": [
                    {
                        "option_id": 22,
                        "order": 10,
                        "title": "看八卦吐槽",
                        "answer": True,
                        "min_value": "",
                        "max_value": "10"
                    },

                    {
                       "option_id": 23,
                       "order": 10,
                       "title": "参与活动",
                       "answer": False,
                       "min_value": "",
                       "max_value": "10"
                    },

                    {
                       "option_id": 24,
                       "order": 10,
                       "title": "发帖",
                       "answer": True,
                       "min_value": "",
                       "max_value": "10"
                    },

                    {
                       "option_id": 25,
                       "order": 10,
                       "title": "点赞或评论",
                       "answer": True,
                       "min_value": "",
                       "max_value": "10"
                    },

                    {
                       "option_id": 26,
                       "order": 10,
                       "title": "发召集令",
                       "answer": True,
                       "min_value": "",
                       "max_value": "10"
                    }
                ]
            },

            {
                "question_id": 17,
                "is_required": False,
                "topic_id": 1,
                "title": "最想在星圈上收获什么？",
                "img_url": "",
                "desc": "",
                "options": [
                    {
                        "option_id": 27,
                        "order": 10,
                        "title": "真实透明的信息",
                        "answer": False,
                        "min_value": "",
                        "max_value": "10"
                    },

                    {
                        "option_id": 28,
                        "order": 10,
                        "title": "提建议,一起升级员工体验",
                        "answer": True,
                        "min_value": "",
                        "max_value": "10"
                    },

                    {
                        "option_id": 29,
                        "order": 10,
                        "title": "参与各种活动",
                        "answer": False,
                        "min_value": "",
                        "max_value": "10"
                    },

                    {
                        "option_id": 30,
                        "order": 10,
                        "title": "只想做个路人",
                        "answer": False,
                        "min_value": "",
                        "max_value": "10"
                    }
                ]
            }
        ],
        "desc": "请根据您的亲身感受填写以下问卷，非常感谢您的支持和参与。",
        "status": 3,
        "status_cn": "open"
    }

    for i in range(3):
        try:
            resp = requests.post(save_api.format(mobile=mobile), data=json.dumps(submit_data), headers=headers)
            result = resp.json().get("result", {})
            # print(result)

            if result.get("code") == 200:
                break
        except:
            traceback.format_exc()

    for i in range(3):
        try:
            resp = requests.post(done_api,
                                 data=json.dumps(dict(mobile=mobile, questionnaire_id=questionnaire_id)),
                                 headers=headers
                                 )
            result = resp.json()
            # print(result)

            if result.get("code") == 200:
                break
        except:
            pass


def test_concurrency():
    step_size = 200
    survey_users = get_survey_info()

    start_time = time.time()
    total_cnt = len(survey_users)
    pool = ThreadPool()

    for i in range(0, len(survey_users), step_size):
        slice_survey_users = survey_users[i:i + step_size]
        iterable = [
            dict(
                mobile=item["receiver_mobile"],
                questionnaire_id=item["ding_msg__ihcm_survey_id"]
            )
            for item in slice_survey_users
        ]

        tmp_ts = time.time()
        pool.map(test_save_survey, iterable=iterable)
        tmp_cost = time.time() - tmp_ts
        tmp_total_cnt = len(slice_survey_users)

        print("slice save: start: %s, end: %s, size: %s, tmp_cost:%s, qps:%s" % (i, i + step_size, tmp_total_cnt, tmp_cost, tmp_total_cnt/tmp_cost))
        pass

    # pool.map(test_save_survey, iterable=[dict(mobile="13601841820", questionnaire_id=4)])
    pool.close()
    pool.join()

    cost_time = time.time() - start_time
    print("Cost time: %s, Avg time: %s" % (cost_time, cost_time * 1.0 / total_cnt))


test_concurrency()

