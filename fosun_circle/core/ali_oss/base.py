import logging

try:
    from functools import cached_property
except ImportError:
    from django.utils.functional import cached_property

from aliyunsdkcore.client import AcsClient

from config.conf import aliyun


class AliOssBase(object):
    ACCEPT_FORMAT = "json"
    PROTOCOL_TYPE = "https"  # https | http
    DEFAULT_REGION_ID = "cn-hangzhou"  # cn-shanghai | oss-cn-shanghai

    def __init__(self,
                 region_id=DEFAULT_REGION_ID,
                 access_key_id=None,
                 access_key_secret=None,
                 **kwargs
                 ):
        self._region_id = region_id
        self._access_key_id = access_key_id or self.conf.ACCESS_KEY_ID
        self._access_key_secret = access_key_secret or self.conf.ACCESS_KEY_SECRET

        self._client = AcsClient(self._access_key_id, self._access_key_secret, self._region_id, **kwargs)

    @cached_property
    def conf(self):
        return aliyun.AliOssConfig()

    @cached_property
    def logger(self):
        _logger = logging.getLogger("django")
        return _logger
