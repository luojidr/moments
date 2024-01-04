import json
import os.path
from datetime import datetime

from django.conf import settings
from django.db import models, connections
from django.contrib.auth import get_user_model

from fosun_circle.core.db.base import BaseAbstractModel
from fosun_circle.core.okhttp.http_util import HttpUtil
from fosun_circle.constants.enums.ding_msg_type import DingMsgTypeEnum
from fosun_circle.middleware.auth_token import payload_handler, encode_handler

# action_type, desc, action_section, user_scope
ACTION_SECTIONS = [
    (1, "帖子评论", "", "通用帖子"),
    (2, "帖子点赞", "", "通用帖子"),
    (3, "评论点赞", "", "通用帖子"),
    (4, "帖子审核", "", "HR知乎"),
    (5, "HR知乎发帖提醒", "hr_scope", "HR知乎"),
    (6, "HR知乎评论与回复提醒", "", "HR知乎"),
]
ACTION_CHOICES = [item[:2] for item in ACTION_SECTIONS]


class DissFeedbackModel(BaseAbstractModel):
    STATE = [
        (0, "待处理"),
        (1, "已处理"),
        (2, "非管辖范围"),
    ]

    diss_id = models.IntegerField(verbose_name="吐槽ID", default=0)
    user_id = models.IntegerField(verbose_name="吐槽的反馈者", default=0)
    mobile = models.CharField(verbose_name="用户手机号", max_length=11, default="")
    state = models.IntegerField(verbose_name="吐槽处理状态", default=0, choices=STATE)
    remark = models.CharField(verbose_name="吐槽备注", max_length=1000, default="")
    is_snapshot = models.BooleanField(verbose_name="是否快照", default=False)

    class Meta:
        db_table = "circle_diss_feedback"
        managed = False


class DissDingPushLogModel(BaseAbstractModel):
    PUSH_STATUS = [
        (0, "失败"),
        (1, "成功"),
        (2, "未发送"),
    ]

    diss_id = models.IntegerField(verbose_name="吐槽ID", db_index=True, default=0)
    send_id = models.IntegerField(verbose_name="推送者id", default=0)
    receive_id = models.IntegerField(verbose_name="接受者id", default=2)
    push_status = models.SmallIntegerField(verbose_name="推送状态")

    class Meta:
        db_table = "circle_diss_push_log"
        managed = False


class CircleMessageBodyModel(BaseAbstractModel):
    MESSAGE_CHOICES = DingMsgTypeEnum.get_items()

    title = models.CharField(verbose_name="标题", max_length=500, default="", blank=True)
    media_id = models.CharField(verbose_name="媒体", max_length=500, default="", blank=True)
    msg_type = models.CharField(verbose_name="消息类型", max_length=100, choices=MESSAGE_CHOICES, default=0, blank=True)
    text = models.CharField(verbose_name="内容", max_length=1000, default="", blank=True)
    app_url = models.CharField(verbose_name="app链接", max_length=500, default="", blank=True)
    pc_url = models.CharField(verbose_name="pc链接", max_length=500, default="", blank=True)
    action_type = models.SmallIntegerField(verbose_name="操作类型", default=0, unique=True, choices=ACTION_CHOICES)

    class Meta:
        db_table = "circle_message_info"

    @classmethod
    def send_ding_message(cls, message_id, receiver_mobile, app_token, url_params=None):
        message_obj = cls.objects.filter(id=message_id, is_del=False).first()

        if message_obj is None:
            return

        url_params = url_params or {}
        timestamp = datetime.now().timestamp()  # 保证消息不会过滤

        if "?" in message_obj.app_url:
            jump_app_url = message_obj.app_url.format(**url_params) + "&timestamp=%s" % timestamp
        else:
            jump_app_url = message_obj.app_url.format(**url_params) + "?timestamp=%s" % timestamp

        if "?" in message_obj.pc_url:
            jump_pc_url = message_obj.pc_url.format(**url_params) + "&timestamp=%s" % timestamp
        else:
            jump_pc_url = message_obj.pc_url.format(**url_params) + "?timestamp=%s" % timestamp

        body_kwargs = dict(
            app_token=app_token,
            source=3, msg_type=6,
            msg_title=message_obj.title, msg_media=message_obj.media_id,
            msg_text=message_obj.text or "", receiver_mobile=receiver_mobile,
            msg_url=jump_app_url, msg_pc_url=jump_pc_url,
        )

        # 获取token
        user = get_user_model().objects.get(phone_number=os.environ.get('API_TICKET'))
        payload = payload_handler(user)

        req = HttpUtil("{host}/api/v1/circle/ding/apps/message/send".format(host=settings.CIRCLE_HOST))
        req.add_headers(key="Content-Type", value="application/json")
        req.add_headers(key="X-Auth", value=encode_handler(payload))
        return req.post(data=body_kwargs)


class CircleActionLogModel(BaseAbstractModel):
    PUSH_STRATEGY = [
        (1, "立即推送"),
        (2, "早上九点推送"),
    ]

    message = models.ForeignKey(to=CircleMessageBodyModel, verbose_name="应用消息", null=True, on_delete=models.DO_NOTHING)
    circle_id = models.IntegerField(verbose_name="帖子id", default=None, null=True)
    comment_id = models.IntegerField(verbose_name="评论id", default=None, null=True)
    action_type = models.SmallIntegerField(verbose_name="操作类型", default=0, choices=ACTION_CHOICES)
    action_cn = models.CharField(verbose_name="操作描述", max_length=200, default="")
    mobile = models.CharField(verbose_name="消息接收者手机号(帖子、评论)", max_length=100, default="")
    operator_mobile = models.CharField(verbose_name="操作者手机号", max_length=20, default="")
    url_params = models.CharField(verbose_name="跳转链接参数JSON", max_length=500, default="")
    is_pushed = models.BooleanField(verbose_name="是否已推送", default=False)
    push_strategy = models.SmallIntegerField(verbose_name="推送策略", choices=PUSH_STRATEGY, default=0)
    is_anonymous = models.BooleanField(verbose_name="帖子是否匿名", default=False)

    class Meta:
        db_table = "circle_action_log"

    @staticmethod
    def _get_section_user_mobiles(action_type):
        mobiles = []
        action_section = [item[2] for item in ACTION_SECTIONS if item[0] == action_type]

        if action_section:
            conn = connections["bbs_user"]
            cursor = conn.cursor()
            params = (action_section[0], )
            cursor.execute("SELECT mobile FROM users_section_info where tag=%s and is_delete=false", params)
            mobiles = [item[0] for item in cursor.fetchall()]

        return mobiles

    @classmethod
    def create_objects(cls, **kwargs):
        object_list = []

        model_fields = cls.fields()
        action_mapping = dict(ACTION_CHOICES)
        mobile = kwargs.pop("mobile", "")  # 给多个人发送,但operator_mobile一般只有一个

        new_kwargs = {key: value for key, value in kwargs.items() if key in model_fields}
        action_type = int(new_kwargs.get("action_type"))

        if action_type == 5:
            # HR知乎: 新帖时自动发给专区HR
            mobiles = cls._get_section_user_mobiles(action_type)
            mobile = ",".join(mobiles)
            new_kwargs["push_strategy"] = 2
        else:
            new_kwargs["push_strategy"] = 1

        if not mobile:
            return object_list

        mobile_list = [s.strip() for s in mobile.split(",") if s.strip()]
        message_obj = CircleMessageBodyModel.objects.get(action_type=action_type)

        # 处理通知的跳转参数，可与前端约定由前端来决定
        if action_type in [1, 2, 3, 5, 6]:
            url_params = json.dumps(dict(circle_id=int(new_kwargs.get("circle_id"))))
        else:
            # 其他暂时不处理
            url_params = kwargs.pop("url_params", "")

        new_kwargs.update(
            action_cn=action_mapping.get(action_type, ""),
            message_id=message_obj.id, url_params=url_params,
        )

        for _mobile in mobile_list:
            insert_kwargs = dict(new_kwargs, mobile=_mobile)
            object_list.append(cls.objects.create(**insert_kwargs))

        return object_list


class CircleAnnualPersonalSummaryModel(BaseAbstractModel):
    user_id = models.IntegerField(verbose_name="用户ID", default=0, null=True)
    mobile = models.CharField(verbose_name="用户手机", max_length=200, default="")
    first_login_date = models.DateField(verbose_name="第一次登陆星圈日期", default=None, null=True)
    first_circle_id = models.IntegerField(verbose_name="第一个实名帖子", default=0, null=True)
    first_circle_text = models.CharField(verbose_name="第一个实名帖子内容", max_length=5000, default='', null=True)
    received_star_cnt = models.IntegerField(verbose_name="收到赞评数", default=0, null=True)
    received_star_user_cnt = models.IntegerField(verbose_name="收到赞评的人数", default=0, null=True)
    delivered_star_cnt = models.IntegerField(verbose_name="送出赞评数", default=0, null=True)
    hot_circle_cnt = models.IntegerField(verbose_name="参与热门话题次数", default=0, null=True)
    login_pv_cnt = models.IntegerField(verbose_name="登陆星圈pv数", default=0, null=True)
    accompany_days = models.IntegerField(verbose_name="陪伴天数", default=0, null=True)
    delivered_avg_star_cnt = models.IntegerField(verbose_name="送赞超过平均赞数", default=0, null=True)
    post_circle_cnt = models.IntegerField(verbose_name="发帖数量(>=2)", default=0, null=True)
    annual = models.IntegerField(verbose_name="年度", default=None, null=True)
    only_visitor = models.BooleanField(verbose_name="仅访问", default=0, null=True)

    class Meta:
        db_table = "circle_annual_summary"

