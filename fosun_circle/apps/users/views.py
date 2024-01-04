import random
import traceback
from datetime import datetime

from django.urls import reverse
from django.conf import settings
from django.shortcuts import render
from django.core.exceptions import ValidationError
from django.views.generic import TemplateView, View
from django.middleware.csrf import get_token as get_csrf_token
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib.auth import get_user_model

from django_redis import get_redis_connection
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.schemas import AutoSchema
import coreapi
from django_otp import match_token

from . import models
from . import forms
from . import serializers
from .service import UserLoginService, ListUsersResourcePermissionService

from esg.models import EsgEntryUserModel
from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.core.ding_talk.uuc import DingUser
from fosun_circle.contrib.drf.throttling import ApiSMSStrictRateThrottle
from fosun_circle.middleware.auth_token import payload_handler, encode_handler, decode_handler

_overseas_text = '(海外)' if settings.IS_OVERSEAS_REGION else ''
EXTRA_CONTEXT = dict(
    app_list=[],
    site_title=settings.T_SITE_TITLE + _overseas_text,
    site_header=settings.T_SITE_HEADER + _overseas_text,
)


class LogoutView(View):
    def get(self, request):
        """ 登出 """
        response = HttpResponseRedirect(reverse("login"))
        response.delete_cookie("csrftoken")
        response.delete_cookie("X-Auth")

        return response


class LoginView(TemplateView):
    """ 用户登录 """
    template_name = "login.html"
    extra_context = EXTRA_CONTEXT
    EXPIRATION_DELTA = settings.JWT_AUTH['JWT_EXPIRATION_DELTA']

    def post(self, request, *args, **kwargs):
        """ 登录认证 """
        _format = request.GET.get("format")
        user_model = get_user_model()
        form = forms.AuthLoginForm(request, request.POST)
        is_valid = form.is_valid()
        logger.info('LoginView form => is_valid: %s, errors: %s', is_valid, form.errors)

        if is_valid:
            user = form.user_cache
            is_required_2fa = form.cleaned_data['is_required_2fa']

            credentials = {
                user_model.USERNAME_FIELD: form.cleaned_data["username"],
                "password": form.cleaned_data["password"],      # encrypt password
            }
            # user = authenticate(**credentials)
            payload = payload_handler(user)
            token = encode_handler(payload)

            if _format == "json":
                response = JsonResponse(data=dict(x_auth=token, is_required_2fa=is_required_2fa))
            else:
                response = HttpResponseRedirect(reverse("index"))
                response.set_cookie("X-Auth", token, expires=datetime.utcnow() + self.EXPIRATION_DELTA)

            return response

        if _format == "json":
            return JsonResponse(data=dict(x_auth=None, message="用户名密码错误", code=500))

        return render(request, self.template_name, context=dict(form=form))

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        response = self.render_to_response(context)

        x_auth = request.GET.get("token")
        x_auth = x_auth or request.COOKIES.get("X-Auth") or request.headers.get("X-Auth")
        logger.info("LoginView.X-Auth: %s", x_auth)

        if x_auth:
            payload = decode_handler(token=x_auth)
            if payload.get("exp") - datetime.utcnow().timestamp() > 0:
                response = HttpResponseRedirect(reverse("index"))
                response.set_cookie("X-Auth", x_auth, expires=datetime.utcnow() + self.EXPIRATION_DELTA)

        return response


class IndexView(TemplateView):
    """ 首页 """
    template_name = "index.html"
    extra_context = EXTRA_CONTEXT


class RegisterView(TemplateView):
    """ 用户注册 """
    template_name = "register.html"
    extra_context = EXTRA_CONTEXT

    def post(self, request, *args, **kwargs):
        """ 注册 """
        form = forms.RegisterForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            email_code = form.cleaned_data["email_code"]

            if models.UserCaptchaCodeModel.validate_expiration(email=email, captcha=email_code):
                models.UsersModel.create_user(email=email)

            return HttpResponseRedirect(reverse("login"))

        return render(request, self.template_name, context=dict(form=form))


class UserSmsCodeApi(APIView):
    throttle_classes = (ApiSMSStrictRateThrottle, )
    schema = AutoSchema(
        manual_fields=[
            coreapi.Field(name='country_code', required=True, location='form', description='国家码', type='string'),
            coreapi.Field(name='phone_number', required=True, location='form', description='手机号', type='string'),
        ])

    def post(self, request, *args, **kwargs):
        """ 获取短信验证码 """
        return Response(data=UserLoginService(request=request).send_sms_code())


class CsrfTokenApi(APIView):
    def get(self, request, *args, **kwargs):
        token = get_csrf_token(request)
        logger.info("Csrftoken: %s", token)

        return Response(data=dict(csrf_token=token))


class AllowAgreementApi(APIView):
    schema = AutoSchema(
        manual_fields=[
            coreapi.Field(name='user_id', required=True, location='form', description='用户id', type='integer'),
        ])

    def put(self, request, *args, **kwargs):
        """ 同意协议 """
        rows = UserLoginService(request=request).allow_agreement()
        return Response(data=dict(rows=rows))


class ListUsersResourcePermissionApi(APIView):
    schema = AutoSchema(
        manual_fields=[
            coreapi.Field(name='user_id', required=True, location='query', description='用户id', type='integer'),
        ])

    def get(self, request, *args, **kwargs):
        """ 用户权限 """
        return ListUsersResourcePermissionService(request=request).get_resource_and_permission_info()


class DefaultAvatarNicknameApi(APIView):
    schema = AutoSchema(
        manual_fields=[
            coreapi.Field(name='select_type', required=True, location='query', description='0:头像 1：昵称', type='integer'),
        ])

    def get(self, request, *args, **kwargs):
        """ 获取默认头像和昵称 """
        return Response(data=UserLoginService(request=request).get_avatar_or_nickname())


class ListFuzzyRetrieveUserApi(generics.GenericAPIView):
    serializer_class = serializers.ListFuzzyRetrieveUserSerializer

    schema = AutoSchema(
        manual_fields=[
            coreapi.Field(name='key', required=True, location='query', description='搜索内容', type='string'),
        ])

    def get_option_user_list_by_mobile(self, mobile_list=None, params=None):
        """ 针对前段下拉人员列表 """
        params = params or {}
        mobile_list = mobile_list or []

        if not mobile_list:
            mobiles = [s.strip() for s in params.get("mobile", "") if s.strip()]
            mobile_list = mobile_list or mobiles or params.get("mobile_list", [])

        queryset = models.CircleUsersModel.objects.filter(phone_number__in=mobile_list).order_by("id")
        serializer = self.serializer_class(queryset, many=True)

        return serializer.data

    def get_queryset(self):
        key = self.request.query_params.get("key", "")
        filter_kwargs = dict(is_del=False)

        if key.isdigit() and len(key) == 11:
            filter_kwargs.update(phone_number=key)
        else:
            filter_kwargs.update(username__icontains=key)

        queryset = models.CircleUsersModel.objects.filter(**filter_kwargs).order_by("id")[:10]
        return queryset

    def get(self, request, *args, **kwargs):
        """ 模糊搜索人员(手机号或姓名) """
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)


class DepartmentRetrieveApi(generics.GenericAPIView):
    def get_queryset(self):
        key = self.request.query_params.get("key", "")
        return models.CircleDepartmentModel.get_department_tree()

    def get(self, request, *args, **kwargs):
        """ 模糊搜索部门 """
        department_tree_dict = self.get_queryset()
        return JsonResponse(data=department_tree_dict)


class ResetPasswordApi(APIView):
    def post(self, request, *args, **kwargs):
        """ 重置用户密码 """
        mobile = request.data.get("username")
        password = request.data.get("password")
        code = request.data.get("code")

        redis_conn = get_redis_connection()
        redis_key = "user:mailCode:%s" % mobile
        mail_code = redis_conn.get(redis_key)

        if not mobile or not password:
            raise ValidationError("用户名或密码不能为空")

        if mail_code != code:
            raise ValidationError("验证码错误")

        user = models.CircleUsersModel.objects.filter(phone_number=mobile, is_del=False).first()
        if not user:
            raise ValidationError("用户<%s> 不存在" % mobile)

        user.set_password(raw_password=password)
        user.save()
        return Response(data=None)


class SendEmailCodeApi(APIView):
    def _send_mail_by_outlook(self, to, mail_code):
        from exchangelib import DELEGATE, Account, Credentials, Message, Mailbox, \
            HTMLBody, Configuration, NTLM, FileAttachment
        from exchangelib.protocol import BaseProtocol, NoVerifyHTTPAdapter
        import urllib3

        BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter
        urllib3.disable_warnings()

        is_ok = False
        email_host_user = 'ihcm@fosun.com'
        email_host_pwd = 'rZ4R7QiF'
        email_host = 'mail.fosun.com'

        credentials = Credentials(email_host_user, email_host_pwd)
        config = Configuration(server=email_host, credentials=credentials, auth_type=NTLM)
        account = Account(
            primary_smtp_address=email_host_user,
            config=config, autodiscover=False, access_type=DELEGATE
        )

        html_body = """
            <div>该验证码仅用于密码重置服务: <span style="color:red">{mail_code}</span></div>
            <p></p>
            <div style="color:red;font-size: 14px">注意: 30分钟内有效。</div>
        """.format(mail_code=mail_code)
        msg = Message(
            account=account,
            subject='您收到星圈服务的邮件验证码',
            body=HTMLBody(html_body),
            to_recipients=[Mailbox(email_address=to)],
        )

        try:
            msg.send()
            is_ok = True
        except Exception:
            logger.error(traceback.format_exc())

        return is_ok

    def post(self, request, *args, **kwargs):
        """ 发送邮件校验 """
        mobile = request.data.get("username")
        mail_code = "".join(
            [random.choice("123456789")] +
            [random.choice("123456789") for _ in range(4)]
        )

        if not mobile:
            raise ValidationError("username 参数错误")

        user = models.CircleUsersModel.objects.filter(phone_number=mobile, is_del=False).first()
        if not user:
            raise ValidationError("用户<%s> 不存在" % mobile)

        # is_ok = self._send_mail(to=user.email, mail_code=mail_code)
        is_ok = self._send_mail_by_outlook(to=user.email, mail_code=mail_code)

        if not is_ok:
            raise ValidationError("邮件发送失败")

        redis_key = "user:mailCode:%s" % mobile
        redis_conn = get_redis_connection()
        redis_conn.set(redis_key, mail_code, ex=1800)

        return Response(data=None)


class TwoFactorAuthenticationApi(APIView):
    def post(self, request, *args, **kwargs):
        mobile = request.data.get("mobile")

        if not mobile:
            x_auth = request.COOKIES.get("X-Auth")
            try:
                payload = decode_handler(x_auth)
                mobile = payload.get("phone_number")
            except Exception as e:
                logger.error(traceback.format_exc())

        otp_info = models.OtpTotpUserModel.get_or_create_2fa(mobile=mobile)
        return Response(data=otp_info)


class ConfirmTwoFactorApi(APIView):
    def post(self, request, *args, **kwargs):
        code_2fa = request.data.get("code_2fa")

        if not match_token(request.user, code_2fa):
            raise ValueError("认证失败， 您没有权限查看任务监控！")

        return Response(data=None)


class DingEmployeeApi(APIView):
    def get(self, request, *args, **kwargs):
        """ 星圈获取人员信息接口
        @mobile: 获取钉钉或UUC人员信息
        @dd_code: 通过钉钉code方式获取人员信息(更安全)
        """
        mobile = request.query_params.get('mobile')
        dd_code = request.query_params.get('dd_code')

        if mobile:
            user = models.CircleUsersModel.objects.filter(phone_number=mobile, is_del=False).first()
            dd_params = dict(mobile=mobile)
        elif dd_code:
            user, dd_params = None, dict(code=dd_code)
        else:
            raise ValueError('mobile或dd_code不能为空')

        if user is None:
            try:
                ding_user = DingUser(**dd_params).get_ding_user()
                email, position_chz = ding_user.get('email', ''), ding_user.get('position', '')
                avatar, username = ding_user.get('avatar', ''), ding_user.get('name', '')
                ding_job_code, departmentName = ding_user.get('userid', ''), ''

                user = models.CircleUsersModel(
                    source="DING_API", phone_number=mobile,
                    avatar=avatar, state_code=ding_user.get('stateCode', ''),
                    position_chz=position_chz, ding_job_code=ding_job_code
                )
                user.set_password(models.CircleUsersModel.DEFAULT_PASSWORD)
                user.save()
            except Exception as e:
                logger.error(traceback.format_exc())
                return Response(data=dict(errcode=10004, data=[], msg="钉钉用户<%s>不存在" % dd_params))
        else:
            email, mobile = user.email, user.phone_number
            position_chz, avatar = user.position_chz, user.avatar
            username, ding_job_code = user.username, user.ding_job_code
            departmentName = user.department_chz

        employee = dict(
            email=email, mobile=mobile,
            department=[dict(departmentName=departmentName)],
            titleDesc=position_chz, avatar=avatar,
            fullname=username, jobCode=ding_job_code,
        )
        return Response(data=dict(errcode=0, data=[employee]))


class DingDingUserApi(APIView):
    throttle_classes = ()

    def get(self, request, *args, **kwargs):
        mobile = request.query_params.get('mobile')
        dd_code = request.query_params.get('code')
        ding_user = DingUser(mobile=mobile, code=dd_code).get_ding_user()

        mobile = ding_user.get('mobile')
        dd_user_data = dict(
            email=ding_user.get('email', ''), avatar=ding_user.get('avatar', ''),
            position_chz=ding_user.get('position', ''), username=ding_user.get('name', ''),
            ding_job_code=ding_user.get('userid', ''), state_code=ding_user.get('stateCode', ''),
        )

        if not models.CircleUsersModel.objects.filter(phone_number=mobile, is_del=False).first():
            user = models.CircleUsersModel(source="DD_API", phone_number=mobile, **dd_user_data)
            user.set_password(models.CircleUsersModel.DEFAULT_PASSWORD)
            user.save()

        return Response(data=dict(mobile=mobile, **dd_user_data))


class UserPermissionApi(APIView):
    def post(self, request, *args, **kwargs):
        mobile = request.user.mobile
        has_esg_entry = EsgEntryUserModel.has_user_entry_permission(mobile)

        return Response(data=dict(
            has_esg_entry=has_esg_entry,
        ))
