import typing
from django.db import connections
from django.contrib.auth import get_user_model
from rest_framework import serializers

from users.models import CircleDepartmentModel
from .models import EsgEntryUserModel, ESGEntryDepartmentModel, ESGAdminModel, ESGTaskActionModel

UserModel = get_user_model()


class DepartmentSerializer(serializers.ModelSerializer):
    parent_dep_name = serializers.SerializerMethodField(help_text="上级部门名称")

    class Meta:
        model = CircleDepartmentModel
        fields = ['parent_dep_name', 'dep_name', 'dep_id', 'parent_dep_id']

    def get_parent_dep_name(self, obj):
        local_cache = getattr(self, 'local_cache', None)

        if local_cache is None:
            instance_list = self.instance
            dep_ids = [obj.parent_dep_id for obj in instance_list]
            queryset = self.Meta.model.objects.filter(dep_id__in=dep_ids).all()

            local_cache = {obj.dep_id: obj.dep_name for obj in queryset}
            setattr(self, 'local_cache', local_cache)

        return local_cache.get(obj.parent_dep_id)


class ESGEntryDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ESGEntryDepartmentModel
        fields = model.fields()


class ESGUserAdminSerializer(serializers.ModelSerializer):
    # user 外键的反序列化
    user = serializers.PrimaryKeyRelatedField(many=False, queryset=UserModel.objects.all())
    username = serializers.CharField(source='user.username', read_only=True, max_length=200, help_text="ESG用户名")
    permission_type_cn = serializers.SerializerMethodField(help_text="权限")

    class Meta:
        model = ESGAdminModel
        fields = model.fields() + ['user', 'username', 'permission_type_cn']

    def get_permission_type_cn(self, obj):
        mapping = dict(self.Meta.model.PERMISSION_TYPE_CHOICES)
        return mapping.get(obj.permission_type)


class ESGTaskActionSerializer(serializers.ModelSerializer):
    tag_name = serializers.SerializerMethodField()

    class Meta:
        model = ESGTaskActionModel
        fields = model.fields() + ['tag_name']

    def get_tag_name(self, obj):
        local_cache = getattr(self, 'local_cache', {})

        if not local_cache:
            instance_list = self.instance if isinstance(self.instance, typing.Iterable) else [self.instance]
            tag_ids = [str(obj.tag_id) for obj in instance_list]

            cursor = connections['bbs_user'].cursor()
            sql = """SELECT id, title FROM "starCircle_tag" WHERE tag_desc='ESG' AND id IN (%s)"""

            if tag_ids:
                cursor.execute(sql % (", ".join(tag_ids)))
                local_cache = {item[0]: item[1] for item in cursor.fetchall()}

            setattr(self, 'local_cache', local_cache)

        if isinstance(obj, self.Meta.model):
            return local_cache.get(obj.tag_id)

