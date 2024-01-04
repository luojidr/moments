from rest_framework import serializers
from .models import QuestionnaireModel


class QuestionnaireSerializer(serializers.ModelSerializer):
    save_time = serializers.DateTimeField("%Y-%m-%d %H:%M:%S", required=False,  help_text='保存时间')
    published_time = serializers.DateTimeField("%Y-%m-%d %H:%M:%S", required=False, help_text='发布时间')

    class Meta:
        model = QuestionnaireModel
        fields = QuestionnaireModel.fields() + ['is_del']
