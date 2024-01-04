from collections import OrderedDict
from itertools import groupby
from operator import attrgetter

from django.db import models

from fosun_circle.core.db.base import BaseAbstractModel
from users.models import CircleUsersModel


class SelectionModel(BaseAbstractModel):
    TYPE_CHOICES = [
        (1, "单选题"),
        (2, "多选题"),
        (3, "单项文本题"),
        (4, "多项文本题"),
        (5, "打分题"),
        (6, "矩阵题"),
    ]

    type = models.SmallIntegerField(choices=TYPE_CHOICES, verbose_name="题型", default=0, blank=True)
    widget = models.CharField(max_length=200, verbose_name="题型组件", default="", blank=True)
    desc = models.CharField(max_length=200, verbose_name="题型描述", default="", blank=True)

    class Meta:
        db_table = "circle_survey_selection"
        verbose_name = "题目类型表"
        verbose_name_plural = verbose_name
        ordering = ['id']


class QuestionnaireModel(BaseAbstractModel):
    SOURCE_CHOICES = [
        ('my', '自建问卷'),
        ('ihcm', 'Odoo问卷'),
    ]

    STATUS_CHOICES = [
        ('draft', "草稿"),
        ('open', "进行中"),
        ('close', "关闭"),
    ]

    # user: 问卷的创建者或同步者
    user = models.ForeignKey(to=CircleUsersModel, verbose_name="用户ID", on_delete=models.CASCADE, blank=True)
    published_time = models.DateTimeField(verbose_name="发布时间", default=None, null=True, blank=True)
    save_time = models.DateTimeField(verbose_name="保存时间", default=None, null=True, blank=True)
    title = models.CharField(max_length=200, verbose_name="标题", default="", blank=True)
    desc = models.CharField(max_length=1000, verbose_name="说明", default="", blank=True)
    img_url = models.CharField(max_length=500, verbose_name="图片", default="", blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, verbose_name="状态", default=0, blank=True)
    source = models.CharField(max_length=10, verbose_name="来源", choices=SOURCE_CHOICES, default="my", blank=True)
    ref_id = models.IntegerField('非my问卷ID', default=None, null=True, blank=True)
    ref_md5 = models.CharField('问卷MD5', max_length=100, default='', blank=True)
    is_anonymous = models.BooleanField(verbose_name="是否匿名", default=True, blank=True)

    class Meta:
        db_table = "circle_survey_questionnaire"
        verbose_name = "问卷表"
        verbose_name_plural = verbose_name
        ordering = ['id']

    @classmethod
    def get_questionnaire_list(cls, status=None):
        questionnaire_list = []
        queryset = cls.objects.filter(is_del=False).all()

        if status:
            queryset = queryset.filter(status=status)

        for questionnaire_obj in queryset:
            questionnaire_list.append(dict(
                questionnaire_id=questionnaire_obj.id,
                title=questionnaire_obj.title,
                desc=questionnaire_obj.desc, status=questionnaire_obj.status
            ))

        return questionnaire_list

    @classmethod
    def get_questionnaire_detail(cls, questionnaire_id):
        q_id = questionnaire_id or 0
        questionnaire_obj = cls.objects.filter(id=q_id, is_del=False).first()

        if not q_id:
            return {}

        question_order_dict = OrderedDict()
        questionnaire_data = dict(
            questionnaire_id=q_id, title=questionnaire_obj.title,
            desc=questionnaire_obj.desc, status=questionnaire_obj.status
        )

        option_queryset = OptionsModel.objects \
            .filter(question__questionnaire_id=q_id, is_del=False, question__is_del=False) \
            .prefetch_related("question", "question__topic") \
            .all().order_by("question__order", "order")

        for option_obj in option_queryset:
            question_obj = option_obj.question
            question_id = question_obj.id

            if question_id not in question_order_dict:
                question_data = dict(
                    question_id=question_id, is_required=question_obj.is_required,
                    topic_id=question_obj.topic.id, title=question_obj.title,
                    desc=question_obj.desc, img_url=question_obj.img_url, answer="",
                )
                question_order_dict[question_id] = question_data

            question_order_dict[question_id].setdefault("options", []).append(
                dict(
                    option_id=option_obj.id, title=option_obj.title, order=option_obj.order,
                    answer="", min_value=option_obj.min_value, max_value=option_obj.max_value
                )
            )

        questionnaire_data["questions"] = [question for _, question in question_order_dict.items()]
        return questionnaire_data


class QuestionModel(BaseAbstractModel):
    questionnaire = models.ForeignKey(to=QuestionnaireModel, verbose_name="问卷id", on_delete=models.CASCADE, blank=True)
    title = models.CharField(max_length=200, verbose_name="题目标题", default="", blank=True)
    desc = models.CharField(max_length=200, verbose_name="题目说明", default="", blank=True)
    topic = models.ForeignKey(to=SelectionModel, verbose_name="题目类型id", on_delete=models.CASCADE, blank=True)
    img_url = models.CharField(max_length=500, verbose_name="题目图片补充", default="", blank=True)
    order = models.SmallIntegerField(verbose_name="题目顺序", default=0, blank=True)
    rows = models.SmallIntegerField(verbose_name='行数', default=0, blank=True)  # 如果为填空题 此字段为文本输入框的行数
    is_required = models.BooleanField(verbose_name='是否必填', default=True, blank=True)

    class Meta:
        db_table = "circle_survey_question"
        verbose_name = "问题表"
        verbose_name_plural = verbose_name
        ordering = ['id']


class OptionsModel(BaseAbstractModel):
    question = models.ForeignKey(to=QuestionModel, verbose_name='关联题目id', on_delete=models.CASCADE, blank=True)
    title = models.CharField(max_length=100, verbose_name='选项名', default="", blank=True)
    order = models.SmallIntegerField(verbose_name="选项顺序", default=0, blank=True)
    min_value = models.CharField(max_length=100, verbose_name="最小值(打分题)", default="", blank=True)
    max_value = models.CharField(max_length=100, verbose_name="最大值(打分题)", default="", blank=True)

    class Meta:
        db_table = "circle_survey_options"
        verbose_name = "问卷中问题选项表"
        verbose_name_plural = verbose_name
        ordering = ['id']


class SubmissionModel(BaseAbstractModel):
    STATUS_CHOICES = [
        (0, "草稿"),      # 系统自动保存的状态
        (1, "暂存"),      # 问卷用户暂存状态
        (2, "提交"),      # 问卷用户提交状态
    ]

    user = models.ForeignKey(to=CircleUsersModel, verbose_name="问卷提交者", on_delete=models.CASCADE, blank=True)
    questionnaire = models.ForeignKey(to=QuestionnaireModel, verbose_name="问卷id", on_delete=models.CASCADE, blank=True)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, verbose_name="提交状态", default=0, blank=True)
    submit_time = models.DateTimeField(verbose_name="问卷提交时间", null=True, default=True, blank=True)

    class Meta:
        db_table = "circle_survey_submission"
        verbose_name = "问卷用户提交表"
        verbose_name_plural = verbose_name
        ordering = ['id']


class AnswerModel(BaseAbstractModel):
    submission = models.ForeignKey(to=SubmissionModel, verbose_name='提交id', on_delete=models.CASCADE, blank=True)
    questionnaire = models.ForeignKey(to=QuestionnaireModel, verbose_name="问卷id", on_delete=models.CASCADE, blank=True)
    question = models.ForeignKey(to=QuestionModel, verbose_name='问题id', on_delete=models.CASCADE, blank=True)
    answer = models.CharField(max_length=500, verbose_name='问题答案', default="", blank=True)

    class Meta:
        db_table = "circle_survey_answer"
        verbose_name = "问卷用户提交表"
        verbose_name_plural = verbose_name
        ordering = ['id']

