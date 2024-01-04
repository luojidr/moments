from rest_framework import serializers

from . import models
from users.models import CircleUsersModel


class DissFeedbackSerializer(serializers.ModelSerializer):
    cn_state = serializers.SerializerMethodField(default="", help_text="处理状态")

    class Meta:
        model = models.DissFeedbackModel
        fields = ["diss_id", "user_id", "mobile", "state", "remark", "cn_state"]
        read_only_fields = ("cn_state",)

    def get_cn_state(self, obj):
        state = obj.state
        mapper = dict(models.DissFeedbackModel.STATE)
        return mapper[state]


class CircleTagSerializer(serializers.Serializer):
    tag_id = serializers.IntegerField(read_only=True, help_text="话题标签ID")
    tag_name = serializers.CharField(read_only=True, min_length=0, max_length=100, help_text="话题标签名称")

