from rest_framework import serializers
from django.template.defaultfilters import filesizeformat

from .models import AliStaticUploadModel


class AliSmsSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=11, required=True, help_text="手机号码")
    country_code = serializers.CharField(max_length=11, required=True, help_text="所属地区")


class AliVodSertalizer(serializers.Serializer):
    title = serializers.CharField(max_length=1024, required=True, help_text="标题")
    filename = serializers.CharField(max_length=1024, required=True, help_text="上传的文件名")


class StaticUploadSerializer(serializers.ModelSerializer):
    file_size = serializers.SerializerMethodField(read_only=True, help_text='File Size Format')

    class Meta:
        model = AliStaticUploadModel
        fields = model.fields() + ['creator']

    def get_file_size(self, obj):
        return filesizeformat(obj.file_size)
