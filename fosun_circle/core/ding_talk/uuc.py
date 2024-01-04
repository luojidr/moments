import random
import os.path

import requests
from django.conf import settings
from django.db import transaction

from .open_api import BaseDingMixin
from fosun_circle.libs.decorators import to_retry
from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.libs.utils.validators import PhoneValidator
from fosun_circle.libs.exception import PhoneValidateError, UUCUserNotExistError
from users.models import (
    CircleUsersModel,
    CircleGroupModel,
    CircleGroupUsersModel,
    CircleUsersVirtualRoleModel
)

__all__ = ["UUCUser", 'DingUser']


class DingUser(BaseDingMixin):
    def __init__(self, mobile=None, code=None):
        super().__init__()
        self._code = code
        self._mobile = mobile

    def get_ding_user(self, userid=None, code=None, mobile=None):
        """ Obtain user by userid """
        if not userid:
            userid = self._get_userid_user_by_code(code)

        if not userid:
            userid = self._get_userid_by_mobile(mobile)

        result = self._client.user.get(userid=userid)
        logger.error("DingUser._get_ding_user_by_userid => userid: %s, result: %s", userid, result)

        if result['errcode'] == 0:
            return result

        logger.error('无法获取钉钉人员信息，可能mobile或code参数错误，请检查！')

    def _get_userid_by_mobile(self, mobile=None):
        mobile = mobile or self._mobile
        if not mobile:
            return

        resp = self._client.post(
            '/topapi/v2/user/getbymobile',
            {'mobile': mobile}
        )
        result = resp.json()
        logger.error("DingUser._get_userid_by_mobile => mobile: %s, result: %s", mobile, result)

        if result['errcode'] == 0:
            return result['result']['userid']

    def _get_userid_user_by_code(self, code=None):
        """ 通过code获取钉钉userid """
        code = code or self._code
        if not code:
            return

        result = self._client.user.getuserinfo(code=code)
        logger.info('DingUser._get_ding_user_by_code => code: %s, resp: %s', code, result)

        if result['errcode'] == 0:
            return result['userid']


class UUCUser(object):
    _uuc_url = settings.UUC_URL

    def __init__(self, phone, validator=PhoneValidator, **kwargs):
        self._phone = phone or ""
        self._validator = validator(phone)

        self._avatar = kwargs.get("avatar", "")

    @to_retry
    def get_uuc_user(self, is_phone_check=False):
        """ 通过 UUC 接口获取用户信息
            返回值符合 UsersModel 字段
        """
        if is_phone_check and not self._validator():
            raise PhoneValidateError()

        params = dict(mobile=self._phone)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"}
        resp = requests.get(self._uuc_url, params=params, headers=headers, timeout=5)
        data = resp.json()

        logger.info("UUCUser.get_uuc_user api:%s, params:%s\ndata:%s", self._uuc_url, params, data)

        if data.get("errcode") != 0:
            raise UUCUserNotExistError(self._phone)

        data = data.get("data", [{}])[0]
        detail_depart = data["department"][0] if data.get("department") else {}
        uuc_user = dict(
            username=data.get("fullname", ""), email=data.get("email", ""),
            state_code=data.get("stateCode", ""), phone_number=data.get("mobile", ""),
            position_chz=data.get("titleDesc", ""), position_eng=data.get("title_en", ""),
            department_chz=detail_depart.get("departmentName", ""),
            department_eng=detail_depart.get("departmentEnName", ""),
            ding_job_code=data.get("jobCode", ""), avatar=data.get("avatar", "") or self._avatar,
            # dept_id=detail_depart.get("depId", ""), ding_id=detail_depart.get("depDDId", ""),
            usr_id=data.get("usrId", "")
        )

        return uuc_user

    def create_uuc_user(self):
        """ 通过 UUC, 创建或修改用户 """
        try:
            uuc_user = self.get_uuc_user()
        except UUCUserNotExistError:
            uuc_user = None
        except Exception as e:
            logger.warning("Mobile: %s, 调用uuc接口错误: %s", self._phone, str(e))
            return

        with transaction.atomic():
            if uuc_user is None:
                self._delete_circle_user()
            else:
                user_obj = self._add_or_update_circle_user(uuc_user=uuc_user)

        if uuc_user is None:
            logger.warning("通过uuc接口获取钉钉用户不存在, mobile: %s", self._phone)
            raise UUCUserNotExistError(self._phone)

        return user_obj

    @staticmethod
    def get_nick_name():
        """ 随机获取昵称 """
        file_path = os.path.join(settings.ROOT_DIR, settings.APP_NAME, "static")
        filename = os.path.join(file_path, "nick_name.txt")

        with open(filename, "r", encoding="utf-8") as fp:
            nick_name_list = fp.readlines() or [""]
            return random.choice(nick_name_list).strip()

    @staticmethod
    def get_avatar_url():
        """ 随机获取默认头像 """
        avatar_url = settings.DEFAULT_AVATAR_URL % random.randint(1, 101)
        return avatar_url

    def _delete_circle_user(self):
        """ 删除用户及相关 """
        group_obj, is_ok_group = CircleGroupModel.objects.get_or_create(name="复星集团")
        user_obj = CircleUsersModel.objects.filter(phone_number=self._phone, is_del=False).first()

        if user_obj is not None:
            user_obj.employee_status = 2
            user_obj.is_del = True
            user_obj.save()

            master_virtual_obj = CircleUsersVirtualRoleModel.objects \
                .filter(user_id=user_obj.id, role_type=0, is_del=False) \
                .first()

            if master_virtual_obj is not None:
                master_virtual_obj.is_del = True
                master_virtual_obj.save()

            group_user_obj = CircleGroupUsersModel.objects \
                .filter(group_id=group_obj.id, user_id=user_obj.id, is_del=False) \
                .first()

            if group_user_obj is not None:
                group_user_obj.is_del = True
                group_user_obj.save()

    def _add_or_update_circle_user(self, uuc_user):
        """ 新增用户及相关
        :param uuc_user, dict
        """
        group_obj, is_ok_group = CircleGroupModel.objects.get_or_create(name="复星集团")
        user_obj = CircleUsersModel.objects.filter(phone_number=self._phone, is_del=False).first()

        if user_obj is None:
            user_obj = CircleUsersModel(source="UUC", **uuc_user)
            user_obj.set_password(CircleUsersModel.DEFAULT_PASSWORD)
            user_obj.save()
        else:
            # 更新用户基本信息
            for key, value in uuc_user.items():
                attr_val = user_obj.__dict__.get(key)

                if value and attr_val != value:
                    user_obj.__dict__[key] = value

            user_obj.save()

        master_virtual_obj = CircleUsersVirtualRoleModel.objects \
            .filter(user_id=user_obj.id, role_type=0, is_del=False) \
            .first()

        if master_virtual_obj is None:
            nick_name = self.get_nick_name()
            CircleUsersVirtualRoleModel.objects.create(
                user_id=user_obj.id,
                role_avatar=user_obj.avatar,
                nick_name=nick_name
            )

        group_user_obj = CircleGroupUsersModel.objects \
            .filter(group_id=group_obj.id, user_id=user_obj.id, is_del=False) \
            .first()

        if group_user_obj is None:
            CircleGroupUsersModel.objects.create(group_id=group_obj.id, user_id=user_obj.id)

        return user_obj

