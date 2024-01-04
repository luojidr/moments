import uuid
import os.path
import typing
import inspect
import traceback
from datetime import date
from inspect import Parameter

from dingtalk import AppKeyClient, DingTalkException
from dingtalk.model.message import BodyBase
from dingtalk.client.api.message import Message
from dingtalk.core.exceptions import DingTalkClientException

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile


from .parser import MessageBodyParser
from fosun_circle.libs.decorators import to_retry
from config.conf.dingtalk import DingTalkConfig
from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.constants.enums.ding_msg_type import DingMsgTypeEnum
from fosun_circle.libs.exception import DingMsgTypeNotExist, DingMsgBodyFieldError

__all__ = ["BaseDingMixin", "DingTalkMessageOpenApi"]


class BaseDingMixin:
    def __init__(self, corp_id="", agent_id=None, app_key=None, app_secret=None, **kwargs):
        self._corp_id = corp_id or self.default_config["corp_id"]
        self._agent_id = agent_id or self.default_config["agent_id"]
        self._app_key = app_key or self.default_config["app_key"]
        self._app_secret = app_secret or self.default_config["app_secret"]

        self._client = AppKeyClient(
            corp_id=self._corp_id,
            app_key=self._app_key,
            app_secret=self._app_secret
        )

    @property
    def default_config(self):
        return dict(
            corp_id=DingTalkConfig.DING_CORP_ID,
            agent_id=DingTalkConfig.DING_AGENT_ID,
            app_key=DingTalkConfig.DING_APP_KEY,
            app_secret=DingTalkConfig.DING_APP_SECRET,
        )

    @to_retry
    def get_access_token(self):
        """ 获取应用 access token """
        return self._client.get_access_token()


class DingTalkMessageOpenApi(BaseDingMixin, MessageBodyParser):
    """ 发送不同类型的消息 """

    def __init__(self, msg_type=None, **kwargs):
        self._msg_type = msg_type

        init_kwargs = dict(msg_type=msg_type)
        init_kwargs.update(**kwargs)
        super().__init__(**init_kwargs)
        super(MessageBodyParser, self).__init__(msg_type=msg_type)

        self._message = Message(client=self._client)

    @to_retry
    def upload_media_file(self, media_type, media_filename=None, media_file=None):
        """ 上传图片、文件、语音文件

        :param media_type: 媒体文件类型，分别有图片（image）、语音（voice）、普通文件(file)
        :param media_file: 要上传的文件，一个 File-object
        :param media_filename: 文件路径

        resp: {
            'errcode': 0, 'errmsg': 'ok', 'media_id': '@lALPDeC2zDlm8IpiYg',
            'created_at': 1603962089663, 'type': 'image'
        }
        """
        if media_type not in ["image", "voice", "file"]:
            raise ValueError("媒体文件类型(仅限: image, voice, file)错误!")

        if not media_file and not media_filename:
            raise ValueError("未选择媒体文件!")

        if media_filename and not os.path.exists(media_filename):
            raise ValueError("媒体文件不存在")

        if isinstance(media_file, UploadedFile):
            media_path = os.path.join(settings.MEDIA_ROOT, str(date.today()))
            filename = str(uuid.uuid1()).replace("-", "") + os.path.splitext(media_file.name)[-1]
            media_filename = os.path.join(media_path, filename)

            if not os.path.exists(media_path):
                os.makedirs(media_path)

            with open(media_filename, 'wb+') as fd:
                for chunk in media_file.chunks():
                    fd.write(chunk)

        resp = {}
        media_file = open(media_filename, "rb")

        try:
            resp = self._message.media_upload(media_type, media_file=media_file)
        except DingTalkClientException:
            traceback.format_exc()
        finally:
            media_file.close()
            os.remove(media_filename)

        log_args = (self.__class__.__name__, media_filename, resp)
        logger.info("<%s>.upload_media_file media_filename:%s, upload resp:%s", *log_args)

        if resp.get("errcode") != 0:
            raise ValueError("上传上传失败: {}".format(resp.get("errmsg")))

        return resp

    def _get_msg_body(self, **body_kwargs):
        """ 根据不同的消息类型获取对应的消息体 """
        if self._msg_type == DingMsgTypeEnum.TEXT.msg_type:
            msg_body_func = self.get_text_body

        elif self._msg_type == DingMsgTypeEnum.LINK.msg_type:
            msg_body_func = self.get_link_body

        elif self._msg_type in self.MEDIA_TYPE_TO_MAX_SIZE:
            msg_body_func = self.get_media_body

        elif self._msg_type == DingMsgTypeEnum.OA.msg_type:
            msg_body_func = self.get_oa_body

        elif self._msg_type == DingMsgTypeEnum.MARKDOWN.msg_type:
            msg_body_func = self.get_markdown_body

        else:
            raise DingMsgTypeNotExist(msg_type=self._msg_type)

        # 过滤消息体参数
        new_body_kwargs = dict()
        sig = inspect.signature(msg_body_func)
        parameters = sig.parameters

        for key, param in parameters.items():
            default = param.default     # 参数签名默认值
            has_key = key not in body_kwargs
            value = body_kwargs.pop(key, None)

            if default is param.empty:
                # 位置参数必须赋值
                if param.kind not in [Parameter.KEYWORD_ONLY, Parameter.VAR_KEYWORD] and has_key:
                    raise DingMsgBodyFieldError(self._msg_type)

                new_body_kwargs[key] = value
            else:
                new_body_kwargs[key] = value or default

        # body_kwargs 其他参数
        new_body_kwargs.update(body_kwargs)
        return msg_body_func(**new_body_kwargs)

    @to_retry
    def async_send(self, body_kwargs, userid_list=(), dept_id_list=(), to_all_user=False):
        """ 企业会话消息异步发送
        :param body_kwargs: dict, 不同消息体对应的参数
        :param userid_list: list|tuple, 接收者的用户userid列表
        :param dept_id_list: list|tuple, 接收者的部门id列表
        :param to_all_user: bool, 是否发送给企业全部用户
        """

        if not isinstance(userid_list, (typing.Tuple, typing.List)):
            raise ValueError("parameter `user_id_list` must is list|tuple")

        msg_body = self._get_msg_body(**body_kwargs)

        if not isinstance(msg_body, BodyBase):
            raise ValueError("parameter `msg_body` must is a instance of BodyBase")

        return self._message.asyncsend_v2(
            msg_body,
            agent_id=self._agent_id, userid_list=userid_list,
            dept_id_list=dept_id_list, to_all_user=to_all_user
        )

    def recall(self, msg_task_id):
        """ 撤回工作通知消息

        :param msg_task_id: 发送工作通知返回的 taskId
        """
        return self._message.recall(agent_id=self._agent_id, msg_task_id=msg_task_id)

    def __getattr__(self, name):
        if name.startswith('_'):
            return object.__getattribute__(self, name)

        method = getattr(self._message, name, None)
        if method is None:
            raise DingTalkException(errcode=10901, errmsg="DingTalk message haven't method<%s>" % name)

        return method



