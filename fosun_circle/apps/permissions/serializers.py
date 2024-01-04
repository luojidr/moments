import enum

from django.db.models import Q
from django.utils.functional import cached_property
from rest_framework import serializers

from .models import ApiInvokerClientModel, ApiInvokerUriModel
from .models import GroupModel, MenuModel, OwnerToMenuPermissionModel, GroupOwnedMenuModel
from users.serializers import SimpleUsersSerializer


class MenuPositionEnum(enum.Enum):
    FIRST = (0, "submenu-first")    # 父菜单的第一个菜单: 即首位
    PREV = (-1, "peer-prev")        # 同级(兄弟)菜单前一个
    NEXT = (1, "peer-next")         # 同级(兄弟)菜单后一个

    @property
    def pos(self):
        return self.value[0]

    @property
    def alias(self):
        return self.value[1]

    @classmethod
    def iterator(cls):
        return iter(cls._member_map_.values())


class MenuSerializer(serializers.ModelSerializer):
    # level: 展示名字，而不是数字
    level = serializers.CharField(source='get_level_display', read_only=True, max_length=100, help_text="层级")
    parent_path = serializers.SerializerMethodField()
    positionMenu = serializers.SerializerMethodField()

    class Meta:
        model = MenuModel
        fields = model.fields() + ['parent_path', 'positionMenu']

    @cached_property
    def root_menu_tree(self):
        return self.Meta.model.get_menu_tree()

    @cached_property
    def menu_parent_paths(self):
        # 计算菜单的父路径
        menu_parent_dict = {}
        stack = [self.root_menu_tree]

        while stack:
            menu = stack.pop(0)
            menu_parent_dict[menu['id']] = ' / '.join(menu['parent_path'])
            stack.extend(menu.get('children') or [])

        return menu_parent_dict

    def get_parent_path(self, obj):
        return self.menu_parent_paths.get(obj.id, '')

    def get_positionMenu(self, obj):
        stack = [self.root_menu_tree]
        get_menu = (lambda x: dict(menuId=x['id'], menuName=x['label']))

        # menuId: 菜单对应位置的父或兄弟菜单的ID
        # menuName: 对应menuId的名称
        # location: 当前菜单对应menuName的位置（首页子菜单、同级菜单前一个、同级菜单后一个位置）
        position_menu = dict(menuId=0, menuName='', position='')

        while stack:
            menu = stack.pop(0)
            child_menus = menu.get('children', [])
            stack.extend(child_menus)

            for index, child_menu in enumerate(child_menus):
                if obj.id == child_menu['id']:
                    if index == 0:
                        if len(child_menus) == 1:
                            position = MenuPositionEnum.FIRST.alias
                            pos_menu = get_menu(menu)
                        else:
                            position = MenuPositionEnum.PREV.alias
                            pos_menu = get_menu(child_menus[index - MenuPositionEnum.PREV.pos])
                    else:
                        position = MenuPositionEnum.NEXT.alias
                        pos_menu = get_menu(child_menus[index - MenuPositionEnum.NEXT.pos])

                    position_menu.update(pos_menu, position=position)
                    break

        return position_menu

    def reorder_position_menus(self, instance):
        """ 调整同级菜单位置顺序 """
        Model = self.Meta.model
        parent_ids = self.initial_data.get('parentIds', [])
        position_menu = self.initial_data.get('positionMenu')

        if not position_menu:
            instance.delete()
            raise ValueError('未设置菜单<name: %s>顺序' % instance.name)

        if not any([position_menu['position'] == e.alias for e in MenuPositionEnum.iterator()]):
            instance.delete()
            raise ValueError('菜单<name: %s>位置顺序不合法' % instance.name)

        menu_id = position_menu['menuId']
        position = position_menu['position']

        if position == MenuPositionEnum.FIRST.alias:
            instance.parent_id = menu_id  # 更新父菜单ID
            instance.level = len(parent_ids) + 1

            # 验证是否为合法的父菜单
            parent_menu = Model.objects.get(id=instance.parent_id)
            if parent_menu.url.strip():
                instance.delete()
                raise ValueError('菜单<name: %s>不能作为父菜单' % parent_menu.name)
        else:
            instance.level = len(parent_ids)
        instance.save()

        query = dict(parent_id=instance.parent_id, is_del=False)
        objects = list(Model.objects.filter(~Q(id=instance.id), **query).all())

        for i, menu_obj in enumerate(objects):
            if menu_obj.id == menu_id:
                if position == MenuPositionEnum.FIRST.alias:
                    objects.insert(0, instance)
                elif position == MenuPositionEnum.PREV.alias:
                    objects.insert(i, instance)
                elif position == MenuPositionEnum.NEXT.alias:
                    objects.insert(i + 1, instance)

                break
        else:
            if objects:
                instance.delete()
                raise ValueError('未匹配菜单<name: %s>位置' % instance.name)

        for j, menu_obj in enumerate(objects):
            menu_obj.menu_order = j + 1
            menu_obj.save()

    def create(self, validated_data):
        instance = super().create(validated_data)
        self.reorder_position_menus(instance)

        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self.reorder_position_menus(instance)

        return instance


class GroupSerializer(serializers.ModelSerializer):
    # queryset = MenuModel.objects.filter(is_del=False).all()  # 多对多 queryset 忽略

    # menus = serializers.StringRelatedField(many=True, read_only=True, allow_null=True)  # 多对多单个字段
    # menu_users = serializers.StringRelatedField(many=True, read_only=True, allow_null=True)  # 多对多单个字段

    menus = MenuSerializer(many=True, read_only=True)
    menu_users = SimpleUsersSerializer(many=True, read_only=True)

    menu_ids = serializers.SerializerMethodField()

    class Meta:
        model = GroupModel
        fields = model.fields() + ['menus', 'menu_users', 'menu_ids']

    def update(self, instance, validated_data):
        user_ids = self.initial_data.get('menu_users') or []  # [1, 2, 3, 4, ...]
        menu_ids = self.initial_data.get('menus') or []  # menu ids: [[1,2,3], [1,2,4], ....]

        # 处理用户组绑定的用户权限
        instance.update_owned_users_or_menus(user_ids=user_ids)

        # 处理用户组绑定的菜单权限
        instance.update_owned_users_or_menus(menu_ids=menu_ids)

        return self.Meta.model.objects.get(id=instance.id)

    def get_menu_ids(self, obj):
        menu_info = obj.get_menu_tree_by_group()
        return menu_info['menu_ids']


class ApiInvokerClientSerializer(serializers.ModelSerializer):
    expire_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, help_text="有效期")

    class Meta:
        model = ApiInvokerClientModel
        fields = model.fields()


class ApiInvokerUrlSerializer(serializers.ModelSerializer):
    # ApiInvokerClientSerializer：可序列化，但不能反序列化(入库错误)
    # invoker = ApiInvokerClientSerializer()

    # 注意: 外键反序列化（OK）
    # 1) 使用 PrimaryKeyRelatedField 字段
    # 2) 序列化字段名与外键字段名保持一致
    invoker = serializers.PrimaryKeyRelatedField(many=False, queryset=ApiInvokerClientModel.objects.all())
    invoker_name = serializers.CharField(source='invoker.name', read_only=True, max_length=100, help_text="API用户名")
    invoker_client_id = serializers.CharField(source='invoker.client_id', read_only=True, max_length=20, help_text="ClientId")
    invoker_app_key = serializers.CharField(source='invoker.app_key', read_only=True, max_length=100, help_text="AppKey")

    class Meta:
        model = ApiInvokerUriModel
        fields = model.fields() + ['invoker', 'invoker_name', 'invoker_client_id', 'invoker_app_key']

