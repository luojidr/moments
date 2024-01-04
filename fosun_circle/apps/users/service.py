import logging
import string
import random
from copy import deepcopy

from django.core.cache import cache
from rest_framework.response import Response

from . import models
from .serializers import UsersSerializer
from config.conf.aliyun import FosunSmsConfig
from fosun_circle.apps import BaseSerializerRequest
from fosun_circle.core.ding_talk.uuc import UUCUser
from fosun_circle.libs.exception import SmsCodeError
from fosun_circle.libs.exception import UUCUserNotExistError
from fosun_circle.core.ali_oss.sms_message import FosunSmsMessageRequest
from users.models import CircleUsersModel


class UserLoginService(BaseSerializerRequest):
    SMS_CODE_EXPIRE = 5 * 60           # 验证码有效期

    def send_sms_code(self):
        country_code = self.get_value("country_code")
        phone_number = self.get_value("phone_number")

        cache_key = "sms_code:%s" % phone_number
        sms_code = cache.get(cache_key)
        ret = {'errno': 0, 'code': 0, 'errmsg': 'ok', 'message': '', 'status': False}

        if not sms_code:
            sms_code = "".join([random.choice(string.digits) for _ in range(6)])

            sms_ret = FosunSmsMessageRequest(
                sign_name=FosunSmsConfig.SIGN_NAME
            ).send_sms(country_code + phone_number, sms_code=sms_code)
            ret.update(sms_ret)

            if ret.get('errno') == 0:
                cache.set(cache_key, sms_code, self.SMS_CODE_EXPIRE)

        return ret

    def _get_user_or_create(self):
        sms_code = self.get_value("sms_code")
        phone_number = self.get_value("phone_number")

        if not phone_number:
            logging.info("未获取手机号，登陆失败")
            raise UUCUserNotExistError(phone_number)

        sms_code_from_cache = cache.get("sms_code:%s" % phone_number)

        if sms_code != sms_code_from_cache:
            raise SmsCodeError()

        user_obj = UUCUser(phone_number).create_uuc_user()
        return UsersSerializer(user_obj).data

    def allow_agreement(self):
        """ 用户同意协议 """
        user_id = int(self.get_value("user_id"))
        return CircleUsersModel.objects.filter(id=user_id, is_del=False).update(is_agree=True)

    def get_avatar_or_nickname(self):
        """ 获取默认头像和昵称 """
        select_type = int(self.get_value("select_type", 0))

        if select_type == 0:
            return UUCUser.get_avatar_url()

        return UUCUser.get_nick_name()

    def to_response(self):
        user_info = self._get_user_or_create()
        return Response(data=user_info)


class ListUsersResourcePermissionService(BaseSerializerRequest):
    resource_perm_model = models.CircleResourcePermissionModel
    resource_mapper_model = models.CircleUsersResourcePermissionModel

    @property
    def perm_type(self):
        return dict(self.resource_perm_model.PERM_RESOURCE)

    def _get_user_resource_mapper(self, user_id=None):
        """ 获取用户与资源权限的映射关系 """
        user_id = user_id or self._request.user.id
        mapper_queryset = self.resource_mapper_model.get_queryset_by_user_id(user_id)
        return {m["resource_perm_id"]: m["is_include"] for m in mapper_queryset}

    def _get_resource_items(self, resource_ids, perm_type=None):
        """ 获取资源或权限 """
        resource_queryset = self.resource_perm_model.get_queryset_by_ids(resource_ids, perm_type)
        return list(resource_queryset)

    @staticmethod
    def _get_module_resource_range_list(resource_items_list, user_resource_mapper):
        """ 用户的模块资源可见范围
        :param user_resource_mapper: dict, 根据 CircleUsersResourcePermissionModel 表中映射的用户资源、权限关系
        :param resource_items_list: list, 根据 `user_resource_mapper` 过滤的用户具体资源、权限信息
        """
        module_resource_range_list = []

        for module_resource_item in filter(lambda item: item["perm_type"] == 1, resource_items_list):
            module_resource_id = module_resource_item["id"]
            has_module = user_resource_mapper.get(module_resource_id, False)

            copy_module_resource_item = deepcopy(module_resource_item)
            copy_module_resource_item.update(has_module=has_module)

            module_resource_range_list.append(copy_module_resource_item)

        return module_resource_range_list

    def _get_tabbar_have_resource_permission(self, tarbar_module_name, resource_items_list, user_resource_mapper):
        """ tabBar 拥有的模块资源范围
        :param tarbar_module_name: str, tabBar 名称
        :param resource_items_list: list, 根据 `user_resource_mapper` 过滤的用户具体资源、权限信息
        :param user_resource_mapper: list, 根据 CircleUsersResourcePermissionModel 表中映射的用户资源、权限关系
        """
        data = {}
        tabbar_func = (lambda it: it["module_name"] == tarbar_module_name and it["perm_type"] == 2)
        tabbar_have_resource_module_list = list(filter(tabbar_func, resource_items_list))

        # 模块可见范围 {模块ID: 模块 Item}
        # 是否拥有模块资源 (如果用户没有模块，则tabBar也不会有该模块的可见范围)
        module_resource_range_list = self._get_module_resource_range_list(resource_items_list, user_resource_mapper)
        module_range_dict = {item["component"]: item for item in module_resource_range_list}

        for tabbar_item in tabbar_have_resource_module_list:
            component = tabbar_item.get("component", "")
            module_param_name = tabbar_item.get("param_name", "")
            module_label = tabbar_item.get("name", "")

            module_item = module_range_dict.get(component, {})
            has_module = module_item.get("has_module", False)  # 是否拥有模块资源

            if has_module:
                data[module_param_name] = dict(component=component, label=module_label)
            else:
                data[module_param_name] = False

        return data

    def _get_module_have_resource_permission(self, resource_items_list, user_resource_mapper):
        """ 模块拥有的资源与权限
        :param resource_items_list: list, 根据 `user_resource_mapper` 过滤的用户具体资源、权限信息
        :param user_resource_mapper: list, 根据 CircleUsersResourcePermissionModel 表中映射的用户资源、权限关系
        """
        def is_include(resource_perm_item):
            """ 判断用户是否拥有该资源 """
            resource_perm_id = resource_perm_item.get("id")
            resource_perm_param_name = resource_perm_item.get("param_name", "")
            has_resource_perm = user_resource_mapper.get(resource_perm_id, False)

            return resource_perm_param_name, has_resource_perm

        data = {}
        module_resource_range_list = self._get_module_resource_range_list(resource_items_list, user_resource_mapper)

        for module_resource_item in module_resource_range_list:
            has_module = module_resource_item.get("has_module", False)

            module_name = module_resource_item.get("module_name", "")
            param_name = module_resource_item.get("param_name", "")

            component = module_resource_item.get("component", "")
            module_label = module_resource_item.get("name", "")

            # 模块拥有的资源
            resource_func = (lambda i: i["module_name"] == module_name and i["perm_type"] == 3)
            module_resource_list = list(filter(resource_func, resource_items_list))

            # 模块拥有的权限
            permission_func = (lambda i: i["module_name"] == module_name and i["perm_type"] == 4)
            module_permission_list = list(filter(permission_func, resource_items_list))

            if has_module:
                data[param_name] = dict(component=component, label=module_label)
                # 解析模块资源
                data[param_name]["resource_list"] = {} if module_resource_list else False

                for resource_item in module_resource_list:
                    resource_param_name, has_resource = is_include(resource_item)

                    if not has_resource:
                        data[param_name]["resource_list"].setdefault(resource_param_name, False)
                    else:
                        resource_label = resource_item.get("name", "")
                        resource_component = resource_item.get("component", "")

                        data[param_name]["resource_list"].setdefault(
                            resource_param_name,
                            dict(component=resource_component, label=resource_label)
                        )

                # 解析模块权限
                data[param_name]["permission"] = {} if module_permission_list else False

                for perm_item in module_permission_list:
                    data[param_name]["permission"].setdefault(*is_include(perm_item))

            else:
                data[param_name] = False

        return data

    def get_resource_and_permission_info(self, user_id=None):
        """ 获取资源列表与权限信息
        注意:
            (1): tabbar 资源列表根据资源表中含有共同的 module_name, 并依据相同的 component 组件找到资源列表
            (2): 模块所拥有的资源和权限列表，根据权限表有相同的 module_name 来确定
            (3): 用户所有的资源与权限映射关系在 CircleUsersResourcePermissionModel 表中，
                 并依据映射关系是否存在或 is_include=False 确定
        """
        data = {}

        resource_mapper_dict = self._get_user_resource_mapper(user_id)
        resource_items_list = self._get_resource_items(resource_mapper_dict.keys())

        # 解析资源与权限
        for tab_bar_item in filter(lambda item: item["perm_type"] == 0, resource_items_list):
            resource_id = tab_bar_item["id"]
            tarbar_param_name = tab_bar_item["param_name"]
            tarbar_module_name = tab_bar_item["module_name"]
            is_include = resource_mapper_dict.get(resource_id, False)       # 是有拥有该 tabBar

            if is_include:
                # tabBar 拥有的模块资源范围
                tabbar_have_module_range = self._get_tabbar_have_resource_permission(
                    tarbar_module_name,
                    resource_items_list,
                    resource_mapper_dict
                )
                data[tarbar_param_name] = tabbar_have_module_range

                # 模块拥有的资源与权限
                module_have_resource_permission = self._get_module_have_resource_permission(
                    resource_items_list,
                    resource_mapper_dict,
                )
                data.update(**module_have_resource_permission)

            else:
                data[tarbar_module_name] = False

        return self.to_response(**data)

    def to_response(self, **kwargs):
        return Response(data=kwargs)
