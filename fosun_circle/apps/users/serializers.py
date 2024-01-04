from rest_framework import serializers

from . import models


class SimpleUsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CircleUsersModel
        fields = ['id', 'username', 'ding_job_code', 'username', 'department_chz', 'position_chz', 'phone_number']


class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CircleUsersModel
        fields = models.CircleUsersModel.fields()


class ListFuzzyRetrieveUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CircleUsersModel
        fields = ["id", "username", "phone_number"]


