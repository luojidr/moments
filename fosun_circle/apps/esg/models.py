from collections import deque

from django.db import models
from django.contrib.auth import get_user_model

from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.core.db.base import BaseAbstractModel
from users.models import CircleUsersModel, CircleUser2DepartmentModel, CircleDepartmentModel

UserModel = get_user_model()


class ESGAdminModel(BaseAbstractModel):
    """ ESG 管理员配置 """
    PERMISSION_TYPE_CHOICES = [
        (1, '超级管理员'),
        (2, '分站管理员'),
    ]

    user = models.ForeignKey(UserModel, null=True, on_delete=models.SET_NULL, blank=True)
    dep_name = models.CharField(max_length=200, verbose_name="所属部门", default="", blank=True)
    dep_id = models.CharField(max_length=200, verbose_name="部门标识", default="", blank=True)
    permission_type = models.SmallIntegerField(choices=PERMISSION_TYPE_CHOICES, default=None, null=True, blank=True)
    priority = models.IntegerField(verbose_name="权限优先级", default=1, null=True, blank=True)

    class Meta:
        db_table = 'circle_esg_admin'
        ordering = ['-id', 'priority']

        unique_together = ['user', 'dep_id', 'permission_type']


class ESGEntryDepartmentModel(BaseAbstractModel):
    """ esg入口权限部门或产业 """
    ENTRY_ROOT_ID = 'entry_root'

    dep_id = models.CharField(max_length=200, unique=True, verbose_name="部门标识", default="")
    dep_name = models.CharField(max_length=200, verbose_name="部门名称", default="")
    parent_dep_id = models.CharField(max_length=200, verbose_name="上级部门标识", default=ENTRY_ROOT_ID)
    parent_dep_name = models.CharField(max_length=200, verbose_name="上级部门名称", default='')
    is_active = models.BooleanField(verbose_name="是否有效", default=True)

    class Meta:
        db_table = 'circle_esg_entry_department'
        ordering = ['-id']

    @classmethod
    def get_entry_department_tree(cls):
        # 入口规则：目前只限定用户一级部门(集团本、大快乐、大健康等)，不限定子部门的入口权限
        entry_dep_tree = {}
        queryset = cls.objects.filter(is_del=False, is_active=True, parent_dep_id='root').values('dep_id')
        # dep_tree = CircleDepartmentModel.get_department_tree('root')

        # 如果具体到子部门的入口权限，需要用组织树来控制（本期不考虑）
        # for entry_dep_item in dict(**entry_dep_dict).values():
        #     parent_dep_id = entry_dep_item['parent_dep_id']
        #
        #     if parent_dep_id in entry_dep_dict:
        #         entry_dep_dict[parent_dep_id].setdefault('children', []).append(entry_dep_item)

        # return entry_dep_dict[cls.ENTRY_ROOT_ID].get('children', [{}])[0]
        return queryset


class EsgEntryUserModel(CircleUsersModel):
    class Meta:
        proxy = True

    @classmethod
    def get_entry_user_permission(cls, mobile):
        """ 用户部门 """
        user = cls.objects.filter(phone_number=mobile, is_del=False).first()
        usr_id = user and user.usr_id
        user_info = user and user.to_dict() or {}

        dep_dict = {}
        query = dict(is_alive=True, is_del=False)
        user2dep = CircleUser2DepartmentModel.objects.filter(usr_id=usr_id, **query).order_by('-display_order').all()
        q = deque([ud.dep_id for ud in user2dep])

        while q:
            dep_id = q.popleft()
            dep_obj = CircleDepartmentModel.objects.filter(dep_id=dep_id, **query).first()

            if dep_obj:
                parent_dep_id = dep_obj.parent_dep_id
                dep_dict[dep_id] = dict(
                    dep_id=dep_id, dep_name=dep_obj.dep_name,
                    parent_dep_id=parent_dep_id, dep_en_name=dep_obj.dep_en_name,
                )

                if parent_dep_id != '-1':
                    q.append(parent_dep_id)

        for dep_item in dict(**dep_dict).values():
            parent_dep_id = dep_item['parent_dep_id']

            if parent_dep_id in dep_dict:
                dep_dict[parent_dep_id].setdefault('children', []).append(dep_item)

        return dict(user_info, dep_list=dep_dict['root'].get('children', []))

    @classmethod
    def has_user_entry_permission(cls, mobile):
        """ esg-用户入口权限 """
        user = cls.objects.filter(phone_number=mobile, is_del=False).first()
        if user is None:
            logger.info('用户<mobile:%s>不存在，没有ESG入口权限', mobile)
            return False

        entry_dep_tree = ESGEntryDepartmentModel.get_entry_department_tree()
        user2dep = CircleUser2DepartmentModel.objects\
            .filter(usr_id=user.usr_id, is_alive=True, is_del=False)\
            .order_by('-display_order')\
            .values_list('first_dep', flat=True)
        first_dep_list = list(user2dep)

        for entry_dep in entry_dep_tree:
            dep_id = entry_dep['dep_id']

            if dep_id in first_dep_list:
                logger.info('用户<mobile:%s>拥有ESG入口权限，entry_dep：%s', mobile, entry_dep)
                return True

        logger.info('用户<mobile:%s>存在，但没有ESG入口权限', mobile)
        return False


class ESGTaskActionModel(BaseAbstractModel):
    # entry_dep = models.ForeignKey(to=ESGEntryDepartmentModel, null=True, on_delete=models.SET_NULL, blank=True)
    name = models.CharField(verbose_name="任务名称", max_length=200, null=True, default="", blank=True)
    task_id = models.CharField(verbose_name="任务唯一标识", max_length=200, unique=True, null=True, default="", blank=True)
    tag_id = models.IntegerField(verbose_name="任务发帖所属标签ID", default=1, null=True, blank=True)
    tips = models.CharField(verbose_name="任务发帖内容提示", max_length=200, null=True, default="", blank=True)
    credits = models.IntegerField(verbose_name="任务发帖对应的积分", default=0, null=True, blank=True)
    esg_url = models.CharField(verbose_name="跳转到ESG URL", max_length=500, null=True, default="", blank=True)
    circle_url = models.CharField(verbose_name="跳转到星圈URL", max_length=500, null=True, default="", blank=True)

    class Meta:
        db_table = 'circle_esg_task_action'
        ordering = ['-id']


class ESGTaskActionLogModel(BaseAbstractModel):
    STATE_CHOICES = [
        (1, '发帖成功'),
        (2, '发帖失败'),
    ]

    action_id = models.IntegerField(verbose_name="任务动作ID", default=None, null=True, blank=True)
    circle_id = models.IntegerField(verbose_name="发帖ID", default=None, null=True, blank=True)
    mobile = models.CharField(verbose_name="发帖人手机号", max_length=200, null=True, default="")
    state = models.SmallIntegerField(choices=STATE_CHOICES, default=None, null=True, blank=True)

    class Meta:
        abstract = True
        # db_table = 'circle_esg_entry_department'
        # ordering = ['-id']
