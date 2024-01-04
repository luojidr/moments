try:
    import simplejson as json
except ImportError:
    import json

import re
import traceback

import coreapi
from django.urls import reverse
from django.http.request import QueryDict
from django.utils.deprecation import MiddlewareMixin
from django.http.response import HttpResponseBase
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.template.response import TemplateResponse

from rest_framework import status
from rest_framework import exceptions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings

from . import get_request_view_class
from fosun_circle.libs.utils.camel_underline import camel_dict, underline_dict
from fosun_circle.constants.enums.code_message import CodeMessageEnum
from fosun_circle.constants.constant import REQUEST_PARAMS_NEGOTIATOR_CAMEL
from fosun_circle.constants.constant import RESPONSE_CONTENT_NEGOTIATOR_CAMEL
from fosun_circle.libs.log import dj_logger as logger


class ResponseMiddlewareBase:
    def select_parser(self, request, parsers=None):
        parsers = parsers or api_settings.DEFAULT_PARSER_CLASSES
        content_type = request.META.get('CONTENT_TYPE', request.META.get('HTTP_CONTENT_TYPE', ''))

        negotiator = api_settings.DEFAULT_CONTENT_NEGOTIATION_CLASS()
        parser = negotiator.select_parser(request, parsers)

        if not parser:
            raise exceptions.UnsupportedMediaType(content_type)

        return parser, content_type

    def get_request(self, request):
        parsers = [parser() for parser in api_settings.DEFAULT_PARSER_CLASSES]

        return Request(
            request,
            parsers=parsers, authenticators=(),
            negotiator=None, parser_context=None
        )

    @staticmethod
    def _get_raw_response_data(response):
        raw_data = response.data
        return raw_data

    def get_query_dict(self, params_or_data):
        if not isinstance(params_or_data, dict):
            raise ValidationError("params_or_data is not dictionary object.")

        query_dict = QueryDict(mutable=True)

        for param, value in underline_dict(params_or_data).items():
            query_dict.appendlist(param, value)

        query_dict._mutable = False
        return query_dict

    def convert_standard_data(self, data, request=None):
        """ 将最终的响应数据转为下划线命名 """
        if data.get("code") != 200:
            data.update(data=None)

        if isinstance(data.get("data"), dict) and 'code' in data['data'] and data['data']['code'] != 200:
            data.update(data=None, code=data['data']["code"], message=data['data'].get("message"))

        if request is None:
            return camel_dict(data)

        view_class = get_request_view_class(request=request)
        if getattr(view_class, RESPONSE_CONTENT_NEGOTIATOR_CAMEL, False):
            return camel_dict(underline_params=data)

        return data


class HttpResponseMiddleware(MiddlewareMixin, ResponseMiddlewareBase):
    def process_exception(self, request, exc):
        """ 处理Django异常, DRF框架有自己的异常处理钩子 """
        cls_name = self.__class__.__name__
        logger.info("Middleware<%s>.process_exception => Request: %s, exc: %s", cls_name, request, exc)

        logger.info("--------------- Django <%s> throw error ---------------", cls_name)
        logger.error(traceback.format_exc())

        code = getattr(exc, "code", 500)
        exc_args = getattr(exc, "args", ())

        if len(exc_args) > 1:
            code, message = exc_args[0], exc_args[1]
        else:
            message = exc_args[0] if exc_args else getattr(exc, "msg", str(exc))

        error_data = dict(code=code, message=message)

        # 基本的异常处理, 默认path为 /api/ 或 视图类有API的认为是接口API
        if request.path.startswith("/api/"):
            return JsonResponse(data=error_data, status=500)

        else:
            view_cls = get_request_view_class(request=request)

            # 视图类以 api 结尾，可能继承 django 或 drf
            if view_cls.__name__.lower().endswith("api"):
                return JsonResponse(data=error_data, status=500)

    def process_request(self, request):
        cls_name = self.__class__.__name__
        params, form_data = request.GET, request.POST
        content_type = request.headers.get("Content-Type", "")
        msg = "Middleware<%s>.process_request => Request: %s, params: %s, data: %s"

        logger.info(msg, cls_name, request, params, form_data)
        logger.info("Middleware<%s>.process_request => request.headers[Content-Type]: %s", cls_name, content_type)

        view_class = get_request_view_class(request=request)
        params_negotiator_camel = getattr(view_class, REQUEST_PARAMS_NEGOTIATOR_CAMEL, False)

        if params_negotiator_camel:
            request.GET = self.get_query_dict(params)
            request.POST = self.get_query_dict(form_data)

        # Content_Type: application/json 是否转驼峰
        if "application/json" in content_type and request.body:
            body_data = json.loads(request.body)

            if params_negotiator_camel:
                request._body = json.dumps(underline_dict(body_data)).encode("utf-8")

            logger.info("=> Request json body: {}".format(body_data))

    def process_view(self, request, callback, callback_args, callback_kwargs):
        msg = "Middleware<%s>.process_view => Request:%s, callback:%s, callback_args:%s, callback_kwargs:%s"
        logger.info(msg, self.__class__.__name__, request, callback, callback_args, callback_kwargs)

    def process_response(self, request, response):
        msg = "Middleware<%s>.process_response => Request: %s, Response:%s\n"
        logger.info(msg, self.__class__.__name__, request, response)

        # Django-Debug-Toolbar | 微信
        if request.path.startswith("/__debug__/") or request.path.startswith(reverse("wechat_robot")):
            logger.info("__debug__ | Werobot response => %s", response)
            return response

        is_raw_response = getattr(response, "_raw_response", False)
        not hasattr(response, "data") and setattr(response, "data", None)
        data = dict(code=CodeMessageEnum.OK_200.code, message=CodeMessageEnum.OK_200.message, data=None)

        # 必须直接返回的response:
        if is_raw_response or \
           (request.path.startswith('/static/') or request.path.endswith('.css') or request.path.endswith('.js')) or \
           isinstance(response.data, coreapi.Document) or \
           isinstance(response, (StreamingHttpResponse, TemplateResponse, HttpResponseRedirect)) or \
           (isinstance(response, HttpResponseBase) and response.get("Content-Disposition")):
            # coreapi.Document: swagger 文档
            # django.http.FileResponse: Django 文件
            # django.http.HttpResponseRedirect: 重定向
            # CSS,JS
            return response

        try:
            content = response.content

            # 网页、模板、重定向 直接返回
            if re.compile(rb"<!DOCTYPE").search(content):
                return response

            raw_result = response.data or json.loads(content)
        except (TypeError, AttributeError, json.JSONDecodeError):
            raw_result = {}

        # 以下全部为api
        if status.is_success(response.status_code):
            data.update(data=raw_result)
        else:
            data.update(
                code=raw_result.pop("code", None) or response.status_code,
                message=str(raw_result.pop("message", ""))
            )

        cookies = response.cookies
        standard_data = self.convert_standard_data(data, request=request)

        if not isinstance(response, Response):
            # 不是 rest_framework 标准响应, 是：Django.http.response.JsonResponse
            response = JsonResponse(data=standard_data)
        else:
            response.data = standard_data
            response._is_rendered = False

        if hasattr(response, "render"):
            response.render()

        response.cookies = cookies
        response["Access-Control-Allow-Origin"] = "*"
        return response
