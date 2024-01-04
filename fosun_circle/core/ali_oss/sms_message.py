import json
import string
import random
import traceback
from _md5 import md5

try:
    from functools import cached_property
except ImportError:
    from django.utils.functional import cached_property

from django.utils import timezone

import requests
from aliyunsdkcore.request import CommonRequest
from aliyunsdkcore.acs_exception import exceptions

from config.conf import aliyun
from .base import AliOssBase as AliClientBase
from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.constants.enums.sms_type import SmsTypeEnum

__all__ = ["AliSmsMessageRequest", 'FosunSmsMessageRequest']


class AliSmsMessageRequest(AliClientBase):
    """ 阿里云发送sms服务(一个签名+一个模板 发送多个人) """

    ACCEPT_FORMAT = "json"
    PROTOCOL_TYPE = "https"     # https | http
    SMS_DOMAIN = "dysmsapi.aliyuncs.com"
    X_ACS_VERSION = "2017-05-25"

    def __init__(self, sign_name=None, template_code=None, template_params=None, **kwargs):
        """ 阿里云发送短信
        :param sign_name:       str, 短信签名
        :param template_code:   str, 短信模板CODE
        :param template_param:  dict, 短信模板参数
        """
        super(AliSmsMessageRequest, self).__init__(**kwargs)

        self._sign_name = sign_name
        self._template_code = template_code
        self._template_params = template_params or {}

        self._request = CommonRequest()

    def _add_body(self, **kwargs):
        self._request.set_accept_format(self.ACCEPT_FORMAT)
        self._request.set_domain(self.SMS_DOMAIN)
        self._request.set_method('POST')
        self._request.set_protocol_type(self.PROTOCOL_TYPE)
        self._request.set_version(self.X_ACS_VERSION)
        self._request.add_query_param('RegionId', self._region_id)

        template_code = kwargs.get("template_code") or self._template_code
        self._request.add_query_param('TemplateCode', template_code)      # 短信模板唯一

        # 其他短信参数
        phone_numbers = kwargs.get("phone_numbers", [])
        sign_names = kwargs.get("sign_names", []) or [self._sign_name]
        template_params = kwargs.get("template_params", []) or [self._template_params]
        kwargs.get("action_name") and self._request.set_action_name(kwargs["action_name"])

        # 发送短信参数
        if phone_numbers:
            phone_cnt = len(phone_numbers)
            self._request.set_action_name("SendBatchSms" if len(phone_numbers) > 1 else "SendSms")

            if phone_cnt == 1:
                query_params = dict(SignName=sign_names[0], PhoneNumbers=phone_numbers[0],
                                    TemplateParam=json.dumps(template_params[0]),)
            else:
                # 批量规则: 对同一短信模板可以有多个签名、发送多个人
                sign_names = sign_names if len(sign_names) == phone_cnt else [self._sign_name] * phone_cnt
                template_params = template_params if len(template_params) == phone_cnt else [self._template_params] * phone_cnt

                query_params = dict(SignNameJson=json.dumps(sign_names),
                                    PhoneNumberJson=json.dumps(phone_numbers),
                                    TemplateParamJson=json.dumps(template_params),)

            for query_key, query_value in query_params.items():
                self._request.add_query_param(query_key, query_value)

    def _get_action_name(self):
        """ 短信API操作 | https://help.aliyun.com/document_detail/419298.html """

    def _do_action(self):
        response = self._client.do_action_with_exception(self._request)
        result = str(response, encoding='utf-8')

        return json.loads(result)

    def send_sms_code(self, phone_number, sms_code=None, code_size=6):
        """ 发送 sms """
        if not sms_code:
            sms_code = "".join([random.choice(string.digits) for _ in range(code_size)])

        sms_entity = dict(code=sms_code)
        self._add_body(template_params=[sms_entity], phone_numbers=[phone_number])

        result = self._do_action()
        assert result.get("Code") == "OK", "验证码发送错误:{}".format(result.get("Message"))

        return dict(result, smsCode=sms_entity["code"])

    def send_sms(self, phone_numbers, template_code=None, template_params=None, sign_names=None, silently=False):
        """
        参考: https://next.api.aliyun.com/api/Dysmsapi/2017-05-25/SendSms | https://www.136.la/python/show-62554.html

        :param phone_numbers: str|list, eg: "13100000000", "13100000000,13200000000", ["13100000000"]
        :param template_params:        dict|list, every phone params
        :param sign_names     str|list， sms sign name
        :param template_code  str， sms template
        :param silently:      bool, whether raise error
        :return:
        """
        if not phone_numbers:
            raise ValueError("手机号码不能为空")

        result = {}
        phone_cnt = len(phone_numbers)
        sign_names = sign_names or []
        template_params = template_params or []

        if template_params and phone_cnt != len(template_params):
            raise ValueError("短信模板参数个数与手机不等")

        if sign_names and phone_cnt != len(sign_names):
            raise ValueError("短信模板签名个数与手机不等")

        if isinstance(phone_numbers, (tuple, list)):
            pass
        elif isinstance(phone_numbers, (str, bytes)):
            phone_numbers = [phone_numbers]
        else:
            raise ValueError("手机号错误")

        try:
            template_code = template_code or self._template_code
            self._add_body(
                phone_numbers=phone_numbers, sign_names=sign_names,
                template_params=template_params,  template_code=template_code,
            )
            result = self._do_action()

            log_args = (self.__class__.__name__, phone_numbers, template_params, result)
            self.logger.info("<%s.send_sms> phone_numbers:%s, params:%s, result:%s", *log_args)

            if result.get("Code") != "OK":
                raise exceptions.ClientException(result["Code"], result.get("Message"))
        except Exception as e:
            self.logger.error(traceback.format_exc())

            if not silently:
                raise e

        return result


class FosunSmsMessageRequest:
    def __init__(self, sign_name=None, template_code=None, template_param=None, **kwargs):
        """
        :param sign_name:       str, 短信签名
        :param template_code:   str, 短信模板CODE
        :param template_param:  dict, 短信模板参数
        """

        self._sign_name = sign_name
        self._template_code = template_code
        self._template_param = template_param or {}

    @cached_property
    def conf(self):
        return aliyun.FosunSmsConfig()

    def _get_signature(self, params=None):
        params = params or dict(
            accessKeyId=self.conf.ACCESS_KEY_ID,
            format=self.conf.ACCEPT_FORMAT,
            timestamp=str(timezone.now().date()).replace('-', ''),
            version=self.conf.VERSION
        )
        src = '&'.join(['%s=%s' % (k, v) for k, v in sorted(params.items())]) + '&key=%s' % self.conf.ACCESS_KEY_SECRET
        return md5(src.encode('utf-8')).hexdigest().upper()

    def _get_body(self, **kwargs):
        return dict(
            phone=kwargs.get('phone'),
            signName=self.conf.SIGN_NAME,
            signCode=self.conf.SIGN_CODE,
            templateCode=self._template_code or kwargs.get('template_code'),
            templateParam=json.dumps(self._template_param or kwargs.get('template_param'))
        )

    def _get_headers(self):
        return {
            'Content-Type': 'application/json',
            'authorization': self.conf.ACCESS_KEY_ID + ':' + self._get_signature(),
            'format': self.conf.ACCEPT_FORMAT,
            'timestamp': str(timezone.now().date()).replace('-', ''),
            'version': self.conf.VERSION
        }

    def send_sms(self, phone_numbers, send_type, template_code=None, template_param=None):
        sms_rets = []
        sms_api = "https://{domain}{path}".format(domain=self.conf.SMS_DOMAIN, path=self.conf.SMS_ONE_API)

        if send_type == SmsTypeEnum.LOGIN.type:
            sms_code = "".join([random.choice(string.digits) for _ in range(6)])
            template_param = dict(code=sms_code)
            template_code = self.conf.LOGIN_TEMPLATE_CODE

        elif send_type == SmsTypeEnum.CALL_NOTIFY.type:
            template_code = self.conf.CALL_NOTIFY_TEMPLATE_CODE

        elif send_type == SmsTypeEnum.CALL_UPDATE.type:
            template_code = self.conf.CALL_UPDATE_TEMPLATE_CODE

        elif send_type == SmsTypeEnum.CALL_START.type:
            template_code = self.conf.CALL_START_TEMPLATE_CODE

        for phone in phone_numbers or []:
            body = self._get_body(
                phone=phone,
                template_code=template_code,
                template_param=template_param
            )
            headers = self._get_headers()

            try:
                r = requests.post(sms_api, data=json.dumps(body), headers=headers)
                _sms_ret = r.json()
                sms_rets.append(dict(
                    phone=phone, send_type=send_type,
                    params=template_param, data=_sms_ret
                ))

                logger.info('FosunSmsMessageRequest.send_sms Ret: %s', _sms_ret)
            except Exception as e:
                logger.error('FosunSmsMessageRequest.send_sms => error: %s', e)
                logger.error(traceback.format_exc())

        return sms_rets

    def _check_sign(self, resp_dict):
        """ 验证微信返回的签名 """
        if 'sign' not in resp_dict:
            return False

        wx_sign = resp_dict['sign']
        sign = self._get_signature(resp_dict)

        if sign == wx_sign:
            return True

        return False

