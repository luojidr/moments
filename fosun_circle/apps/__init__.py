from abc import ABCMeta, abstractmethod

from rest_framework import serializers

from fosun_circle.libs.utils import camel_underline
from fosun_circle.libs.exception import (
    SerializerNotExist
)


class BaseSerializerRequest(metaclass=ABCMeta):
    """ 解析请求参数名由驼峰转下划线 """

    empty_values = (None, '', [], (), {})

    serializer_class = None

    def __init__(self, request=None, **kwargs):
        if request is None and kwargs.get("request") is None:
            raise ValueError("request 参数未解析")

        self._request = request or kwargs.pop("request", None)
        req_params = camel_underline.underline_dict(kwargs)

        # request.query_params
        raw_req_params = camel_underline.underline_dict(self._request.query_params)
        self.req_params = dict(req_params, **raw_req_params)

        # request.data
        self.req_data = camel_underline.underline_dict(self._request.data)

        if request and request.method in ["POST", "PUT"]:
            if self.serializer_class:
                if not isinstance(self.serializer_class, serializers.SerializerMetaclass):
                    raise SerializerNotExist()

                self.req_data = self.serializer_class(self.req_data).data

    def __getitem__(self, name):
        return self.req_params.get(name) or self.req_data.get(name)

    def get_value(self, name, default=None):
        return self.__getitem__(name) or default

    def is_boolean(self, value):
        if value in self.empty_values:
            return False

        if value in (True, False):
            # 1/0 are equal to True/False. bool() converts former to latter.
            return bool(value)

        if value in ('t', 'True', '1', "false"):
            return True

        if value in ('f', 'False', '0', "true"):
            return False

        return bool(value)

    @abstractmethod
    def to_response(self, **kwargs):
        """ 返回字典 """
        raise NotImplemented


