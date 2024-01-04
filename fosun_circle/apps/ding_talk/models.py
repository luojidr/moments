from django.db import models
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import FileSystemStorage

from fosun_circle.core.db.base import BaseAbstractModel
from fosun_circle.constants.enums.ding_msg_type import DingMsgTypeEnum
from fosun_circle.libs.utils.crypto import AESHelper
from fosun_circle.libs.path_builder import PathBuilder

default_storage = FileSystemStorage()


class DingAppMediaModel(BaseAbstractModel):
    MEDIA_TYPE_CHOICE = (
        (1, "image"),
        (2, "file"),
        (3, "voice"),
    )

    app = models.ForeignKey(to="DingAppTokenModel", verbose_name="微应用id", on_delete=models.CASCADE, related_name="app")
    media_type = models.SmallIntegerField(verbose_name="媒体类型", choices=MEDIA_TYPE_CHOICE, default=1, blank=True)
    media_title = models.CharField(verbose_name="媒体名称", max_length=500, default="", blank=True)
    media_id = models.CharField(verbose_name="媒体id", max_length=100, default="", blank=True)

    # 图片保存在服务器端
    media = models.FileField("媒体链接", upload_to=PathBuilder("media"), storage=default_storage, max_length=500, blank=True)
    key = models.CharField("上传文件key", unique=True, max_length=50, default="", blank=True)
    media_url = models.URLField("媒体文件URL", max_length=500, default="", blank=True)
    file_size = models.IntegerField("文件大小", default=0, blank=True)
    check_sum = models.CharField("源文件md5", max_length=64, default="", blank=True)
    src_filename = models.CharField("源文件名称", max_length=200, default="", blank=True)
    post_filename = models.CharField("处理后的文件名称", max_length=200, default="", blank=True)
    is_share = models.BooleanField("是否共享", default=False, blank=True)
    is_success = models.BooleanField("是否成功", default=False, blank=True)
    access_token = models.CharField("token秘钥(如果不共享)", max_length=100, default="", blank=True)

    class Meta:
        db_table = "circle_ding_app_media"
        ordering = ["-create_time"]

    @classmethod
    def get_media_by_key(cls, key):
        try:
            return cls.objects.get(key=key, is_del=False)
        except (ObjectDoesNotExist, MultipleObjectsReturned):
            pass


class DingAppTokenModel(BaseAbstractModel):
    """ 钉钉应用信息 """

    TOKEN_ENV = (
        (0, "测试环境"),
        (1, "生产环境"),
    )
    # from django.core.management.utils import get_random_secret_key
    TOKEN_KEY = "j9oi-Xplq#wYtmr+"      # 固定值: 16位

    corp_id = models.CharField(verbose_name="企业corpId", max_length=100, db_index=True, default="")
    app_name = models.CharField(verbose_name="钉钉应用名称", max_length=100, unique=True, default="")
    agent_id = models.IntegerField(verbose_name="应用 appId", unique=True, default=0)
    app_key = models.CharField(verbose_name="应用 appKey", max_length=200, default="")
    app_secret = models.CharField(verbose_name="应用 appSecret", max_length=500, default="")
    app_token = models.CharField(verbose_name="外部调用的唯一Token", max_length=500, db_index=True, default="")
    expire_time = models.BigIntegerField(verbose_name="Token过期时间", default=0)
    env = models.SmallIntegerField(verbose_name="Token所属环境", choices=TOKEN_ENV, default=0)

    class Meta:
        db_table = "circle_ding_app_token"
        ordering = ["id"]

    def __str__(self):
        return "<agentId: %s>" % self.agent_id

    def encrypt_token(self):
        raw = "%s:%s:%s:%s" % (self.agent_id, self.corp_id, self.app_key, self.app_secret)
        cipher_text = AESHelper(key=self.TOKEN_KEY).encrypt(raw=raw)

        return cipher_text

    def decrypt_token(self):
        return self.decipher_text(self.app_token)

    @classmethod
    def decipher_text(cls, app_token):
        cipher_text = app_token
        plain_text = AESHelper(key=cls.TOKEN_KEY).decrypt(text=cipher_text)

        return plain_text

    @classmethod
    def get_app_by_token(cls, app_token):
        try:
            plain_token = cls.decipher_text(app_token)
            agent_id = int(plain_token.split(":", 1)[0])
            app_obj = DingAppTokenModel.objects.get(agent_id=agent_id)

            return app_obj
        except Exception:
            raise ObjectDoesNotExist("媒体上传的微应用 app_token 不合法！")


class DingMessageModel(BaseAbstractModel):
    SOURCE_CHOICES = [
        (1, "星喜积分"),  # 已使用
        (2, "问卷投票"),  # 已使用
        (3, "星圈话题"),  # 已使用
        (4, "节日关怀(H5)"),  # 已使用
        (5, "星喜甄选"),  # 已使用
        (6, "抽奖活动"),  # 已使用
    ]

    MSG_TYPE_CHOICES = [
        (1, DingMsgTypeEnum.TEXT.msg_type),
        (2, DingMsgTypeEnum.IMAGE.msg_type),
        (3, DingMsgTypeEnum.VOICE.msg_type),
        (4, DingMsgTypeEnum.FILE.msg_type),
        (5, DingMsgTypeEnum.LINK.msg_type),
        (6, DingMsgTypeEnum.OA.msg_type),
        (7, DingMsgTypeEnum.MARKDOWN.msg_type),
        (8, DingMsgTypeEnum.ACTION_CARD.msg_type),
    ]

    app = models.ForeignKey(to=DingAppTokenModel, verbose_name="微应用id", default=None, on_delete=models.CASCADE)
    msg_title = models.CharField(verbose_name="消息标题", max_length=500, default="", blank=True)
    msg_media = models.CharField(verbose_name="消息图片", max_length=500, default="", blank=True)
    msg_type = models.SmallIntegerField(verbose_name="消息类型", choices=MSG_TYPE_CHOICES, default=0, blank=True)
    msg_type_cn = models.CharField(verbose_name="消息类型", max_length=20, default="", blank=True)
    msg_text = models.CharField(verbose_name="消息文本", max_length=1000, default="", blank=True)
    # msg_other = models.CharField(verbose_name="消息文本", max_length=1000, default="")
    msg_url = models.CharField(verbose_name="消息链接", max_length=1000, default="", blank=True)
    msg_pc_url = models.CharField(verbose_name="PC消息链接", max_length=1000, default="", blank=True)
    source = models.SmallIntegerField(verbose_name="推送来源", choices=SOURCE_CHOICES, default=0, blank=True)
    source_cn = models.CharField(verbose_name="推送来源", max_length=200, default="", blank=True)
    ihcm_survey_id = models.IntegerField(verbose_name="Odoo问卷投票id", default=0, blank=True)

    class Meta:
        db_table = "circle_ding_message_info"
        ordering = ["-id"]


class DingMsgPushLogModel(BaseAbstractModel):
    """ 消息推送记录 """
    DEFAULT_TIME = "1979-01-01 00:00:00"

    ding_msg_id = models.IntegerField("钉钉消息ID", default=0, blank=True)
    sender = models.CharField(verbose_name="推送人(默认系统)", max_length=100, default="sys", blank=True)
    send_time = models.DateTimeField(verbose_name="推送时间", auto_now_add=True, blank=True)
    receiver_mobile = models.CharField(verbose_name="接收人手机号", max_length=20, default="", db_index=True, blank=True)
    receiver_job_code = models.CharField(verbose_name="接收人钉钉jobCode", max_length=100, default="", blank=True)
    receive_time = models.DateTimeField(verbose_name="接收时间", default=DEFAULT_TIME, blank=True)
    is_read = models.BooleanField(verbose_name="接收人是否已读", default=False, blank=True)
    read_time = models.DateTimeField(verbose_name="接收人已读时间", default=DEFAULT_TIME, blank=True)
    is_success = models.BooleanField(verbose_name="推送是否成功", default=False, blank=True)
    traceback = models.CharField(verbose_name="推送异常", max_length=2000, default="", blank=True)
    task_id = models.CharField(verbose_name="钉钉创建的异步发送任务ID", default="", max_length=100, db_index=True, blank=True)
    request_id = models.CharField(verbose_name="钉钉推送的请求ID", max_length=100, default="", blank=True)
    msg_uid = models.CharField(verbose_name="消息唯一id", default="", max_length=100, unique=True, blank=True)
    is_recall = models.BooleanField(verbose_name="消息是否撤回", default=False, blank=True)
    recall_time = models.DateTimeField(verbose_name="撤回时间", default=DEFAULT_TIME, blank=True)
    is_test = models.BooleanField(verbose_name="是否测试消息", default=False, blank=True)
    is_done = models.BooleanField(verbose_name="是否完成(问卷投票等)", default=False, blank=True)
    is_cryptonym = models.BooleanField(verbose_name="是否匿名(问卷)", default=False, blank=True)
    max_times = models.IntegerField("消息是失败最大补偿推送次数", default=1, blank=True)

    class Meta:
        db_table = "circle_ding_msg_push_log"
        ordering = ["-id"]


class DingMsgRecallLogModel(BaseAbstractModel):
    """ 消息回撤记录 """
    DEFAULT_TIME = "1979-01-01 00:00:00"

    app_id = models.IntegerField(verbose_name="微应用id", default=0, blank=True)
    ding_msg_id = models.IntegerField(verbose_name="钉钉消息id", default=0, blank=True)
    task_id = models.CharField(verbose_name="撤回消息的任务ID", default="", max_length=100, db_index=True, blank=True)
    msg_uid = models.CharField(verbose_name="撤回消息UID", default="", max_length=100, blank=True)
    recall_time = models.DateTimeField(verbose_name="撤回时间", default=DEFAULT_TIME, blank=True)
    is_recall_ok = models.BooleanField(verbose_name="状态", default=False, blank=True)
    recall_cnt = models.IntegerField(verbose_name="撤回消息数量", default=0, blank=True)
    recall_ret = models.CharField(verbose_name="撤回消息的结果", default="", max_length=2000, blank=True)

    class Meta:
        db_table = "circle_ding_msg_recall_log"
        ordering = ["-id"]


class DingPeriodicTaskModel(BaseAbstractModel):
    cron_name = models.CharField(verbose_name="定时任务名称", default="", max_length=200, blank=True)
    beat_cron_id = models.IntegerField(verbose_name="定时任务id", default=0, blank=True)
    beat_periodic_task_id = models.IntegerField(verbose_name="定时任务", default=0, blank=True)
    cron_expr = models.CharField(verbose_name="定时表达式", default="", max_length=100, blank=True)
    max_run_times = models.IntegerField(verbose_name="定时任务最大执行次数", default=0, blank=True)
    deadline_run_time = models.DateTimeField(verbose_name='截止执行时间', blank=True, null=True, help_text='截止执行时间',)
    message_id = models.IntegerField(verbose_name="推送消息话题ID", default=0, blank=True)
    push_range = models.CharField(verbose_name="话题推送范围(JSON格式)", default="{}", max_length=5000, blank=True)
    remark = models.CharField(verbose_name="任务说明", default="", max_length=500, blank=True)

    class Meta:
        db_table = "circle_ding_periodic_task"
        ordering = ["-id"]


# class DingPushTaskStatModel(BaseAbstractModel):
#     user_count = models.IntegerField("推送人数", default=0, blank=True)
#     ding_msg_id = models.IntegerField("推送消息ID", default=0, blank=True)
#     success_count = models.IntegerField("成功数量", default=0, blank=True)
#     failed_count = models.IntegerField("失败数量", default=0, blank=True)

