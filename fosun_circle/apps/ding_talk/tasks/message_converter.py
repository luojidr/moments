import re
import json
import os.path
import tempfile
import traceback
import urllib.parse
from enum import Enum
from enum import unique

import requests
from django.conf import settings

from fosun_circle.libs.utils.crypto import BaseCipher
from fosun_circle.libs.log import task_logger as logger
from ding_talk.models import DingMessageModel, DingAppMediaModel, DingAppTokenModel

__all__ = ["MessageConverter"]


@unique
class StarCreditEnum(Enum):
    DINING = ("餐饮积分", "您的餐饮积分已到账")
    BIRTHDAY = ("生日积分", "您的生日积分已到账")
    STATIONERY = ("文具积分", "您的文具积分已到账")
    ADMINISTRATION = ("行政积分", "您的行政积分已到账")
    MOTIVATION = ("激励积分", "您的激励积分已到账")
    SPRING = ("春节积分", "您的春节积分已到账")

    @property
    def type(self):
        return self.value[0]

    @property
    def title(self):
        return self.value[1]

    @classmethod
    def iterator(cls):
        return iter(cls._member_map_.values())


class MessageConverter:
    MEDIA_MAPPING = {}
    STAR_ENUM = StarCreditEnum
    MEDIA_UPLOAD_API = "{host}/api/v1/circle/ding/apps/message/media/upload".format(host=settings.CIRCLE_HOST)
    MSG_REGEX = re.compile(r"!\[alt\]\((?P<img_url>.*?)\)(?P<msg_text>.*?)\[.*?\]\((?P<msg_url>.*?)\).*", re.S | re.M)

    @classmethod
    def get_body_markdown_to_oa(cls, ding_msg_object=None, ding_msg_id=None):
        """ 星喜积分 markdown 消息体转为 oa """
        body_kwargs = {}

        if not isinstance(ding_msg_object, DingMessageModel):
            try:
                ding_msg_object = DingMessageModel.objects.filter(id=ding_msg_id).select_related("app").first()
            except DingMessageModel.DoesNotExist:
                pass

        if not isinstance(ding_msg_object, DingMessageModel):
            return body_kwargs

        try:
            content = ding_msg_object.msg_text
            match_dict = cls.MSG_REGEX.search(content)

            if match_dict:
                img_url = (match_dict["img_url"] or "").strip()
                msg_text = (match_dict["msg_text"] or "").strip()
                msg_url = (match_dict["msg_url"] or "").strip()

                instance = cls()
                media_id = instance._get_media_id(img_url=img_url, app_token=ding_msg_object.app.app_token)

                body_kwargs = dict(
                    title=instance._get_msg_title(msg_text), media_id=media_id,
                    content=msg_text, message_url=msg_url, pc_message_url=msg_url,
                )
        except Exception as e:
            logger.info("MessageConverter => star markdown ding body error: %s", e)
            logger.error(traceback.format_exc())

        return body_kwargs

    def _get_media_id(self, img_url, app_token=None):
        url_md5 = BaseCipher.crypt_md5(img_url)

        if url_md5 in self.MEDIA_MAPPING:
            return self.MEDIA_MAPPING[url_md5]

        if not img_url:
            return None

        result = urllib.parse.urlparse(img_url)
        if result.path:
            basename = os.path.basename(result.path)
            media_obj = DingAppMediaModel.objects.filter(src_filename=basename).select_related("app").first()

            if media_obj:
                return media_obj.media_id

            # 临时保存文件
            r = requests.get(img_url)
            data = dict(app_token=app_token, media_type="image", media_title="星喜积分-%s" % self.__class__.__name__)

            with tempfile.TemporaryFile() as fp:
                fp.name = basename
                fp.write(r.content)
                fp.seek(0)

                resp = requests.post(self.MEDIA_UPLOAD_API, data=data, files=dict(media=fp))
                if resp.status_code == 200:
                    resp_data = resp.json().get("data", {})
                    media_id = resp_data.get("media_id")

                    if media_id:
                        self.MEDIA_MAPPING[url_md5] = media_id
                        DingAppMediaModel.objects.filter(id=resp_data["id"]).update(is_success=True)

                    return self.MEDIA_MAPPING[url_md5]

        return None

    def _get_msg_title(self, msg_text):
        default_title = "您的星喜积分已到账"

        for one_enum in self.STAR_ENUM.iterator():
            _type = one_enum.type
            title = one_enum.title

            if re.compile(_type, re.S | re.M).search(msg_text):
                default_title = title
                break

        return default_title


