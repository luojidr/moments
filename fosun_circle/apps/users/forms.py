from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.utils.translation import gettext_lazy as _
from django.utils.text import capfirst
from django.core.exceptions import ValidationError
from django_otp import match_token

from . import models
from fosun_circle.libs.utils.crypto import AESCipher, AESHelper
from fosun_circle.libs.log import dj_logger as logger

UserModel = get_user_model()


class AuthLoginForm(forms.Form):
    """ django.contrib.admin.forms:AdminAuthenticationForm """
    username = UsernameField(widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )

    # is_required_2fa: 登录页是否需要二因子验证， 否：用户名密码登录
    is_required_2fa = forms.BooleanField(label=_("is_required_2fa"), required=False)

    # 需要二因子验证后(is_required_2fa=true)， is_open_2fa: 展示二因子输入框
    is_open_2fa = forms.BooleanField(label=_("is_open_2fa"), required=False)
    code_2fa = forms.CharField(label=_("code_2fa"), required=False)

    error_messages = {
        'invalid_login': _(
            "用户名和密码不正确: 注意大小写"
        ),
        'inactive': _("This account is inactive."),
        'forbidden': _("您没有登录管理后台的权限，请联系管理员!"),
    }

    def __init__(self, request=None, *args, **kwargs):
        """
        The 'request' parameter is set for custom auth use by subclasses.
        The form data comes in via the standard 'data' kwarg.
        """
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

        # Set the max length and label for the "username" field.
        self.username_field = UserModel._meta.get_field(UserModel.USERNAME_FIELD)
        username_max_length = self.username_field.max_length or 254
        self.fields['username'].max_length = username_max_length
        self.fields['username'].widget.attrs['maxlength'] = username_max_length
        if self.fields['username'].label is None:
            self.fields['username'].label = capfirst(self.username_field.verbose_name)

    def clean(self):
        username = self.cleaned_data.get('username')
        en_password = self.cleaned_data.get('password')
        csrf_token = self.data.get("csrfmiddlewaretoken", "")

        try:
            password = AESCipher(key=csrf_token[:16]).decrypt(en_password)
        except Exception as e:
            raise ValidationError("登录密码加密错误")

        if username is not None and password:
            credentials = {
                self.username_field.column: username,
                "password": password
            }
            logger.info('AuthLoginForm credentials: %s', credentials)
            user = authenticate(self.request, **credentials)
            logger.info('AuthLoginForm user: %s, info: %s', not user, user and user.to_dict())

            if not user:
                raise self.get_invalid_login_error()
            else:
                self.user_cache = user
                self.confirm_login_allowed(self.user_cache)
                self.cleaned_data['is_required_2fa'] = self.user_cache.is_required_2fa

        # 双因子认证
        if self.cleaned_data['is_required_2fa'] and self.cleaned_data["is_open_2fa"]:
            code_2fa = self.cleaned_data["code_2fa"]
            if not match_token(self.user_cache, code_2fa):
                raise ValueError("双因子认证失败")

        return self.cleaned_data

    def confirm_login_allowed(self, user):
        """
        Controls whether the given User may log in. This is a policy setting,
        independent of end-user authentication. This default behavior is to
        allow login by active users, and reject login by inactive users.

        If the given user cannot log in, this method should raise a
        ``ValidationError``.

        If the given user may log in, this method should return None.
        """
        if not user.is_active:
            raise ValidationError(
                self.error_messages['inactive'],
                code='inactive',
            )

        if not user.is_staff:
            raise ValidationError(
                self.error_messages['invalid_login'],
                code='invalid_login',
                params={'username': self.username_field.verbose_name}
            )

        if not user.is_superuser:
            raise ValidationError(
                self.error_messages['forbidden'],
                code='forbidden',
                params={'username': self.username_field.verbose_name}
            )

    def get_user(self):
        return self.user_cache

    def get_invalid_login_error(self):
        return ValidationError(
            self.error_messages['invalid_login'],
            code='invalid_login',
            params={'username': self.username_field.verbose_name},
        )


class RegisterForm(forms.Form):
    mobile = forms.CharField(required=False, min_length=11, max_length=11, help_text="注册手机号")
    email = forms.EmailField(help_text="注册邮箱")
    template_type = forms.IntegerField(help_text="验证码类型")
    email_code = forms.CharField(min_length=4, max_length=4, help_text="邮箱验证码")
    password = forms.CharField(strip=False, help_text="注册密码")

    def clean_password(self):
        en_password = self.cleaned_data.get('password')
        csrf_token = self.data.get("csrfmiddlewaretoken", "")

        password = AESCipher(key=csrf_token).decrypt(en_password)
        return password

    def clean_email_code(self):
        email = self.cleaned_data.get("email")
        email_code = self.cleaned_data.get("email_code")

        captcha_obj = models.UserCaptchaCodeModel.objects.filter(email=email).order_by("-create_time")

        if captcha_obj and captcha_obj[0].captcha == email_code:
            return email_code
        else:
            raise ValidationError("邮箱验证码错误")




