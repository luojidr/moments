from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from users.models import CircleUsersModel
from .models import ActivityModel, ParticipantModel, AwardModel


class LotteryActivitySerializer(serializers.ModelSerializer):
    deadline = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, help_text="活动截止时间")

    class Meta:
        model = ActivityModel
        fields = model.fields()
        read_only_fields = ['participant_num', 'awarded_num']

    def validate(self, attrs):
        is_confirmed = attrs.get('is_confirmed')

        if not is_confirmed:
            if not attrs.get('name'):
                raise ValidationError('抽奖-活动名称不能为空')

            if attrs.get('participant_mode') == 'CIRCLE':
                if not attrs.get('tag_id'):
                    raise ValidationError('参与模式为<星圈话题>时，<话题标签>不能为空')

                if attrs.get('tag_id') and \
                        not attrs.get('is_posted') and \
                        not attrs.get('is_commented') and \
                        not attrs.get('is_liked'):
                    raise ValidationError('参与模式为<星圈话题>时, 发帖、评论、点赞不能同时为空')

            if not attrs.get('deadline'):
                raise ValidationError('抽奖-截止时间不能为空')

        return attrs


class ListAwardSerializer(serializers.ListSerializer):
    """ self.get_serializer(data=request.data, many=True) """

    def validate(self, attrs):
        if len(attrs) == 0:
            raise ValidationError('奖品不能为空')

        activity_id = attrs[0]['activity_id']
        if not all([activity_id == item['activity_id'] for item in attrs]):
            raise ValidationError('奖品必须属于同一抽奖活动')

        # 把之前创建的奖品删除
        self.child.Meta.model.objects.filter(activity_id=activity_id).delete()

        # 如果之前抽过奖，需将之前抽奖人员清空
        ParticipantModel.objects.filter(activity_id=activity_id, is_del=False).update(is_awarded=False, award_id=None)
        return attrs


class AwardSerializer(serializers.ModelSerializer):
    activity_id = serializers.IntegerField(write_only=True, help_text='活动id')

    class Meta:
        model = AwardModel
        fields = model.fields()
        list_serializer_class = ListAwardSerializer

    def create(self, validated_data):
        return self.Meta.model.objects.create(**validated_data)


class ParticipantSerializer(serializers.ModelSerializer):
    award = AwardSerializer(read_only=True)

    class Meta:
        model = ParticipantModel
        fields = model.fields() + ['award']

    def create(self, validated_data):
        object_list = []
        new_mobiles = []

        activity_id = self.initial_data['activity_id']
        mobiles = self.initial_data.get('mobiles') or []

        fields = ("phone_number", "id", "username")
        user_queryset = CircleUsersModel.objects.filter(phone_number__in=mobiles, is_del=False).values(*fields)

        query = dict(activity_id=activity_id, is_del=False)
        existed_mobiles = self.Meta.model.objects.filter(**query).values_list('mobile', flat=True)

        for user in user_queryset:
            mobile = user['phone_number']
            new_mobiles.append(mobile)
            kwargs = dict(
                user_id=user['id'], mobile=mobile, username=user['username'],
                activity_id=activity_id, is_awarded=False, is_pushed=False, is_recall=False,
            )

            if mobile not in existed_mobiles:
                object_list.append(self.Meta.model(**kwargs))

        self.Meta.model.objects.bulk_create(object_list)  # 新增

        remove_mobiles = list(set(existed_mobiles) - set(new_mobiles))
        self.Meta.model.objects.filter(mobile__in=remove_mobiles).update(is_del=True)

        ActivityModel.objects.filter(id=activity_id, is_del=False).update(participant_num=len(user_queryset))
        return object_list


