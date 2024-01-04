import os.path
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from users.models import CircleUsersModel
from permissions.models import MenuModel, GroupModel, GroupOwnedMenuModel, OwnerToMenuPermissionModel


def add_menu_permissions_to_user(mobile, group_name=None, ordered_menu_ids=None, group_id=None):
    user = CircleUsersModel.get_user_by_mobile(mobile=mobile, add_uuc=False)
    assert user, 'mobile: %s does not exist' % mobile
    assert group_name or group_id, '菜单组名和菜单组id不能同时为空'

    if group_id:
        group = GroupModel.objects.get(id=group_id)
    else:
        group = GroupModel.objects.get_or_create(name=group_name)

    if ordered_menu_ids:
        ordered_menu_ids.sort()
    else:
        ordered_menu_ids = MenuModel.objects.filter(is_del=False).order_by('id').values_list('id', flat=True)

    for menu_id in ordered_menu_ids:
        gom, _ = GroupOwnedMenuModel.objects.get_or_create(menu_id=menu_id, group=group)
        # gom.reason = 'SYS'
        # gom.save()

    OwnerToMenuPermissionModel.objects.get_or_create(group=group, user=user)


def sync_menus_to_local():
    queryset = MenuModel.objects.using(alias='circle').all()

    for menu_obj in queryset:
        menu_item = menu_obj.to_dict()
        menu_item.pop('id')

        MenuModel.objects.get_or_create(**menu_item)


if __name__ == '__main__':
    _ordered_menu_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    _mobile = '18101711031'

    # group_id: 1, 超级管理员全部菜单权限
    # group_id: 2, 关怀推送菜单权限
    add_menu_permissions_to_user(_mobile, group_id=1, ordered_menu_ids=None)

