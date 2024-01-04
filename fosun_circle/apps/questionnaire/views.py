import os.path
import pathlib
import uuid
import time
from datetime import date, datetime
from itertools import groupby
from operator import itemgetter

from django.conf import settings
from django.views import View
from django.views.static import serve
from django.db.models import Q
from django.db import transaction, connections
from django.http.response import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from django_redis import get_redis_connection

from config.conf.dingtalk import DingTalkConfig
from fosun_circle.libs.utils.snow_flake import Snowflake
from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.core.views import ListVueView, SingleVueView
from ding_talk.models import DingMsgPushLogModel, DingMessageModel
from fosun_circle.apps.questionnaire.tasks.task_sync_survey import sync_survey
from users.models import CircleUsersModel
from users.models import CircleDepartmentModel
from . import models
from .service import SurveyVoteService
from .serializers import QuestionnaireSerializer


class CreateQuestionnaireSurveyView(SingleVueView):
    template_name = "questionnaire/survey_manage.html"
    model = models.SelectionModel

    def get_queryset(self):
        user = self.request.user
        redis_conn = get_redis_connection()
        redis_key = "questionnaireId:%s" % user.mobile
        questionnaire_id = int(redis_conn.get(redis_key) or 0)

        topic_queryset = self.model.objects.filter(is_del=False).all()
        topic_list = [obj.to_dict() for obj in topic_queryset]

        questionnaire_data = models.QuestionnaireModel.get_questionnaire_detail(questionnaire_id)
        return dict(topic_list=topic_list, questionnaire=questionnaire_data)


class ListQuestionnaireSurveyView(ListVueView):
    template_name = "questionnaire/survey_list.html"
    model = models.QuestionnaireModel

    def get_pagination_list(self):
        login_user = self.request.user
        query_kwargs = dict(is_del=False)
        queryset = self.model.objects.select_related("user").filter(**query_kwargs).all()
        data = dict(list=[], total_count=queryset.count())

        object_list = queryset[self.page_offset:self.page_limit + self.page_offset]
        serializer = QuestionnaireSerializer(object_list, many=True)
        data["list"] = serializer.data

        return data


class DingPushQuestionnaireSurveyView(SingleVueView):
    template_name = "questionnaire/survey_ding_push.html"
    model = models.QuestionnaireModel

    def get_queryset(self):
        questionnaire_list = self.model.get_questionnaire_list(status=2)

        root_id = DingTalkConfig.DING_FOSUN_GROUP_HEAD_ROOT_ID
        department_tree = CircleDepartmentModel.get_department_tree(root_id)
        return dict(
            questionnaire_list=questionnaire_list,
            department_list=[department_tree]
        )


@method_decorator(csrf_exempt, name="dispatch")
class UploadQuestionImageApi(View):
    """ 接口长传图片必须使用继承 View, 并且 @method_decorator(csrf_exempt, name="dispatch") """

    def post(self, request, *args, **kwargs):
        """ 上传题目图片 """
        media_url = settings.MEDIA_URL
        file_obj = request.FILES["media"]
        img_filename = str(uuid.uuid1()).replace("-", "") + os.path.splitext(file_obj.name)[-1]

        media_root = settings.MEDIA_ROOT
        today = str(date.today())
        path = pathlib.Path(media_root, today)

        if not path.exists():
            os.makedirs(str(path))

        with open(str(path / img_filename), 'wb+') as fd:
            for chunk in file_obj.chunks():
                fd.write(chunk)

        img_url = os.path.join(media_url, today, img_filename)
        return JsonResponse(data=dict(img_url=img_url))


class ListQuestionnaireSurveyApi(ListAPIView):
    serializer_class = QuestionnaireSerializer

    def get_queryset(self):
        title = self.request.query_params.get('title')
        query = dict(is_del=False)
        title and query.update(title__icontains=title)
        queryset = models.QuestionnaireModel.objects.filter(**query).all()

        return queryset


class UpdateQuestionnaireSurveyApi(UpdateAPIView):
    serializer_class = QuestionnaireSerializer

    def get_object(self):
        survey_id = self.request.data.get('id') or 0
        return models.QuestionnaireModel.objects.get(id=survey_id)

    def post(self, request, *args, **kwargs):
        return self.update(request, *args, partial=True, **kwargs)


class SaveQuestionnaireApi(APIView):
    """ 保存问卷 """

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data

        questionnaire_id = data.get("questionnaire_id")
        questionnaire_fields = dict(
            user_id=user.id, status=data.get("status", 0),
            title=data.get("title", ""), desc=data.get("desc", ""),
            save_time=datetime.now() if data.get("status", 0) == 1 else "1970-01-01 00:00:00",
            published_time=datetime.now() if data.get("status", 0) == 2 else "1970-01-01 00:00:00",
        )

        with transaction.atomic():
            if not questionnaire_id:
                questionnaire_obj = models.QuestionnaireModel(**questionnaire_fields)
            else:
                questionnaire_obj = models.QuestionnaireModel.objects.filter(id=questionnaire_id, is_del=False).first()
                questionnaire_obj.save_attributes(**questionnaire_fields)

            # 保存问卷
            questionnaire_obj.save()
            questionnaire_id = questionnaire_obj.id

            # 题目列表
            actual_question_ids = []
            questions_list = data.get("questions", [])
            questions_queryset = models.QuestionModel.objects.filter(questionnaire_id=questionnaire_id, is_del=False)
            question_dict = {question_obj.id: question_obj for question_obj in questions_queryset}

            for order, question in enumerate(questions_list, 1):
                question_id = question.get("question_id") or 0
                question_fields = dict(
                    questionnaire_id=questionnaire_id, order=order,
                    title=question.get("title", ""), desc=question.get("desc", ""),
                    topic_id=question.get("topic_id", 0), img_url=question.get("img_url", ""),
                    is_required=question.get("is_required", True)
                )

                if question_id in question_dict:
                    actual_question_ids.append(question_id)

                    question_obj = question_dict[question_id]
                    question_obj.save_attributes(**question_fields)
                else:
                    question_obj = models.QuestionModel(**question_fields)

                # 保存题目
                question_obj.save()
                question_id = question_obj.id

                # 题目选项列表
                actual_option_ids = []
                option_list = question.get("options", [])
                option_queryset = models.Options.objects.filter(question_id=question_id, is_del=False)
                option_dict = {option_obj.id: option_obj for option_obj in option_queryset}

                for option_order, option in enumerate(option_list, 1):
                    option_id = option.get("option_id") or 0
                    option_fields = dict(
                        question_id=question_id,
                        order=option_order, title=option.get("title", ""),
                        min_value=option.get("min_value", ""), max_value=option.get("max_value", ""),
                    )

                    if option_id in option_dict:
                        actual_option_ids.append(option_id)

                        option_obj = option_dict[option_id]
                        option_obj.save_attributes(**option_fields)
                    else:
                        option_obj = models.Options(**option_fields)

                    option_obj.save()

                # 移除不需要的题目选项列表
                deleted_option_ids = list(option_dict.keys() - set(actual_option_ids))
                option_queryset.filter(id__in=deleted_option_ids).update(is_del=True)

            # 移除不需要的题目列表
            deleted_question_ids = list(question_dict.keys() - set(actual_question_ids))
            questions_queryset.filter(id__in=deleted_question_ids).update(is_del=True)

        return JsonResponse(data={})


class StaticServeApi(APIView):
    def get(self, request, path, *args, **kwargs):
        """ 静态文件 """
        return serve(request=request, path=path, document_root=settings.MEDIA_ROOT)


class ListQuestionnaireApi(APIView):
    """ 问卷列表 """

    def get(self, request, *args, **kwargs):
        user = request.user

        questionnaire_list = models.QuestionnaireModel.get_questionnaire_list()
        data = dict(list=questionnaire_list)

        return JsonResponse(data=data)


class DetailQuestionnaireApi(APIView):
    """ 问卷详情 """
    CONTENT_NEGOTIATOR_CAMEL = False

    def get(self, request, *args, **kwargs):
        user = request.user
        q_id = int(request.query_params.get("questionnaire_id") or 0)
        questionnaire_data = models.QuestionnaireModel.get_questionnaire_detail(q_id)

        return JsonResponse(data=questionnaire_data)


class StatisticsResultSurveyAPi(APIView):
    def get(self, request, *args, **kwargs):
        """ 问卷统计结果 """
        start_time = time.time()
        _connection = connections["default"]
        cursor = _connection.cursor()
        questionnaire_id = int(self.request.query_params.get("questionnaire_id") or 0)

        # 计算提交的问卷数量
        sql_params = [DingMsgPushLogModel._meta.db_table, DingMessageModel._meta.db_table, questionnaire_id]
        cursor.execute("""
            SELECT COUNT(a.id) FROM %s a 
            JOIN %s b 
            ON a.ding_msg_id=b.id 
            WHERE b.ihcm_survey_id=%s AND a.is_del=false AND b.is_del=False
        """ % tuple(sql_params))
        survey_db_ret = cursor.fetchone()
        survey_total_cnt = survey_db_ret[0][0] if survey_db_ret else 0

        department_userCnt_dict = {}
        user_dep_sql = """
            SELECT usr_id, first_dep FROM circle_user_department_relation AS ud_rel
            WHERE is_alive=TRUE 
            AND EXISTS (
                SELECT usr_id FROM (
                    SELECT usr_id FROM circle_users aa
                    WHERE EXISTS (
                        SELECT receiver_mobile FROM (
                            SELECT receiver_mobile FROM circle_ding_msg_push_log AS a_log  
                            JOIN circle_ding_message_info AS b_msg 
                            ON a_log.ding_msg_id=b_msg.id AND b_msg.ihcm_survey_id=%s 
                            WHERE a_log.is_done=true AND a_log.is_del=false
                        ) as bb
                        WHERE bb.receiver_mobile=aa.phone_number
                    )
                ) AS cc
                WHERE cc.usr_id=ud_rel.usr_id
            )
        """
        # 人员与部门映射
        cursor.execute(user_dep_sql, (questionnaire_id, ))
        user_dep_relation_dict = {item[0]: item[1] for item in cursor.fetchall()}

        start_ts2 = time.time()
        logger.info("StatisticsResultSurveyAPi cost time 001: %s", start_ts2 - start_time)

        # 统计一级部门人数
        for first_dep in user_dep_relation_dict.values():
            department_userCnt_dict[first_dep] = department_userCnt_dict.get(first_dep, 0) + 1

        start_ts4 = time.time()
        logger.info("StatisticsResultSurveyAPi cost time 003: %s", start_ts4 - start_ts2)

        # 一级部门
        department_where = "parent_dep_id='root' AND is_alive=true ORDER BY display_order"
        cursor.execute("SELECT dep_id, dep_name FROM circle_ding_department WHERE " + department_where)
        department_dict = {item[0]: item[1] for item in cursor.fetchall()}

        start_ts5 = time.time()
        logger.info("StatisticsResultSurveyAPi cost time 004: %s", start_ts5 - start_ts4)

        # 最终统计
        # exclude_dep_set = {"复星", "复星津美", "OneFosun会务系统"}
        exclude_dep_set = set()
        dep_result = [
            dict(dep_name=dep_name, dep_id=dep_id, user_cnt=department_userCnt_dict.get(dep_id, 0))
            for dep_id, dep_name in department_dict.items()
            if dep_name not in exclude_dep_set and department_userCnt_dict.get(dep_id, 0) > 0
        ]
        dep_user_cnt = sum([item["user_cnt"] for item in dep_result])

        end_time1 = time.time()
        logger.info("StatisticsResultSurveyAPi cost time 005: %s", end_time1 - start_ts5)

        data = SurveyVoteService().get_survey_statistics_result(questionnaire_id)
        # data = {}
        data.update(survey_total_cnt=survey_total_cnt, dep_result=dep_result, dep_user_cnt=dep_user_cnt)

        logger.info("StatisticsResultSurveyAPi cost time 002: %s", time.time() - end_time1)
        return Response(data=data, status=200)


class ListSurveyVoteAPi(APIView):
    def get(self, request, *args, **kwargs):
        """ 问卷列表
        query_params:
            mobile:         用户手机号
            keyword:        搜索问卷的关键字
            state:          问卷状态: open, closed
            submit_state:   问卷提交状态: 0,未提交; 1,已提交; 2-所有api返回的问卷
            is_vote_admin:  1,所有问卷; 0,用户自己相关的问卷
            from:           app-手机端; cms-管理后台
        """
        query_params = request.query_params
        mobile = query_params.get("mobile") or ""
        submit_state = query_params.get("submit_state")
        submit_state = 2 if submit_state is None else int(submit_state)
        is_statistics_perm = int(query_params.get("is_vote_admin") or 0)  # app 是否看统计数据的权限
        _from = query_params.get("from")  # 区分调用接口开源 默认 app,

        if not mobile:
            raise ValueError("手机号不能为空")

        user = CircleUsersModel.get_user_by_mobile(mobile=mobile, add_uuc=False)

        if user is None:
            raise ObjectDoesNotExist("用户不存在<mobile:%s>" % mobile)

        survey_sql = """
            SELECT b.ihcm_survey_id, a.is_done FROM %s a 
            JOIN %s b 
            ON a.ding_msg_id=b.id AND b.ihcm_survey_id > 0
            WHERE a.receiver_mobile='%s' AND a.is_del=false AND b.is_del=False
            ORDER BY b.ihcm_survey_id
        """
        sql_params = [DingMsgPushLogModel._meta.db_table, DingMessageModel._meta.db_table, mobile]
        cursor = connections["default"].cursor()
        cursor.execute(survey_sql % tuple(sql_params))
        db_survey_ret = [dict(ihcm_survey_id=item[0], is_done=item[1]) for item in cursor.fetchall()]

        survey_done_dict = {
            survey_id: any([it["is_done"] for it in items])
            for survey_id, items in groupby(db_survey_ret, key=itemgetter("ihcm_survey_id"))
        }

        # 从 ihcm 中获取问卷列表
        if not is_statistics_perm:
            survey_ids = list(survey_done_dict.keys()) or [0]
        else:
            survey_ids = ()
            query_params = dict(query_params, size=1000)

        if _from == "cms":
            survey_ids = ()  # 管理后台需要获取 open 和 closed 的问卷
            query_params = dict(query_params, state="")

        survey_result = SurveyVoteService().get_survey_list(query_params, ding_survey_ids=survey_ids)

        survey_list = []
        count = survey_result.pop("count", 0)
        ihcm_survey_list = survey_result.pop("list", [])

        for item in ihcm_survey_list:
            questionnaire_id = item["questionnaire_id"]
            is_done = bool(survey_done_dict.get(questionnaire_id))
            survey_item = dict(is_done=is_done, **item)

            if submit_state == 0:
                not is_done and survey_list.append(survey_item)
            elif submit_state == 1:
                is_done and survey_list.append(survey_item)
            else:
                survey_list.append(survey_item)

        if is_statistics_perm == 1:
            survey_list = [_item for _item in survey_list if _item["creator"] == mobile]
            count = len(survey_list)

        data = dict(count=count, list=survey_list, is_vote_admin=user.is_vote_admin, mobile=mobile)
        return Response(data=data, status=200)


class DoneSurveyVoteApi(APIView):
    def _get_survey_records(self, params_or_data):
        params_or_data = params_or_data or self.request.data
        mobile = params_or_data.get("mobile")
        survey_id = int(params_or_data.get("questionnaire_id") or 0)

        if not mobile or not survey_id:
            raise ValidationError("手机或问卷id不能为空")

        msg_query = dict(ihcm_survey_id=survey_id, source=2, is_del=False)
        msg_id_list = DingMessageModel.objects.filter(**msg_query).values_list('id', flat=True)

        filter_kwargs = dict(receiver_mobile=mobile, ding_msg_id__in=msg_id_list, is_del=False)
        queryset = DingMsgPushLogModel.objects.filter(**filter_kwargs).order_by("-create_time")
        return queryset

    def get(self, request, *args, **kwargs):
        """ 问卷投票是否完成 """
        params = request.query_params
        queryset = self._get_survey_records(params)
        msg_obj = queryset[0] if queryset.exists() else None

        data = dict(
            is_done=any([obj.is_done for obj in queryset]),
            mobile=params.get("mobile"), questionnaire_id=params.get("questionnaire_id")
        )
        return Response(data=data, status=200)

    def post(self, request, *args, **kwargs):
        """ 完成问卷提交 """
        data = request.data
        is_cryptonym = bool(request.data.get("isCryptonym"))
        queryset = self._get_survey_records(data)

        if not queryset.exists():
            logger.info("DoneSurveyVoteApi.msg_obj<post> is empty")

            mobile = data.get("mobile")
            survey_id = int(data.get("questionnaire_id") or 0)

            if mobile and survey_id:
                ding_msg_queryset = DingMessageModel.objects.filter(is_del=False)
                message_obj = ding_msg_queryset.filter(ihcm_survey_id=survey_id).first()

                DingMsgPushLogModel.objects.create(
                    receiver_mobile=mobile, receive_time=datetime.now(), read_time=datetime.now(),
                    is_success=True, is_done=True, is_cryptonym=is_cryptonym, traceback="share",
                    ding_msg_id=message_obj.id if message_obj else ding_msg_queryset.first().id,
                    msg_uid=str(Snowflake().get_id())
                )
        else:
            queryset.update(is_cryptonym=is_cryptonym, is_done=True)

        return Response(data=None, status=200)


class DetailSurveyVoteApi(APIView):
    """ 问卷详情 """
    def get(self, request, *args, **kwargs):
        mobile = request.query_params.get('mobile')
        survey_id = request.query_params.get('questionnaire_id')

        data = SurveyVoteService().get_survey_detail(survey_id, mobile=mobile)
        survey_obj = models.QuestionnaireModel.objects.filter(Q(id=survey_id) | Q(ref_id=survey_id), is_del=False).first()
        data['is_anonymous'] = survey_obj and survey_obj.is_anonymous or False

        return Response(data=data, status=200)


class CreateSurveyVoteApi(APIView):
    def post(self, request, *args, **kwargs):
        mobile = request.query_params.get('mobile')
        data = SurveyVoteService().save_survey_detail(mobile, survey_data=request.data)
        return Response(data=data, status=200)


class SyncSurveyVoteApi(APIView):
    def post(self, request, *args, **kwargs):
        """  """
        user = request.user
        sync_survey(user_id=user.id)
        return Response(data=None, status=200)

