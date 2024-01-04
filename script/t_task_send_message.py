import os, sys
import logging
import django
from django.db.models import Q

logging.warning("Script Path: %s\n", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# os.environ.setdefault("APP_ENV", "PROD")
# os.environ.setdefault("DEPLOY", "DOCKER")
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

import json
import requests

from fosun_circle.apps.ding_talk.tasks.task_send_ding_message import send_ding_message
from fosun_circle.apps.ding_talk.tasks.task_compensation_policy import compensate_message_push
from ding_talk.models import DingMsgPushLogModel, DingMessageModel
from users.models import CircleUsersModel

from kombu import Connection, Queue, Exchange, Consumer
from kombu.mixins import ConsumerMixin, ConsumerProducerMixin

_logger = logging.getLogger('t_task_send_message')
f_handler = logging.StreamHandler()
f_handler.setFormatter(logging.Formatter('%(asctime)s-%(name)s-%(filename)s-[line:%(lineno)d]-%(levelname)s-[日志信息]:-%(message)s'))
_logger.addHandler(f_handler)
_logger.setLevel(logging.DEBUG)


def get_message_ids(title):
    """ 钉钉推送失败， 重推 """
    msg_queryset = DingMessageModel.objects\
        .filter(msg_title__icontains=title, is_del=False)\
        .values_list('id', flat=True)

    return list(msg_queryset)


def repush_ding_messages(title, step_size=1):
    message_ids = get_message_ids(title)
    log_queryset = DingMsgPushLogModel.objects\
        .filter(ding_msg_id__in=message_ids, is_success=False, is_del=False)\
        .values_list('msg_uid', flat=True)

    msg_uid_list = list(log_queryset)
    total_count = len(msg_uid_list)
    _logger.info("【%s】MessageIds: %s, totalCount: %s", title, message_ids, total_count)

    # 分片异步推送
    step_size = step_size
    sharding_msg_uid_list = [msg_uid_list[i: i + step_size] for i in range(0, len(msg_uid_list), step_size)]

    for index, msg_uids in enumerate(sharding_msg_uid_list, 1):
        log_args = (index, total_count, len(msg_uids), msg_uids)
        _logger.info("Repush Message => Index: %s, totalCount: %s, Current Cnt: %s, msg_uids: %s", *log_args)
        send_ding_message.delay(msg_uid_list=msg_uids, alert=True)


def repush_messages_by_api(title, dep_ids):
    ding_user_list = CircleUsersModel.get_ding_users_by_dep_ids(dep_ids)
    mobile_list = [item['phone_number'] for item in ding_user_list]
    _logger.info("repush_messages_by_api => get_ding_users_by_dep_ids: %s", len(mobile_list))

    # 已经推送的
    message_ids = get_message_ids(title)
    log_queryset = DingMsgPushLogModel.objects.filter(ding_msg_id__in=message_ids, is_success=True).values_list('receiver_mobile', flat=True)

    mobile_list = list(set(mobile_list) - set(log_queryset))
    _logger.info("repush_messages_by_api => filter mobile_list: %s", len(mobile_list))
    print('13701865840' in mobile_list)
    # return

    step_size = 50

    headers = {"Content-Type": "application/json"}
    data = dict(
        app_token="qe7mbtSqMYkCoxyRAZQdw8VObradTtRYFnKQ6VPzKyS5wtxFmgDvvzMDvG4ThTjP+dc2u3W8n7hd6wEZwbKmB105nvIfRzNjCKttpirKe8RXnyE9HpnzpRBM6rzNPEBgdoCCTtf6CyEX1tkrHsC+kddmO3been45Td0NOJ0UfvU=",
        batch_mobile_path=None,
        dep_ids=[],
        ihcm_survey_id=0,
        is_test=False,
        msg_media="@lALPDf0i8MYLAYLNARDNAu4",
        msg_pc_url="https://ui-circle.fosun.com/exerland/pushDynamicDetail/28868?title=LANVIN Family Sale 复星员工福利专场",
        msg_text="地点：BFC外滩金融中心商场6F Now空间\n时间：7月27日—28日\n周四至周五 10：00 ——19：00（最后入场时间18：30）入场前需出示复星钉钉页面及预约凭证\n谢绝携包入场，不设寄包处；\n现场请勿拍摄照片及视频；\n本场此为微瑕疵商品专场，售出商品不退不换；\n每位员工限购皮具5件，鞋类5件，成衣10件；\n每场次均有补货，请务必扫码预约入场时段，错峰购物！",
        msg_title="LANVIN Family Sale 复星员工福利专场",
        msg_type=6,
        msg_url="https://ui-circle.fosun.com/exerland/pushDynamicDetail/28868?title=LANVIN Family Sale 复星员工福利专场",
        receiver_mobile='',
        source=3
    )
    api = 'https://circle.fosun.com/api/v1/circle/ding/apps/message/send/by/department'

    # api = 'https://circle.fosun.com/api/v1/circle/ding/apps/message/send'
    # data = dict(
    #     app_token="qe7mbtSqMYkCoxyRAZQdw8VObradTtRYFnKQ6VPzKyS5wtxFmgDvvzMDvG4ThTjP+dc2u3W8n7hd6wEZwbKmB105nvIfRzNjCKttpirKe8RXnyE9HpnzpRBM6rzNPEBgdoCCTtf6CyEX1tkrHsC+kddmO3been45Td0NOJ0UfvU=",
    #     batch_mobile_path=None,
    #     dep_ids=[],
    #     ihcm_survey_id=0,
    #     is_test=False,
    #     msg_media="@lALPDf0i8MYLAYLNARDNAu4",
    #     msg_pc_url="https://ui-circle.fosun.com/exerland/pushDynamicDetail/28868?title=LANVIN Family Sale 复星员工福利专场",
    #     msg_text="xxx地点：BFC外滩金融中心商场6F Now空间\n时间：7月27日—28日\n周四至周五 10：00 ——19：00（最后入场时间18：30）\u000b\u000b入场前需出示复星钉钉页面及预约凭证\n谢绝携包入场，不设寄包处；\n现场请勿拍摄照片及视频；\n本场此为微瑕疵商品专场，售出商品不退不换；\n每位员工限购皮具5件，鞋类5件，成衣10件；\n每场次均有补货，请务必扫码预约入场时段，错峰购物！",
    #     msg_title="LANVIN Family Sale 复星员工福利专场",
    #     msg_type=6,
    #     msg_url="https://ui-circle.fosun.com/exerland/pushDynamicDetail/28868?title=LANVIN Family Sale 复星员工福利专场",
    #     receiver_mobile='',
    #     source=3
    # )

    # mobile_list = ['13601841820']
    for i in range(0, len(mobile_list), step_size):
        start = i
        stop = i + step_size
        receiver_mobiles = mobile_list[start:stop]

        log_args = (start, stop, len(receiver_mobiles))
        _logger.info("bulk_send_ding_messages => start: %s, stop: %s, Cnt: %s", *log_args)

        try:
            data['receiver_mobile'] = ",".join(receiver_mobiles)
            r = requests.post(api, data=json.dumps(data), headers=headers)
            _logger.info('通过API重新推送钉钉消息：Res: %s', r.json())
        except Exception as e:
            pass


def recall_ding_message(title, start_pk=None):
    message_ids = get_message_ids(title)
    log_queryset = DingMsgPushLogModel.objects.filter(ding_msg_id__in=message_ids, is_success=True, is_del=False)

    if start_pk:
        log_queryset = log_queryset.filter(pk__gte=start_pk).all()

    log_queryset = log_queryset.values('msg_uid', 'receiver_mobile')
    log_item_list = list(log_queryset)
    _logger.info("【%s】需要被撤回的数量: %s", title, len(log_item_list))

    app_token = "qe7mbtSqMYkCoxyRAZQdw8VObradTtRYFnKQ6VPzKyS5wtxFmgDvvzMDvG4ThTjP+dc2u3W8n7hd6wEZwbKmB105nvIfRzNjCKttpirKe8RXnyE9HpnzpRBM6rzNPEBgdoCCTtf6CyEX1tkrHsC+kddmO3been45Td0NOJ0UfvU="
    x_auth = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjozMDcwLCJ1c2VybmFtZSI6IjEzNjAxODQxODIwIiwiZXhwIjoxNjkwODY4MDE2LCJlbWFpbCI6ImRpbmd4dEBmb3N1bi5jb20iLCJtb2JpbGUiOiIxMzYwMTg0MTgyMCJ9.onZOXLoQ4_2lCBEVZjPWyDAeCOYq3TT-xI3yvhfiW9E'

    for index, item in enumerate(log_item_list, 1):
        msg_uid = item['msg_uid']
        mobile = item['receiver_mobile']
        resp = requests.post(
            "https://circle.fosun.com/api/v1/circle/ding/apps/message/recall",
            data=json.dumps(dict(app_token=app_token, msg_uid=msg_uid)),
            headers={"Content-Type": "application/json", "X-Auth": x_auth}
        )
        _logger.info('Index: %s, Mobile: %s, msg_uid: %s 被撤回成功, Ret: %s', index, mobile, msg_uid, resp.json())


if __name__ == "__main__":
    # 修改PG配置为外网
    step = 1
    name = '当我们吐槽职场时，到底是在吐槽啥？'
    # repush_ding_messages(title=name, step_size=step)
    # repush_messages_by_api(name, dep_ids=['root'])

    # recall_ding_message(name, start_pk=823674)

    compensate_message_push()
