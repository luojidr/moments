import enum
import json
import time
import hmac
import base64
import hashlib
import logging
import inspect
import traceback
import urllib.parse
from typing import Union, List, Dict

import requests

from django.conf import settings

__all__ = ["DDCustomRobotWebhook"]


class DDCustomRobotMsgTypeEnum(enum.Enum):
    TEXT = ("text", "Text")
    LINK = ("link", "Link")
    MARKDOWN = ("markdown", "Markdown")
    FEED_CARD = ("feedCard", "FeedCard")
    ACTION_CARD = ("actionCard", "ActionCard")

    @property
    def msgtype(self):
        return self.value[0]

    @classmethod
    def iterator(cls):
        return iter(cls._member_map_.values())


_MsgTypeEnum = DDCustomRobotMsgTypeEnum


class DDMsgBase:
    msgtype: Union[str, None] = None

    def __init__(self, **kwargs):
        cls_attrs = self.__class__.__dict__

        for name, value in cls_attrs.items():
            if name == '__annotations__':
                for k, _ in value.items():
                    # 设置默认值
                    try:
                        setattr(self, k, cls_attrs[k])
                    except KeyError:
                        pass

                    if k in kwargs:
                        setattr(self, k, kwargs[k])

            if name.startswith('_'):
                continue

            if name in kwargs and value:
                setattr(self, name, value)

    def get_dict(self):
        assert self.msgtype is not None, "Message Type is not allow to empty."
        return {'msgtype': self.msgtype, self.msgtype: self._get_data()}

    def _get_data(self):
        ret = {}
        self._check()

        for k in self.__dict__:
            v = getattr(self, k, None)

            if v is None or hasattr(v, '__call__'):
                continue

            if v is not None:
                if isinstance(v, DDMsgBase):
                    v = v._get_data()
                ret[k] = v

        return ret

    def _init_field_list(self, field_cls, datas: List[Dict[str, str]]):
        if not self.msgtype:
            raise ValueError('Message Type is not allow to empty')

        ret = []
        for items in datas:
            obj = field_cls(**items)
            if not isinstance(obj, DDMsgBase):
                raise ValueError('%s is not subclass of DDMsgBase' % field_cls)

            ret.append(obj._get_data())

        return ret

    def _check(self):
        raise NotImplemented


class DDTextMsg(DDMsgBase):
    msgtype = _MsgTypeEnum.TEXT.msgtype
    content: str

    def _check(self):
        if not self.content:
            raise ValueError("`text` type `content` field is empty.")


class DDLinkMsg(DDMsgBase):
    msgtype = _MsgTypeEnum.LINK.msgtype
    title: str
    text: str
    messageUrl: str
    picUrl: Union[str, None] = None

    def _check(self):
        if not self.title or not self.text or not self.messageUrl:
            raise ValueError("`link` type `title` or `text` or `messageUrl` field is empty.")


class DDMarkdownMsg(DDMsgBase):
    msgtype = _MsgTypeEnum.MARKDOWN.msgtype
    title: str
    text: str

    def _check(self):
        if not self.title or not self.text:
            raise ValueError("`markdown` type `title` or `text` field is empty.")


class _ActionCardBtn(DDMsgBase):
    title: str
    actionURL: str

    def _check(self):
        if not self.title or not self.actionURL:
            raise ValueError("`actionCard` type btns field `title` or `actionURL` is empty.")


class DDActionCardMsg(DDMsgBase):
    msgtype = _MsgTypeEnum.ACTION_CARD.msgtype
    title: str
    text: str
    singleTitle: Union[str, None] = None   # 设置此项和singleURL后，btns无效
    singleURL: Union[str, None] = None
    btnOrientation: str = "0"
    btns: Union[List[Dict[str, str]], None] = None

    def _check(self):
        if not self.title or not self.text:
            raise ValueError("`actionCard` type `title` or `text` field is empty.")

        if (self.singleTitle and not self.singleURL) or (not self.singleTitle and self.singleURL):
            raise ValueError("`actionCard` type `singleTitle` or `singleURL` field must exist simultaneously.")
        elif not self.singleTitle and not self.singleURL:
            if not self.btns:
                raise ValueError("`actionCard` type `btns` field is empty.")

            # btns: [{"title": "xxx", "actionURL": "https://yyy"}, ...]
            self.btns = self._init_field_list(_ActionCardBtn, datas=self.btns)


class _FeedCardLink(DDMsgBase):
    title: str
    picURL: str
    messageURL: str

    def _check(self):
        if not self.title or not self.messageURL or not self.picURL:
            raise ValueError("`feedCard` type links field `title` or `picURL` or `messageURL` is empty.")


class DDFeedCardMsg(DDMsgBase):
    msgtype = _MsgTypeEnum.FEED_CARD.msgtype
    links: List[Dict[str, str]]

    def _check(self):
        if not self.links:
            raise ValueError("`feedCard` type `links` field is empty.")

        # links: [{"title": "xxx", "messageURL": "https://yyy", "picURL": "https://zzz", }, ...]
        self.links = self._init_field_list(_FeedCardLink, datas=self.links)


class DDCustomRobotWebhook:
    """ https://open.dingtalk.com/document/robots/custom-robot-access#title-72m-8ag-pqw """
    MSGTYPE_ENUM = _MsgTypeEnum

    def __init__(self,
                 webhook: str,
                 access_token: str,
                 secret: Union[str, None] = None,
                 keywords: Union[List[str], None] = None
                 ):
        self._webhook = webhook or settings.DD_CUSTOM_ROBOT_WEBHOOK_URL
        self._secret = secret or settings.DD_CUSTOM_ROBOT_WEBHOOK_SECRET
        self._access_token = access_token or settings.DD_CUSTOM_ROBOT_WEBHOOK_ACCESS_TOKEN
        self._keywords = keywords or []
        self._logger = logging.getLogger('django')

    def _check_keywords(self, content: Union[str, None] = None):
        if self._keywords and content and not any([kw in content for kw in self._keywords]):
            kws = ', '.join(self._keywords)
            raise ValueError('消息内容中未包含任何给定的关键词（keywords: %s）' % kws)

    def _get_class(self, msgtype: str):
        vars_dict = globals()
        msgtype_list = [e.msgtype for e in self.MSGTYPE_ENUM.iterator()]

        for name, obj in vars_dict.items():
            if inspect.isclass(obj) and not name.startswith('_'):
                cls_msgtype = getattr(obj, 'msgtype', None)
                if cls_msgtype not in msgtype_list:
                    continue

                if msgtype not in msgtype_list:
                    raise ValueError('钉钉机器人消息<msgtype: %s>类型错误!' % msgtype)

                if cls_msgtype == msgtype:
                    return obj

        raise ValueError('钉钉机器人消息没有该消息类型<msgtype: %s>' % msgtype)

    def _get_body(self,
                  msgtype: str,
                  at_mobiles: Union[List[str], None] = None,
                  at_user_ids: Union[List[str], None] = None,
                  is_at_all: Union[bool, None] = False,
                  **kwargs
                  ):
        msg_cls = self._get_class(msgtype=msgtype)
        self._check_keywords(content=kwargs.get('content'))

        body = {
            'at': {
                'atMobiles': at_mobiles or [],
                'atUserIds': at_user_ids or [],
                'isAtAll': is_at_all or False
            },
            **msg_cls(**kwargs).get_dict()
        }

        return body

    def _get_sign_params(self):
        timestamp = str(round(time.time() * 1000))
        secret_enc = self._secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self._secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

        return dict(timestamp=timestamp, sign=sign)

    def send(self, msgtype: str, **kwargs):
        body = self._get_body(msgtype, **kwargs)
        params = dict(access_token=self._access_token)
        headers = {'Content-Type': 'application/json'}

        if self._secret:
            params.update(self._get_sign_params())

        try:
            r = requests.post(url=self._webhook, params=params, data=json.dumps(body), headers=headers)
            r_ret = r.json()

            if r.status_code == 200 and r_ret.get('errcode') == 0:
                return

            errmsg = r_ret.get('errmsg')
        except Exception as e:
            errmsg = str(e)
            self._logger.error(traceback.format_exc())

        raise ValueError('DDRobotWebhook.send message error: %s' % errmsg)

