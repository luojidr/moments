import os
import uuid
import json
import traceback
import asyncio
from urllib.parse import quote_plus
from datetime import datetime, timedelta
from collections import namedtuple

import jwt
from rest_framework_jwt.utils import jwt_get_secret_key
from django.conf import settings
from django.urls import reverse, NoReverseMatch, is_valid_path
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin

from django_redis import get_redis_connection
from rest_framework.status import HTTP_403_FORBIDDEN

from . import get_request_view_class
from ..libs import redis_helpers
from ..libs.log import dj_logger as logger
from ..libs.exception import AuthenticationFailed
from fosun_circle.core.globals import LocalContext
from permissions.models import ApiInvokerClientModel, ApiInvokerUriModel

User = get_user_model()
ALGORITHM = "HS256"
VERIFY_EXPIRATION = True
VERIFY = True
LEEWAY = 0
AUDIENCE = None
ISSUER = None

ApiInvokerClient = namedtuple('ApiInvokerClient', ['id', 'name', 'client_id'])


def payload_handler(user):
    username_field = get_user_model().USERNAME_FIELD
    username = user.get_username()
    payload = {
        'user_id': user.pk, 'username': username,
        'exp': datetime.utcnow() + settings.JWT_AUTH['JWT_EXPIRATION_DELTA'],
        'mobile': user.phone_number,
        User.USERNAME_FIELD: user.phone_number,
    }
    if hasattr(user, 'email'):
        payload['email'] = user.email
    if isinstance(user.pk, uuid.UUID):
        payload['user_id'] = str(user.pk)

    payload[username_field] = username

    return payload


def encode_handler(payload):
    key = settings.SECRET_KEY
    token = jwt.encode(payload, key, ALGORITHM)
    return token.decode("utf-8") if hasattr(token, "decode") else token


def decode_handler(token, secret_key=None):
    secret_key = secret_key or settings.SECRET_KEY
    options = {
        'verify_exp': VERIFY_EXPIRATION,
    }

    # get user from token, BEFORE verification, to get user secret key
    unverified_payload = jwt.decode(token, secret_key, [ALGORITHM])
    _secret_key = jwt_get_secret_key(unverified_payload)

    return jwt.decode(
        token,
        secret_key,
        # VERIFY,
        algorithms=[ALGORITHM],
        options=options,
        leeway=LEEWAY,
        audience=AUDIENCE,
        issuer=ISSUER,
    )


def response_payload_handler(token, user=None, request=None):
    return {
        'token': token
    }


class BaseAuthMiddleware:
    CACHE_PREFIX = "user_"

    def get_payload(self, token):
        # 通过X-Auth校验后，基本都是有用户的
        try:
            payload = decode_handler(token, secret_key=None)
        except Exception as e:
            logger.error("AuthTokenMiddleware => Circle Token 解析错误: %s", e)
            logger.error("\t\tCircle Token: %s, SECRET_KEY: %s", token, settings.SECRET_KEY)

            bbs_secret_key = os.environ.get('BBS_SECRET_KEY')
            try:
                payload = decode_handler(token, secret_key=bbs_secret_key)
            except Exception as e:
                logger.error("AuthTokenMiddleware => BBS Token 解析错误: %s", e)
                logger.error("\t\tBBS Token: %s, SECRET_KEY: %s", token, bbs_secret_key)
                payload = dict(user_id=0, exp=0, username="")

        return payload

    def authenticate_credentials(self, payload):
        """
        Returns an active user that matches the payload's user id and email.
        """
        username = payload.get('mobile')

        try:
            user = User.objects.get_by_natural_key(username)
        except User.DoesNotExist:
            raise AuthenticationFailed("不合法的签名")

        if not user.is_active:
            raise AuthenticationFailed("用户未激活")

        return user

    @property
    def exempt_request_path(self):
        attr = "_exempt_request_path"
        exempt_names = [
            "login", "register", "survey_media_upload", 'ali_sms_send',
            "two_factor_auth_api", "static_serve", "wechat_robot",
            'user_csrf_token', 'ding_app_msg_send', 'health_check',
            'ali_oss_anti_spam_check', 'survey_download', 'user_login_sms',
            'kpi_download', 'tag_topic_download', 'download_state',
            'file_export_test', 'gettoken_api', 'user_dd_user_api',
            'get_user_by_code_api', 'dd_custom_robot_send_api',
            'dd_devops_notify_view', 'vod_CreateUploadVideo_api',
            # "swagger_docs",
        ]

        if attr not in self.__dict__:
            exempt_path = []

            for view_name in exempt_names:
                try:
                    exempt_path.append(reverse(view_name))
                except NoReverseMatch:
                    pass

            exempt_path.extend([
                reverse("media_preview", kwargs=dict(key_name="")),
            ])

            try:
                exempt_path.append(reverse("static", kwargs=dict(path="/")))
            except NoReverseMatch:
                pass

            self.__dict__[attr] = exempt_path
            self.__dict__[attr].append("/favicon.ico")

            return exempt_path

        return self.__dict__[attr]

    def _operate_stack(self, ctx_list, action="push"):
        assert action in ["push", "pop"], "线程变量操作栈错误"

        for ctx in ctx_list:
            if action == "push":
                ctx.push()
            else:
                ctx.pop()

            ctx_label = ctx._ctx_label
            local_val = getattr(ctx, "request") if ctx_label.startswith("req") else getattr(ctx, "user")
            logger.warning("%s -> Local Thread %s, %s %s to stack!", ctx_label, ctx, action, local_val)


class AuthTokenMiddleware(MiddlewareMixin, BaseAuthMiddleware):
    """ django 用户登录认证校验 """
    def _exempt_csrf_token(self, request):
        # Avoid error: rest_framework.exceptions.PermissionDenied:
        # CSRF Failed: CSRF token missing or incorrect. But anonymous user
        # There are ways to skip CSFF validation:
        #   (1): Set request.csrf_processing_done = True, Skip all request check
        #   (2): Set callback of view function or view class to callback.csrf_exempt = True, Skip all request check
        #   (3): Set request._dont_enforce_csrf_checks = True, Skip 'POST' request check

        request._dont_enforce_csrf_checks = True

    def check_invoker_permission(self, request):
        path = request.path
        if not path.startswith('/api/'):
            return False, None

        content_type = request.content_type
        is_json = 'application/json' in content_type

        if request.GET.get('access_token'):
            access_token = quote_plus(request.GET['access_token'], safe='/=')
        else:
            access_token = request.POST.get('access_token')

        if is_json and not access_token and request.method == 'POST':
            json_data = json.loads(request.body)
            access_token = json_data.get("access_token")

        if not access_token:
            return False, None

        try:
            # 建议缓存
            if not ApiInvokerUriModel.has_api_path(path):
                return False, None

            invoker_obj = ApiInvokerClientModel.get_invoker_object(access_token=access_token)  # 校验token是否合法
            ApiInvokerUriModel.check_invoker_urls(path, invoker_id=invoker_obj.id)  # 校验api权限

            if not hasattr(request, 'api_invoker'):
                request.api_invoker = ApiInvokerClient(
                    id=invoker_obj.id, name=invoker_obj.name,
                    client_id=invoker_obj.client_id
                )
        except Exception as e:
            code = getattr(e, 'code', 4010)
            logger.error(traceback.format_exc())
            return True, JsonResponse(data=dict(code=code, message=str(e)), status=HTTP_403_FORBIDDEN)

        return True, None

    def _get_request_user(self, request, payload, redis_key=None):
        redis_conn = get_redis_connection()
        cached_user = redis_conn.hgetall(redis_key) or {}  # bool 被转成了 'True' or 'False' ???
        decode = (lambda s: s.decode() if isinstance(s, bytes) else s)

        if cached_user:
            user = User(**{decode(k): decode(v) for k, v in cached_user.items()})
        else:
            user = self.authenticate_credentials(payload)

            try:
                redis_helpers.hset(redis_key, mapping=user.to_dict(), expires=24 * 60 * 60)
            except Exception as e:
                # redis-py version > 2.10.6 raise error:
                # redis.exceptions.DataError: Invalid input of type: 'bool'. Convert to a byte, string or number first.
                logger.error('auth_token => process_request err: %s', e)
                logger.error(traceback.format_exc())

        # user 对象中可能没有 mobile
        user.mobile = user.phone_number
        request.user = user  # 保证所有的模板中包含request.user信息
        logger.info("用户登录信息 user: %s, mobile: %s", request.user, request.user.mobile)

    def process_request(self, request):
        path = request.path
        self._exempt_csrf_token(request)

        if not is_valid_path(path) and not path.startswith('/api/'):
            return HttpResponseRedirect(reverse("monitor_inner_404"))

        if any([path.startswith(prefix_path) for prefix_path in self.exempt_request_path]):
            return

        token = request.COOKIES.get("X-Auth") or request.headers.get("X-Auth")
        if not token:
            # API第三方客户调用
            is_invoker_pass, err = self.check_invoker_permission(request)
            if is_invoker_pass: return err  # API三方调用通过

            if path.startswith('/api/'):
                return JsonResponse(data=dict(code=5001, message="登录token为空", data=None), status=HTTP_403_FORBIDDEN)

            return HttpResponseRedirect(reverse("login"))

        payload = self.get_payload(token)
        log_args = (self.__class__.__name__, path, payload, token)
        logger.info("Middleware: %s, process_request => path: %s, payload: %s, X-Auth: %s", *log_args)

        if payload.get("exp") - datetime.utcnow().timestamp() <= 0:
            if path.startswith('/api/'):
                return JsonResponse(data=dict(code=5001, message="登录token过期", data=None), status=HTTP_403_FORBIDDEN)

            return HttpResponseRedirect(reverse("login"))

        cache_key = self.CACHE_PREFIX + payload.get('mobile', "")
        if cache_key == self.CACHE_PREFIX:
            logger.error('Payload中未获取到用户: 缓存Key错误')
            return JsonResponse(data=dict(code=5002, message='Payload中未获取到用户'), status=HTTP_403_FORBIDDEN)

        self._get_request_user(request, payload, cache_key)

    def __call__(self, request):
        """ request.user 入栈 """
        # Exit out to async mode, if needed
        if asyncio.iscoroutinefunction(self.get_response):
            return self.__acall__(request)
        response = None
        if hasattr(self, 'process_request'):
            response = self.process_request(request)

        # 处理 process_request 后， X-Auth可以获取当前用户
        # (1): 若 self.process_request(request) 出现异常，不会执行以下的代码(user 入栈与出栈)
        # (2): 若将 self.process_request(request) 使用 try/except ，则会继续执行以下的代码(user 入栈与出栈)
        #         try:
        #             response = self.process_request(request)
        #         except:
        #             logger.warning("%s raise Error", self.__class__.__name__)
        user = getattr(request, "user", AnonymousUser())
        ctx_list = [LocalContext(request=request, session=request.session, ctx_label="req")]

        # session 必须执行之前的session中间件的process_request
        if not isinstance(user, AnonymousUser):
            ctx_list.append(LocalContext(user=user, ctx_label="user"))

        self._operate_stack(ctx_list, action="push")

        response = response or self.get_response(request)
        if hasattr(self, 'process_response'):
            response = self.process_response(request, response)

        self._operate_stack(ctx_list, action="pop")

        return response

    def process_view(self, request, callback, callback_args, callback_kwargs):
        logger.info("Middleware<%s>.process_view", self.__class__.__name__)

    def process_exception(self, request, exception):
        logger.info("Middleware<%s>.process_exception", self.__class__.__name__)

    def process_response(self, request, response):
        logger.info("Middleware<%s>.process_response", self.__class__.__name__)
        return response

