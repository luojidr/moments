import time
import random
import string
import base64
import logging
import traceback
from collections import deque
from typing import List, Union, Dict

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from fosun_circle.libs import exception
from fosun_circle.libs.utils.crypto import AESHelper
from fosun_circle.core.db.base import BaseAbstractModel

UserModel = get_user_model()


class ApiInvokerClientModel(BaseAbstractModel):
    DEFAULT_EXPIRE_IN = 1 * 60 * 60
    SEQUENCE = string.digits + string.ascii_letters

    name = models.CharField('Invoker Client', max_length=200, default='', blank=True)
    client_id = models.CharField('Invoker Client ID', max_length=8, blank=True)
    salt = models.CharField('Token Salt', max_length=16, default=None, blank=True)
    app_key = models.CharField(verbose_name="AppKey", max_length=100, unique=True, default="", blank=True)
    app_secret = models.CharField(verbose_name="AppSecret", max_length=200, default="", blank=True)
    access_token = models.CharField(verbose_name="Token", max_length=500, default="", blank=True)
    expire_at = models.DateTimeField(verbose_name='Expiration', default='1979-01-01 00:00:00', blank=True)
    remark = models.CharField(verbose_name="Token", max_length=200, db_index=True, default="", blank=True)

    class Meta:
        db_table = 'circle_permission_api_invoker_client'

    @classmethod
    def _get_unique_value(cls, name, k, sequence=None):
        max_times = 100
        unique_val = None
        attr_set = set(cls.objects.values_list(name, flat=True))

        while max_times > 0:
            unique_val = "".join(random.choices(sequence or cls.SEQUENCE, k=k))
            if unique_val[0] == '0':
                continue

            if unique_val not in attr_set:
                break

            max_times -= 1

        if unique_val is None:
            raise ValueError("无法生成三方客户<%s>惟一标识" % name)

        return unique_val

    @classmethod
    def create_invoker_client(cls, name, remark=None):
        get_sequence = (lambda k: "".join(random.choices(cls.SEQUENCE, k=k)))
        client_id = cls._get_unique_value('client_id', k=6, sequence=string.digits)

        salt = get_sequence(k=16)
        app_secret = get_sequence(k=64)
        app_key = cls._get_unique_value('app_key', k=32)

        invoker_obj = cls.objects.create(
            name=name, client_id=client_id, salt=salt,
            app_key=app_key, app_secret=app_secret, remark=remark or ""
        )
        invoker_obj.set_token()

        return invoker_obj.to_dict()

    def set_token(self):
        timestamp = int(time.time())
        expire_in = self.DEFAULT_EXPIRE_IN
        expire_at = timezone.datetime.fromtimestamp(timestamp + expire_in)
        raw_text = "%s:%s:%s:%s" % (self.client_id, self.app_key, self.app_secret, timestamp)

        if self.is_expired():
            encrypt_text = AESHelper(key=self.salt).encrypt(raw=raw_text)
            access_token = base64.b64encode(encrypt_text.encode()).decode()
            self.access_token = access_token

        self.expire_at = expire_at
        self.save()

    def is_expired(self):
        expire_at = self.expire_at

        if isinstance(expire_at, str):
            expire_at = timezone.datetime.strptime(expire_at, "%Y-%m-%d %H:%M:%S")

        timestamp = expire_at.timestamp() if expire_at else 0
        return time.time() > timestamp

    @classmethod
    def get_invoker_object(cls, access_token):
        invoker_obj = cls.objects.filter(is_del=False, access_token=access_token).first()
        if invoker_obj is None:
            raise exception.InvalidTokenError("非法API Token ，疑似非法用户！")

        try:
            encrypt_text = base64.b64decode(invoker_obj.access_token)
            plain_text = AESHelper(key=invoker_obj.salt).decrypt(text=encrypt_text)
            client_id, app_key, app_secret, _ = plain_text.split(':')
        except Exception as e:
            logging.error(traceback.format_exc())
            raise exception.InvalidTokenError("API Token 解析错误，请检查token！")

        if (client_id != invoker_obj.client_id or
                app_key != invoker_obj.app_key or
                app_secret != invoker_obj.app_secret):
            raise exception.InvalidTokenError("API Token 非法注册，请联系管理员核查！")

        if invoker_obj.is_expired():
            raise exception.ExpiredTokenError("API Token 已过期！")

        return invoker_obj


class ApiInvokerUriModel(BaseAbstractModel):
    invoker = models.ForeignKey(to=ApiInvokerClientModel, null=True, on_delete=models.SET_NULL, blank=True)
    name = models.CharField(verbose_name="Invoker Name", max_length=100, default="", blank=True)
    url = models.CharField(verbose_name="Invoker URL", max_length=200, default="", blank=True)

    class Meta:
        db_table = 'circle_permission_api_invoker_url'
        ordering = ['-id']

    @classmethod
    def check_invoker_urls(cls, api_path, invoker_id=None):
        invoker_id = invoker_id or 0
        queryset = cls.objects.filter(invoker_id=invoker_id, is_del=False).values_list('url', flat=True)

        if api_path not in set(queryset):
            raise exception.UriForbiddenError("没有权限调用该接口: %s" % api_path)

    @classmethod
    def has_api_path(cls, api_path):
        return cls.objects.filter(url=api_path, is_del=False).exists()


class MenuModel(BaseAbstractModel):
    # 菜单栏等级
    MENU_LEVEL_CHOICES = [
        (0, '根'),
        (1, '一级菜单'),
        (2, '二级菜单'),
        (3, '三级菜单'),
    ]

    name = models.CharField('Menu Name', max_length=200, default='', blank=True)
    icon = models.CharField('Menu Icon', max_length=200, default='', blank=True)
    app = models.CharField('Menu Belong to App', max_length=200, default='', blank=True)
    url = models.CharField('Menu Url', max_length=500, default='', blank=True)
    component_name = models.CharField('Vue Component Name', max_length=200, default='', blank=True)
    parent_id = models.IntegerField('Parent Menu ID', default=0, blank=True)
    menu_order = models.IntegerField('Menu Order', default=1, blank=True)
    level = models.SmallIntegerField('Menu Level', choices=MENU_LEVEL_CHOICES, default=1, blank=True)
    is_hidden = models.BooleanField('Hidden', default=False, blank=True)
    remark = models.CharField('Remark', max_length=200, default='', blank=True)

    class Meta:
        db_table = 'circle_permission_menu'
        ordering = ('parent_id', 'level', 'menu_order')

    def __str__(self):
        return self.name

    @classmethod
    def get_menu_tree(cls, menu_queryset=None, is_leaf: bool = True):
        """ 菜单树
        :param menu_queryset: 可选，用户组的菜单集
        :param is_leaf: bool, True 全部菜单, False 不包括叶子菜单
        :return:
        """
        menu_tree = {}
        fields = ['id', 'name', 'app', 'url', 'icon', 'parent_id']

        if menu_queryset is None:
            menu_queryset = cls.objects.filter(is_del=False).values(*fields)
        elif not menu_queryset:
            return {}

        for menu in menu_queryset:
            if isinstance(menu, cls):
                menu_item = {attr: getattr(menu, attr) for attr in fields}
            else:
                menu_item = menu

            menu_id = menu_item['id']
            parent_id = menu_item['parent_id']
            menu_item.update(value=menu_id, label=menu_item.pop('name'), is_leaf=True)
            parent_path = menu_item.setdefault('parent_path', [])  # 当前菜单的父菜单路径

            menu_tree[menu_id] = menu_item  # 更新menu_item

            if parent_id in menu_tree:
                parent_menu = menu_tree[parent_id]
                parent_menu['is_leaf'] = False
                parent_menu.setdefault('children', []).append(menu_item)

                # 更新当前菜单的父菜单路径
                p_menu_parent_path = parent_menu['parent_path']  # 父菜单的父菜单路径
                parent_path.extend(p_menu_parent_path + [parent_menu['label']])

        menu_tree = menu_tree.get(settings.MENU_ROOT_ID, {})

        # 判断是否需要叶子菜单
        if not is_leaf:
            q = deque([menu_tree])

            while q:
                menu_item = q.popleft()
                new_child_menus = [
                    child_menu
                    for child_menu in menu_item.pop('children', [])
                    if not child_menu['is_leaf']
                ]

                q.extend(new_child_menus)
                new_child_menus and menu_item.update(children=new_child_menus)

        return menu_tree


class GroupModel(BaseAbstractModel):
    name = models.CharField('Group Name', max_length=200, default='', blank=True)
    desc = models.CharField('Desc', max_length=500, default='', blank=True)

    # many_to_many: menu, group; related_name: 反向查询
    # through_fields: 第一个字段必须是本模型的
    menus = models.ManyToManyField(MenuModel, related_name='menu_groups',
                                   through='GroupOwnedMenuModel', through_fields=['group', 'menu'])

    # many_to_many: user, group; related_name: 反向查询
    menu_users = models.ManyToManyField(UserModel, related_name='menu_groups',
                                        through='OwnerToMenuPermissionModel', through_fields=['group', 'user'])

    class Meta:
        db_table = 'circle_permission_group'
        ordering = ('id', )

    def get_menus(self, ordering=()):
        menu_queryset = self.menus.filter(is_del=False).all()

        if ordering:
            menu_queryset = menu_queryset.order_by(*ordering).all()

        return menu_queryset

    def get_menu_users(self):
        menu_users = self.menu_users.filter(is_del=False).all()
        return menu_users

    def get_menu_tree_by_group(self):
        menu_ids_list = []
        menu_tree = MenuModel.get_menu_tree(menu_queryset=self.get_menus())
        q = [(menu_tree, (settings.MENU_ROOT_ID, ))] if menu_tree else []

        while q:
            menu_item, menu_ids = q.pop(0)  # left pop
            children = menu_item.get('children', [])

            if not children:
                menu_ids_list.append(menu_ids)

            for child_menu in children:
                child_menu_ids = list(menu_ids)
                child_menu_ids.append(child_menu['id'])
                q.append((child_menu, tuple(child_menu_ids)))

        return dict(menu_tree=menu_tree, menu_ids=menu_ids_list)

    @classmethod
    def get_group_list(cls, user_id: int, first_id: Union[int, None] = None) -> List[dict]:
        """ 获取用户所有的用户组权限 """
        user = UserModel.objects.get(id=user_id or 0, is_del=False)
        if not user:
            raise ValueError('用户为空')

        group_list = []
        queryset = user.menu_groups.filter(is_del=False).all()

        for obj in queryset:
            group_id = obj.id
            item = dict(id=group_id, name=obj.name)

            if group_id == first_id:
                group_list.insert(0, item)
            else:
                group_list.append(item)

        return group_list

    @classmethod
    def get_menu_permissions(cls, user_id: int, group_id: Union[int, None] = None):
        """ 反向查询: 获取用户对应的菜单组，进而获取该用户的的菜单权限 """
        user = UserModel.objects.get(id=user_id or 0, is_del=False)

        if not user:
            raise ValueError('用户为空')

        group_query = dict(is_del=False)
        group_id and group_query.update(id=group_id)
        group_queryset = user.menu_groups.filter(**group_query).all()
        only_group_obj = group_queryset.first()

        if only_group_obj:
            group_id = only_group_obj.id
            menu_queryset = only_group_obj.get_menus()
            root_menu_id = menu_queryset.get(parent_id=0).id

            menu_list = [menu.to_dict(exclude=['level', 'menu_order']) for menu in menu_queryset]
            menu_map = {menu_item['id']: menu_item for menu_item in menu_list}

            for menu_item in menu_list:
                menu_item.pop('id')
                parent_id = menu_item.pop('parent_id')

                if parent_id:
                    menu_map[parent_id].setdefault('models', []).append(menu_item)
        else:
            group_id = 0
            root_menu_id = 0
            menu_map = {}

        menus_config = dict(
            system_keep=True, dynamic=True, group_id=group_id,
            menus=menu_map.get(root_menu_id, {}).get('models', []),
        )
        return menus_config

    def update_owned_users_or_menus(self,
                                    user_ids: Union[List[int], None] = None,
                                    menu_ids: Union[List[List[int]], None] = None
                                    ):
        if user_ids:
            m2m_field = self.menu_users
            require_bound_ids = user_ids
        else:
            m2m_field = self.menus
            require_bound_ids = [menu_id for sub_menu_ids in menu_ids for menu_id in sub_menu_ids]

        queryset = m2m_field.filter(is_del=False).all()
        db_bound_ids = [obj.id for obj in queryset]

        # 新增需要绑定的用户/菜单
        add_bound_ids = list(set(require_bound_ids) - set(db_bound_ids))
        m2m_field.add(*add_bound_ids)

        # 用户设置为管理员
        if m2m_field.target_field_name == 'user':
            m2m_field.filter(is_del=False).update(is_active=True, is_staff=True, is_superuser=True)

        # 删除未绑定的用户/菜单
        remove_bound_ids = list(set(db_bound_ids) - set(require_bound_ids))
        m2m_field.remove(*remove_bound_ids)


class GroupOwnedMenuModel(BaseAbstractModel):
    menu = models.ForeignKey(to=MenuModel, null=True, on_delete=models.SET_NULL)
    group = models.ForeignKey(to=GroupModel, null=True, on_delete=models.SET_NULL)
    reason = models.CharField('进组原因', max_length=100, default='', blank=True)

    class Meta:
        db_table = 'circle_permission_group_owned_menus'


class OwnerToMenuPermissionModel(BaseAbstractModel):
    """ many_to_many: user, group """
    user = models.ForeignKey(UserModel, null=True, on_delete=models.SET_NULL)
    group = models.ForeignKey(GroupModel, null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'circle_permission_owner_to_menus'
