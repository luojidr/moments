from django.db import models
from django.contrib.auth import get_user_model

from fosun_circle.core.db.base import BaseAbstractModel

User = get_user_model()


class AwardModel(BaseAbstractModel):
    """ 奖品 """
    Award_CHOICES = [
        (1, '一等奖'),
        (2, '二等奖'),
        (3, '三等奖'),
    ]

    name = models.CharField('奖品名称', max_length=200, default='', null=True, blank=True)
    desc = models.CharField('奖品描述', max_length=500, default='', null=True, blank=True)
    num = models.IntegerField('数量', default=0, null=True, blank=True)
    img_url = models.URLField('奖品链接', max_length=500, default='', null=True, blank=True)
    award_type = models.SmallIntegerField('奖品类型', default=1, null=True, blank=True)
    activity = models.ForeignKey('ActivityModel', on_delete=models.SET_NULL, default=None, null=True, blank=True)

    class Meta:
        db_table = 'circle_lottery_award'
        ordering = ['-id']


class ActivityModel(BaseAbstractModel):
    """ 抽奖活动 """
    STATE_CHOICES = [
        ('SET_CONDITION', '设置参与条件'),
        ('CONFIRM_PARTICIPANT', '确认参与人员名单'),
        ('SET_AWARD', '设置奖品'),
        ('LOTTERY', '抽奖'),  # 确认抽奖结果后，已填抽奖信息不可修改
        ('PUSH_MESSAGE', '推送中奖消息'),
    ]
    PARTICIPANT_MODES = [
        ('CIRCLE', '星圈话题参与'),
        ('EXCEL', 'Excel导入'),
    ]

    name = models.CharField('抽奖活动名称', max_length=200, default='', null=True, blank=True)
    participant_num = models.IntegerField('参与抽奖人数', default=0, null=True, blank=True)
    awarded_num = models.IntegerField('已中奖人数', default=0, null=True, blank=True)
    is_confirmed = models.BooleanField('已确认抽奖', default=False, null=True, blank=True)
    is_pushed = models.BooleanField('中奖消息已推送', default=False, null=True, blank=True)

    # 抽奖相关配置
    state = models.CharField('抽奖节点状态', choices=STATE_CHOICES, max_length=50,
                             default='SET_CONDITION', null=True, blank=True)
    participant_mode = models.CharField('参与模式', choices=PARTICIPANT_MODES, max_length=20,
                                        default='CIRCLE', null=True, blank=True)
    tag_id = models.IntegerField('话题标签', default=0, null=True, blank=True)
    is_posted = models.BooleanField('已发帖', default=False, null=True, blank=True)
    is_commented = models.BooleanField('已评论', default=False, null=True, blank=True)
    is_liked = models.BooleanField('已点赞', default=False, null=True, blank=True)
    deadline = models.DateTimeField('截止时间', default=None, null=True, blank=True)

    class Meta:
        db_table = 'circle_lottery_activity'
        ordering = ['-id']

    def get_node_state(self, current_state, prev=False, next=True):
        state = current_state.upper()
        state_list = [choice[0] for choice in self.STATE_CHOICES]
        index = state_list.index(state)

        if prev:
            if index - 1 < 0:
                raise ValueError('Previous state doex not exist for current state<%s>.' % state)
            return state_list[index - 1]

        if next:
            if index + 1 >= len(state_list):
                raise ValueError('Next state doex not exist for current state<%s>.' % state)
            return state_list[index + 1]

        raise ValueError("State not allowed.")


class ParticipantModel(BaseAbstractModel):
    """ 奖品参与人员 """
    activity = models.ForeignKey(ActivityModel, on_delete=models.SET_NULL,
                                 related_name='lottery_participants', default=None, null=True, blank=True)
    award = models.ForeignKey(AwardModel, on_delete=models.SET_NULL,
                              related_name='lottery_winners', default=None, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, default=None, null=True, blank=True)
    mobile = models.CharField('Mobile', max_length=20, default='', null=True, blank=True)
    username = models.CharField('Username', max_length=100, default='', null=True, blank=True)
    is_awarded = models.BooleanField('已获奖', default=False, null=True, blank=True)
    is_pushed = models.BooleanField('中奖消息已推送', default=False, null=True, blank=True)
    is_recall = models.BooleanField('中奖消息已撤回', default=False, null=True, blank=True)
    push_log_id = models.IntegerField('推送记录ID', default=None, null=True, blank=True)

    class Meta:
        db_table = 'circle_lottery_participant'
        ordering = ['-id']

