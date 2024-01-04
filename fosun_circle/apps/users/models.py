import time
import os.path
import traceback
from operator import itemgetter
from itertools import groupby
from collections import deque

from django.conf import settings
from django.urls import reverse
from django.db import models, connections, router
from django.db.models import ObjectDoesNotExist, Q
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.contrib.auth.models import UserManager, PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.module_loading import import_string
import qrcode
from django_otp.plugins.otp_totp.models import TOTPDevice

from fosun_circle.core.db.base import BaseAbstractModel
from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.core.ali_oss.upload import AliOssFileUploader


class AbstractUser(AbstractBaseUser, PermissionsMixin, BaseAbstractModel):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Username and password are required. Other fields are optional.
    """
    DEFAULT_PASSWORD = "guest!1234"

    username_validator = UnicodeUsernameValidator()

    password = models.CharField(_('password'), max_length=128, default=DEFAULT_PASSWORD)

    # username直接控制创建超级用户(createsuperuser)与Admin登录
    username = models.CharField(
        _('username'),
        max_length=150,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
        default=""
    )
    first_name = models.CharField(_('first name'), max_length=150, blank=True, default="")
    last_name = models.CharField(_('last name'), max_length=150, blank=True, default="")
    email = models.EmailField(_('email address'), blank=True, default="")
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        abstract = True

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)


class CircleUsersModel(AbstractUser):
    """ 用户基本信息 """
    GENDER_CHOICES = [
        (0, '男'),
        (1, '女'),
        (3, '保密')
    ]

    EMPLOYEE_STATUS_CHOICES = [
        (0, "未入职"),
        (1, "已入职"),
        (2, "已离职"),
    ]

    DEFAULT_AVATAR = "http://exerland-bbs.oss-cn-shanghai.aliyuncs.com/default-profile.png"

    is_superuser = models.BooleanField(default=False, verbose_name="是否超级管理员")
    avatar = models.CharField(verbose_name="头像链接", max_length=500, default=DEFAULT_AVATAR)
    gender = models.SmallIntegerField(choices=GENDER_CHOICES, default=3, verbose_name='性别')
    birthday = models.DateField(verbose_name="出生日期", default="1979-01-01")
    phone_number = models.CharField(max_length=20, default="", unique=True, verbose_name="手机号码")
    state_code = models.CharField(max_length=10, default='+86', verbose_name='国家码')
    employee_status = models.SmallIntegerField(verbose_name="员工状态", choices=EMPLOYEE_STATUS_CHOICES, default=1)
    company = models.CharField(max_length=200, verbose_name='公司名', default='')
    department_id = models.CharField(max_length=200, verbose_name='部门ID', default='')
    department_chz = models.CharField(max_length=500, verbose_name='部门中文名', default='')
    department_eng = models.CharField(max_length=500, verbose_name='部门英文名', default='')
    position_chz = models.CharField(max_length=500, verbose_name='职位中文名', default="")
    position_eng = models.CharField(max_length=500, verbose_name='职位英文名', default="")
    is_agree = models.BooleanField(default=False, verbose_name="同意用户公告")
    ding_job_code = models.CharField(max_length=100, verbose_name="钉钉用户jobCode", default="")
    source = models.CharField(max_length=20, verbose_name="用户来源", default="SYS")
    circle_user_id = models.IntegerField(verbose_name="星圈用户ID", default=0)
    usr_id = models.CharField(verbose_name="钉钉人员唯一id", default="", max_length=200)
    is_vote_admin = models.BooleanField(default=False, verbose_name="是否问卷投票管理员")
    is_required_2fa = models.BooleanField(default=True, verbose_name="是否开启二因子验证")

    class Meta:
        db_table = "circle_users"
        verbose_name = "用户表"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username

    @classmethod
    def get_user_by_mobile(cls, mobile, add_uuc=True):
        from fosun_circle.core.ding_talk.uuc import UUCUser

        user_obj = cls.objects.filter(phone_number=mobile, is_del=False).first()

        if user_obj is None and add_uuc:
            user_obj = UUCUser(phone=mobile).create_uuc_user()

        return user_obj

    @classmethod
    def create_or_update_user_by_uuc(cls, mobile):
        from fosun_circle.core.ding_talk.uuc import UUCUser

        try:
            uuc_user = UUCUser(phone=mobile).get_uuc_user(is_phone_check=False)
            phone_number = uuc_user.get("phone_number")

            if phone_number:
                user_obj = CircleUsersModel.objects.filter(phone_number=mobile).first()
                if user_obj is None:
                    user_obj = CircleUsersModel(source="UUC_API", **uuc_user)
                    user_obj.set_password(CircleUsersModel.DEFAULT_PASSWORD)
                else:
                    uuc_user.update(is_del=False, is_active=True, is_staff=True, employee_status=1)
                    user_obj.__dict__.update(uuc_user)

                user_obj.save()
                return user_obj
        except Exception as e:
            logger.error("CircleUsersModel.create_or_update_user_by_uuc err: %s", e)
            logger.error(traceback.format_exc())

    @classmethod
    def get_job_code_list(cls, mobile_list):
        fields = ("phone_number", "ding_job_code")
        queryset = cls.objects.filter(phone_number__in=mobile_list, is_del=False).values(*fields)

        job_code_list = [qs["ding_job_code"] for qs in queryset]
        diff_mobile_list = list(set(mobile_list) - {qs["phone_number"] for qs in queryset})

        for uuc_mobile in diff_mobile_list:
            user_obj = cls.create_or_update_user_by_uuc(mobile=uuc_mobile)
            if user_obj:
                job_code_list.append(user_obj.ding_job_code)

        return job_code_list

    @classmethod
    def get_ding_users_by_dep_ids(cls, dep_ids=None):
        """ 获取部门成员

        :param dep_ids: 部门 id列表, eg: ['5fff4ae9-326d-425a-a188-106b7be22ba2']
        """
        start_time = time.time()
        department_id_set = set()
        all_department_dict = CircleDepartmentModel.get_department_tree()

        for _dep_id in dep_ids or []:
            department_tree = all_department_dict.get(_dep_id) or {}
            queue = deque([department_tree])

            while queue:
                depart_item = queue.popleft()
                depart_id = depart_item.get("value", "")
                department_id_set.add(depart_id)

                # 子部门进入队列
                queue.extend(depart_item.get("children") or [])

        dep_end_time = time.time()
        logger.info("get_ding_users_by_dep_ids => get_department_tree cost time:%s", dep_end_time - start_time)

        if not department_id_set:
            logger.info("get_ding_users_by_dep_ids => department_id_set is empty")
            return []

        # 根据部门id获取人员usr_id (数量过大，采用sql获取, 现用时6s,之前20s)
        alias = router.db_for_read(cls)
        _connection = connections[alias]
        cursor = _connection.cursor()

        raw_sql = """
            SELECT b.dep_id, a.phone_number, a.ding_job_code FROM circle_users a
            JOIN circle_user_department_relation b
            ON a.usr_id = b.usr_id AND b.is_alive=true
            WHERE a.is_del=FALSE
        """

        cursor.execute(raw_sql)
        db_fetch_result = cursor.fetchall()
        results = {tmp_item[1:] for tmp_item in db_fetch_result if tmp_item[0] in department_id_set}

        log_args = (time.time() - dep_end_time, len(results))
        logger.info("get_ding_users_by_dep_ids => total cost time: %s, len(db_results): %s", *log_args)

        ding_user_list = [dict(phone_number=item[0], ding_job_code=item[1]) for item in results]
        return ding_user_list


class CircleDepartmentModel(BaseAbstractModel):
    """ 部门上下级关系 """
    dep_name = models.CharField(max_length=200, verbose_name="部门名称", default="")
    dep_id = models.CharField(max_length=200, verbose_name="部门唯一标识", default="")
    parent_dep_id = models.CharField(max_length=200, verbose_name="上一级部门唯一标识", default="")
    dep_only_code = models.CharField(max_length=200, verbose_name="部门 Only Code", default="")
    dep_en_name = models.CharField(max_length=200, verbose_name="部门英文名称", default="")
    display_order = models.IntegerField(verbose_name="部门在钉钉展示顺序", default=0)
    name_path = models.CharField(max_length=200, verbose_name="部门唯一路径", default="")
    is_alive = models.BooleanField(verbose_name="是否有效", default=True)
    batch_no = models.CharField(max_length=200, verbose_name="同步批号", default="")

    class Meta:
        db_table = "circle_ding_department"
        verbose_name = "钉钉部门表"
        verbose_name_plural = verbose_name

    @classmethod
    def get_root_departments(cls):
        dep_list = []
        excludes = ['复星', '复星津美', 'OneFosun会务系统']
        queryset = CircleDepartmentModel.objects \
            .filter(parent_dep_id='root', is_alive=True, is_del=False) \
            .order_by('display_order').all()

        for dep_obj in queryset:
            dep_name = dep_obj.dep_name
            if dep_name in excludes:
                continue

            dep_list.append(dict(
                dep_name=dep_name, dep_id=dep_obj.dep_id,
                dep_en_name=dep_obj.dep_en_name, name_path=dep_obj.name_path
            ))

        return dep_list

    @classmethod
    def get_department_tree(cls, root_id=None, on_cascade=False):
        """ 部门树

        :param root_id:     string, 部门id
        :param on_cascade:  bool, 前端 cascader 组件, 默认展示二级（部门树级联组件）
        :return: dict
        """
        fields = ["dep_name", "dep_id", "parent_dep_id"]
        queryset = cls.objects.filter(is_alive=1).values(*fields).order_by("parent_dep_id")

        department_list = [
            dict(
                label=depart["dep_name"], value=depart["dep_id"],
                parent_dep_id=depart["parent_dep_id"],
                # display_order=depart["display_order"],
            )
            for depart in queryset
        ]
        department_dict = {item["value"]: item for item in department_list}

        for parent_dep_id, iterator in groupby(department_list, key=itemgetter("parent_dep_id")):
            if parent_dep_id in department_dict:
                sub_department_list = list(iterator)
                # sub_department_list.sort(key=itemgetter("display_order"))

                children = department_dict[parent_dep_id].setdefault("children", [])
                children.extend(sub_department_list)

        target_department = department_dict.get(root_id, {}) if root_id else department_dict
        target_q = deque([target_department])

        # 前端 element-ui cascader 组件精简数据
        while on_cascade and target_q:
            department_node = target_q.popleft()
            depth = department_node.pop("depth", 0)

            if depth >= 2:
                department_node.pop("children", None)
                continue

            for child in department_node.get("children", []):
                child["depth"] = depth + 1
                target_q.append(child)

        if on_cascade:
            default_order_deps = [item['dep_name'] for item in cls.get_root_departments()]

            def sort_dep(dep_item):
                # 部门展示顺序
                for i, label in enumerate(default_order_deps):
                    if label in dep_item.get("label", ""):
                        return i

                return len(default_order_deps)

            dep_children = target_department.get("children", [])
            dep_children.sort(key=sort_dep)
            target_department.update(children=dep_children[:len(default_order_deps)])

        return target_department


class CircleUser2DepartmentModel(BaseAbstractModel):
    """ 人员与部门关系 """
    usr_id = models.CharField(verbose_name="钉钉人员id", default="", max_length=200)
    dep_id = models.CharField(max_length=200, verbose_name="钉钉部门唯一id", default="")
    first_dep = models.CharField(max_length=200, verbose_name="first_dep", default="")
    display_order = models.IntegerField(verbose_name="部门在钉钉展示顺序", default=0)
    is_alive = models.BooleanField(verbose_name="是否有效", default=True)
    batch_no = models.CharField(max_length=200, verbose_name="batch_no", default="")

    class Meta:
        db_table = "circle_user_department_relation"
        verbose_name = "钉钉人员与部门关系表"
        verbose_name_plural = verbose_name


class CircleUsersVirtualRoleModel(BaseAbstractModel):
    """ 用户角色(角色：虚拟用户名，跟随主用户)
    不同角色用户下"我的" 怎么控制，消息、点赞，评论如何控制
    """

    ROLE_TYPE = [
        (0, "主用户角色"),
        (1, "虚拟用户角色")
    ]

    user_id = models.IntegerField(verbose_name="用户id", db_index=True, default=0)
    role_name = models.CharField(verbose_name="角色名称(eg: 小甜甜)", max_length=200, default="")
    role_avatar = models.CharField(verbose_name="角色头像", max_length=200, default="")
    role_type = models.SmallIntegerField(verbose_name="角色状态", choices=ROLE_TYPE, default=0)
    nick_name = models.CharField(verbose_name='昵称', max_length=100, default='')
    sign_name = models.CharField(verbose_name='个性签名', max_length=500, default="")

    class Meta:
        db_table = "circle_virtual_role"


class CircleGroupModel(BaseAbstractModel):
    """ 用户组 """
    name = models.CharField(verbose_name="用户组名称", max_length=200, unique=True, default="")

    class Meta:
        db_table = "circle_group"


class CircleGroupUsersModel(BaseAbstractModel):
    """ 用户与组的关系(组目前不涉及权限，只与人关联) """
    group_id = models.IntegerField(verbose_name="用户组id", db_index=True, default=0)
    user_id = models.IntegerField(verbose_name="用户id", db_index=True, default=0)

    class Meta:
        db_table = "circle_group_users"


class CircleResourcePermissionModel(BaseAbstractModel):
    """ 用户权限 """
    PERM_RESOURCE = [
        (0, "TabBar 资源(首页、发现、开炼、我的 等)"),
        (1, "模块资源(日历、动态、吐槽......)"),
        (2, "TabBar 拥有的模块资源(首页: 日历、动态、吐槽...)"),
        (3, "模块拥有的资源范围(动态： 列表、详情......)"),
        (4, "模块拥有的权限范围(动态： 创建、评论、点赞....)"),
    ]

    name = models.CharField(verbose_name="资源或权限名称", max_length=200, default="")
    resource_path = models.CharField(verbose_name="资源或权限路径", max_length=500, default="")
    module_name = models.CharField(verbose_name="所属模块", max_length=100, default="")
    component = models.CharField(verbose_name="所属组件", max_length=100, default="")
    param_name = models.CharField(verbose_name="参数名", max_length=100, default="")
    perm_type = models.SmallIntegerField(verbose_name="类型", choices=PERM_RESOURCE, default=0)
    desc = models.CharField(verbose_name="资源或权限描述", max_length=500, default="")

    class Meta:
        db_table = "circle_resource_permission"

    @classmethod
    def get_queryset_by_ids(cls, resource_ids, perm_type=None):
        """ 用户资源数据集
        :param resource_ids: list, 资源列表
        :param perm_type: int, 0-资源 1-权限 None-全部
        """
        resource_ids = resource_ids or []
        fields = cls.fields()

        query_kwargs = dict(id__in=resource_ids, is_del=False)
        perm_type is not None and query_kwargs.update(perm_type=perm_type)
        queryset = cls.objects.filter(**query_kwargs).values(*fields).order_by("perm_type")

        return queryset


class CircleUsersResourcePermissionModel(BaseAbstractModel):
    """ 用户、资源权限、操作权限的关系
    (1): 一个资源模块下含有多个操作权限
    (2): permission_ids 一个资源模块具有的操作权限范围
    (2): belong_type 用户拥有的资源权限类型
        0: 所有用户共有基础的资源与操作权限
        1：用户拥有的资源与操作权限
        2：用户覆盖基础的资源与操作权限
    """
    RESOURCE_BELONG_TYPE = [
        (0, "基础资源与操作权限"),
        (1, "用户自己拥有的资源与操作权限"),
        (2, "用户覆盖基础资源与操作权限")
    ]

    user_id = models.IntegerField(verbose_name="用户id", db_index=True, default=0)
    resource_perm_id = models.IntegerField(verbose_name="资源或权限权限ID", db_index=True, default=-1)
    is_include = models.BooleanField(verbose_name="是否包含resource_id的资源", default=True)
    belong_type = models.SmallIntegerField(verbose_name="用户拥有的资源和权限类型", choices=RESOURCE_BELONG_TYPE, default=0)

    class Meta:
        db_table = "circle_users_perm_resource_mapper"

    @classmethod
    def get_queryset_by_user_id(cls, user_id):
        """ 用户对应的资源、权限映射关系 """
        query_kwargs = dict(user_id__in=[0, user_id], is_del=False)
        mapper_fields = cls.fields()

        data = []
        existed_resource_perm_ids = set()
        queryset = cls.objects.filter(**query_kwargs).values(*mapper_fields).order_by("-id")
        logger.info("get_resource_list SQL: {}".format(queryset.query))

        for item in queryset:
            resource_perm_id = item["resource_perm_id"]

            if resource_perm_id not in existed_resource_perm_ids:
                data.append(item)
                existed_resource_perm_ids.add(resource_perm_id)

        return data


class BbsUserModel(models.Model):
    """
    用户信息表
    """
    GENDER = [
        (0, '男'),
        (1, '女'),
        (3, '保密')
    ]
    USERTYPE = [
        (0, "master"),
        (1, "role")
    ]
    STATUS = [
        (0, "workpre"),
        (1, "working"),
        (2, "workout"),
    ]
    gender = models.SmallIntegerField(choices=GENDER, default=3, verbose_name='性别')
    birthday = models.DateField(null=True, blank=True)
    phoneNumber = models.CharField(max_length=20, default="", verbose_name="手机号码")
    countryCode = models.CharField(max_length=10, default='+86', verbose_name='国别')
    email = models.EmailField(max_length=500, verbose_name="邮箱", default="example@126.com")
    avatar = models.CharField(default="", max_length=1000, null=True, blank=True)
    isJob = models.BooleanField(default=True, verbose_name='在职状态')
    company = models.CharField(max_length=200, verbose_name='公司名', default='')
    departmentCh = models.CharField(max_length=100, verbose_name='中文部门', default='')
    departmentEn = models.CharField(max_length=100, verbose_name='英文部门', default='')
    positionCh = models.CharField(max_length=200, null=True, blank=True, verbose_name='中文职位')
    positionEn = models.CharField(max_length=200, null=True, blank=True, verbose_name='英文文职位')
    # 回帖数量
    replyCount = models.IntegerField(default=0, verbose_name='回帖数量')
    signName = models.CharField(max_length=255, verbose_name='个性签名', null=True)
    nickName = models.CharField(max_length=12, verbose_name='昵称', default='')
    source = models.CharField(max_length=12, verbose_name="用户来源", default="SYS")
    isForbidden = models.BooleanField(default=False, verbose_name="禁止发表言论")
    isAgree = models.BooleanField(default=False, verbose_name="同意用户公告")
    fullname = models.CharField(max_length=100, default="", verbose_name="全名")
    newCircleCount = models.IntegerField(default=0, verbose_name="新增星圈信息")
    newTaleCount = models.IntegerField(default=0, verbose_name="新增召集令信息")
    userType = models.SmallIntegerField(default=0, verbose_name="用户类型")
    isAllowAddRole = models.BooleanField(default=False, verbose_name="是否允许新增用户角色")
    isCheckoutRole = models.BooleanField(default=False, verbose_name="是否允许切换用户角色")
    userStatus = models.SmallIntegerField(default=1, choices=STATUS, verbose_name="用户状态")
    real_avatar = models.CharField(max_length=500, verbose_name='真实头像', default="")
    jobCode = models.CharField(max_length=50, default="")
    isAllowAddSchedule = models.BooleanField(default=False)
    is_admin_user = models.BooleanField(default=False, verbose_name="是否是后台管理人员")

    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    is_superuser = models.BooleanField()

    class Meta:
        verbose_name = "用户信息"
        db_table = "users_userinfo"
        verbose_name_plural = verbose_name
        ordering = ['id']

        # managed = False: 生成 migrations 迁移文件，但不会在数据库中创建表
        managed = False

    def __str__(self):
        return self.fullname

    @classmethod
    def get_bbs_user_queryset(cls):
        """ 获取 bbs 老库中用户信息 """
        queryset = BbsUserModel.objects.using("bbs_user").filter(
            ~Q(jobCode=""), ~Q(jobCode=None),
            ~Q(phoneNumber=""), ~Q(phoneNumber=None)
        )

        return queryset


class OdooDingUserModel(models.Model):
    job_code = models.CharField(max_length=200, verbose_name="钉钉userid")
    state_code_1 = models.CharField(max_length=20, verbose_name="区号")
    mobile_1 = models.CharField(max_length=20, verbose_name="手机号")
    usr_id = models.CharField(verbose_name="钉钉人员id", max_length=200)
    work_place = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    dept_desc = models.CharField(max_length=1000)
    title_desc = models.CharField(max_length=1000)
    fullname = models.CharField(max_length=200)
    avatar = models.CharField(max_length=500)
    user_ucode = models.CharField(max_length=200)
    en_name = models.CharField(max_length=200)
    en_workplace = models.CharField(max_length=200)
    en_title_desc = models.CharField(max_length=1000)
    rec_revise_time = models.DateTimeField()
    rec_create_time = models.DateTimeField()
    tel = models.CharField(max_length=200)
    alive_flag = models.CharField(max_length=200)
    write_uid = models.IntegerField()
    write_date = models.DateTimeField()
    batch_no = models.CharField(max_length=20)

    class Meta:
        verbose_name = "钉钉人员表(Odoo)"
        db_table = "intf_uuc_user"
        ordering = ['id']

        # managed = False: 生成 migrations 迁移文件，但不会在数据库中创建表
        managed = False


class OdooDingUser2DepartmentModel(models.Model):
    usr_id = models.CharField(verbose_name="钉钉人员id", max_length=200)
    dep_id = models.CharField(verbose_name="钉钉部门id", max_length=200)
    disporder = models.CharField(max_length=20)
    alive_flag = models.CharField(max_length=20)
    write_uid = models.IntegerField()
    write_date = models.DateTimeField()
    batch_no = models.CharField(max_length=200)
    firstdep = models.CharField(max_length=200)

    class Meta:
        verbose_name = "钉钉人员与部门表(Odoo)"
        db_table = "intf_uuc_user_job"
        ordering = ['id']

        # managed = False: 生成 migrations 迁移文件，但不会在数据库中创建表
        managed = False


class OdooDingDepartmentModel(models.Model):
    """ 钉钉部门 """
    dep_id = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    parent_dep_id = models.CharField(max_length=200)
    dept_ucode = models.CharField(max_length=200)
    en_name = models.CharField(max_length=200)
    disporder = models.CharField(max_length=200)
    name_path = models.CharField(max_length=200)
    alive_flag = models.CharField(max_length=200)
    write_uid = models.IntegerField()
    write_date = models.DateTimeField()
    batch_no = models.CharField(max_length=200)

    class Meta:
        verbose_name = "钉钉部门表(Odoo)"
        db_table = "intf_uuc_department"
        ordering = ['id']

        # managed = False: 生成 migrations 迁移文件，但不会在数据库中创建表
        managed = False

    def __str__(self):
        return "%s:%s" % (self.name, self.dep_id)


class OtpTotpUserModel(BaseAbstractModel):
    mobile = models.CharField(max_length=20, default="", unique=True, verbose_name="手机号码", blank=True)
    url_2fa = models.CharField(verbose_name="双因子二维码url", max_length=500, default="", blank=True)

    class Meta:
        db_table = "otp_totp_users"

    @classmethod
    def get_or_create_2fa(cls, mobile):
        User = get_user_model()
        default_qr_factory = 'qrcode.image.pil.PilImage'
        otp_2fa_obj = cls.objects.filter(mobile=mobile, is_del=False).first()

        if otp_2fa_obj is None:
            user = User.objects.filter(phone_number=mobile, is_del=False).first()
            if user is None:
                raise ValueError("用户<%s>不存在，禁止使用星圈管理后台" % mobile)

            totp_device_obj = TOTPDevice.objects.filter(user_id=user.id).first()
            if totp_device_obj is None:
                totp_device_obj = TOTPDevice.objects.create(user_id=user.id, name=mobile)
            otpauth_url = totp_device_obj.config_url

            # Make and return QR code
            image_factory = import_string(default_qr_factory)
            img = qrcode.make(otpauth_url, image_factory=image_factory)

            filename = "2fa_%s.png" % mobile
            file_path = os.path.join(settings.MEDIA_ROOT, filename)
            img.save(file_path)

            # Upload Aliyun OSS
            # result = AliOssFileUploader().complete_upload(filename=filename)
            # url_2fa = result["url"]

            url_2fa = reverse("static_serve") + "?filename=" + filename
            otp_2fa_obj = cls.objects.create(mobile=mobile, url_2fa=url_2fa)

        return otp_2fa_obj.to_dict()


