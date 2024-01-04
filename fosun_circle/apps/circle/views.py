import json
import uuid
import time
import os.path
import traceback
from itertools import chain

from django.db import connections
from django.conf import settings
from django.utils import timezone
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.schemas import AutoSchema
import coreapi
import requests

from . import models
from . import serializers
from . import service
from fosun_circle.core.views import ListVueView, SingleVueView
from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.libs.utils.crypto import AESCipher
from fosun_circle.contrib.drf.throttling import ApiClientRateThrottle
from fosun_circle.apps.circle.tasks.task_notify import notify_star_or_comment


class CircleActionLogApi(APIView):
    def post(self, request, *args, **kwargs):
        """ 星圈帖子点赞或评论的推送 """
        is_async = request.data.pop("is_async", True)
        if is_async:
            notify_star_or_comment.delay(**request.data)
        else:
            notify_star_or_comment.run(**request.data)

        return Response()


class CircleAnnualSummaryApi(APIView):
    def get(self, request, *args, **kwargs):
        """ 员工年度总结 """
        mobile = request.query_params.get("mobile")
        annual = int(request.query_params.get("annual") or 0)

        if not annual:
            annual = (timezone.datetime.now() - timezone.timedelta(days=30)).year

        queryset = models.CircleAnnualPersonalSummaryModel.objects.filter(is_del=False)
        annual_obj = queryset.filter(mobile=mobile, annual=annual).first()
        data = dict(is_customized=bool(annual_obj))

        conn = connections["bbs_user"]
        cursor = conn.cursor()

        # 我有话要说 的最多点赞
        sql = """
            SELECT 
                a.is_actual, a.content, a."upCount", a.user_id, b.fullname, b."nickName" 
            FROM "starCircle_starcircle" a
            JOIN users_userinfo b ON a.user_id =b.id
            WHERE a.id IN (
                SELECT circle_id FROM "starCircle_circle2tag"
                WHERE tag_id=31
            ) AND a.is_show=TRUE AND a.is_delete=FALSE
            ORDER BY a."upCount" DESC LIMIT 5
        """
        cursor.execute(sql)
        db_ret = cursor.fetchall()
        is_actual = db_ret[0][0]

        data.update(
            top_star_username=db_ret[0][4] if is_actual else db_ret[0][5],  # 我有话要说点赞最多的人
            top_star_cnt=db_ret[0][2],
            top_star_circle_text=db_ret[0][1],
        )

        if annual_obj:
            data.update(annual_obj.to_dict())

        return Response(data=data)


class BbsFuzzySearchUserApi(APIView):
    def get(self, request, *args, **kwargs):
        """ @user搜索 """
        key = self.request.query_params.get("key") or ""
        mobile = self.request.query_params.get("mobile")

        assert mobile is not None, "参数手机号丢失"

        db_user_results = []
        conn = connections['bbs_user']
        cursor = conn.cursor()

        # 先查询之前有@Ta的人员
        cursor.execute('SELECT id FROM users_userinfo WHERE "phoneNumber"=%s', (mobile, ))
        db_user_ret = cursor.fetchone()
        user_id = db_user_ret and db_user_ret[0] or 0

        cursor.execute('SELECT "parentComment_id" FROM "starCircle_circlecomment" '
                       'WHERE user_id=%s AND is_show=true', (user_id,))
        parent_comment_ids = [str(item[0]) for item in cursor.fetchall() if item[0]]

        if parent_comment_ids:
            cursor.execute('SELECT user_id FROM "starCircle_circlecomment" '
                           'WHERE nid in (%s) AND is_show=true' % ','.join(parent_comment_ids))
            related_user_ids = [str(item[0]) for item in cursor.fetchall() if item[0]]
        else:
            related_user_ids = []

        user_sql = '''
            SELECT id, real_avatar, fullname, "phoneNumber", "jobCode" FROM users_userinfo 
            WHERE fullname like '%%%s%%' AND "isJob"=true AND "jobCode"<>'' AND "jobCode" IS NOT NULL 
        ''' % key

        if related_user_ids:
            _sql = user_sql + " AND id IN (%s) " % ','.join(related_user_ids)
            cursor.execute(_sql)
            db_user_results.extend(cursor.fetchall())

        # 其余全表查询
        limit = 10 - len(db_user_results)
        _sql = user_sql
        if related_user_ids:
            _sql += ' AND id NOT IN (%s) ' % ','.join(related_user_ids)

        _sql += " ORDER BY id ASC LIMIT %s" % limit
        cursor.execute(_sql)
        user_list = [
            dict(user_id=it[0], avatar=it[1], fullname=it[2], mobile=it[3], job_code=it[4])
            for it in chain(db_user_results, cursor.fetchall())
        ]

        return Response(data=user_list)


class ListCircleTagLotteryApi(generics.ListAPIView):
    serializer_class = serializers.CircleTagSerializer

    def paginate_queryset(self, queryset):
        """ 此接口不需要分页 """

    def get_queryset(self):
        cursor = connections['bbs_user'].cursor()
        sql = """
            SELECT id, title FROM "starCircle_tag"
            WHERE is_delete=false AND is_show=TRUE  
            ORDER BY is_official DESC, created_time DESC
            LIMIT 50
        """
        cursor.execute(sql)

        fields = ('tag_id', 'tag_name')
        return [dict(zip(fields, items)) for items in cursor.fetchall()]


class CircleTagApi(APIView):
    def get(self, request, *args, **kwargs):
        key = request.query_params.get('key')
        cursor = connections['bbs_user'].cursor()

        is_esg = service.CircleBBSService(request).has_esg
        sql = """SELECT id, title FROM "starCircle_tag" WHERE is_delete=false AND is_show=TRUE"""

        if is_esg:
            sql += " AND tag_desc='ESG'"
        else:
            sql += " AND (tag_desc IS NULL OR tag_desc <> 'ESG') "

        if key:
            sql += " AND title like '%%%s%%'" % key

        sql += " ORDER BY created_time DESC Limit 10"
        cursor.execute(sql)

        fields = ('tag_id', 'tag_name')
        tag_list = [dict(zip(fields, items)) for items in cursor.fetchall()]
        return Response(data=dict(list=tag_list))

    def post(self, request, *args, **kwargs):
        title = request.data.get('title')
        tag_desc = request.data.get('tag_desc')

        conn = connections['bbs_user']
        cursor = conn.cursor()
        sql = """
            INSERT INTO "starCircle_tag"(
                is_show, is_delete, title, is_recommend, is_official, 
                tag_desc, is_top, created_time, update_time
                )
            VALUES (true, false, %s, false, false, %s, false, NOW(), NOW())
        """
        cursor.execute(sql, (title, tag_desc))
        conn.commit()

        return Response()


class ListCircleUserApi(APIView):
    def get(self, request, *args, **kwargs):
        key = request.query_params.get('key', "")
        cursor = connections['bbs_user'].cursor()

        sql = "SELECT id, fullname FROM users_userinfo "

        if key.isdigit():
            sql += """ WHERE "phoneNumber" like '%%%s%%' """ % key
        elif key:
            sql += " WHERE fullname like '%%%s%%' " % key

        sql += " ORDER BY id DESC Limit 10"
        cursor.execute(sql)

        fields = ('id', 'name')
        user_list = [dict(zip(fields, items)) for items in cursor.fetchall()]
        return Response(data=dict(list=user_list))


class ListCircleApi(APIView):
    throttle_classes = (ApiClientRateThrottle, )

    ACTION_LIST = []

    def get(self, request, *args, **kwargs):
        """ 星圈发帖 """
        circle_ret = service.CircleBBSService(request).get_circle_list()
        return Response(data=circle_ret)

    def post(self, request, *args, **kwargs):
        """ 星圈发帖|评论删除 """


class DetailCircleApi(APIView):
    def get(self, request, *args, **kwargs):
        circle_ret = service.CircleBBSService(request).get_circle_list()
        circle_list = circle_ret['list']

        if circle_list:
            circle_item = circle_list[0]
        else:
            circle_item = {}

        return Response(data=circle_item)


class ListCommentOfCircleApi(APIView):
    def get(self, request, *args, **kwargs):
        """ 发帖对应的评论列表 """
        comment_ret = service.CircleBBSService(request).get_comment_of_circle_list()
        return Response(data=comment_ret)


class ListCommentApi(APIView):
    def get(self, request, *args, **kwargs):
        """ 所有的评论列表 """
        comment_ret = service.CircleBBSService(request).get_comment_list()
        return Response(data=comment_ret)


class SetCommentStateApi(APIView):
    def post(self, request, *args, **kwargs):
        """ 设置帖子状态(隐藏或展示) """
        ret = service.CircleBBSService(request=request).set_comment_state()
        data = dict(message=ret['msg'], code=603) if not ret['is_ok'] else None

        return Response(data=data)


class ListTagApi(APIView):
    def get(self, request, *args, **kwargs):
        """ 标签列表 """
        tag_list = service.CircleBBSService(request).get_tag_list()
        return Response(data=tag_list)


class OperationTagApi(APIView):
    def post(self, request, *args, **kwargs):
        """ 话题标签操作(设置官方、修改、删除、热门置顶) """
        service.CircleBBSService(request).operate_tag()
        return Response()


class CircleView(ListVueView):
    template_name = 'circle/bbs_circle_mgr.html'

    def get_pagination_list(self):
        data = service.CircleBBSService(request=self.request).get_circle_list()
        data['is_overseas_region'] = settings.IS_OVERSEAS_REGION
        return data


class CircleCommentView(ListVueView):
    template_name = 'circle/bbs_comment_mgr.html'

    def get_pagination_list(self):
        return service.CircleBBSService(request=self.request).get_comment_list()


class CircleOperationsView(SingleVueView):
    template_name = 'circle/bbs_operations_mgr.html'


class CircleSlideshowView(SingleVueView):
    template_name = 'circle/bbs_slideshow_mgr.html'


class TagView(SingleVueView):
    template_name = 'circle/bbs_tag_mgr.html'


class CircleSlideshowApi(APIView):
    def get(self, request, *args, **kwargs):
        banner_list = service.CircleBBSService(request).get_slideShow_list()
        return Response(data=banner_list)

    def post(self, request, *args, **kwargs):
        service.CircleBBSService(request).operate_slideShow()
        return Response(data=None)


class CircleDDShareView(SingleVueView):
    template_name = 'circle/bbs_ddShare_mgr.html'


class CircleDDShareApi(APIView):
    def get(self, request, *args, **kwargs):
        banner_list = service.CircleBBSService(request).get_ddshare_list()
        return Response(data=banner_list)

    def post(self, request, *args, **kwargs):
        service.CircleBBSService(request).operate_ddshare()
        return Response(data=None)


class UserXTokenApi(APIView):
    TOKEN_API = '/user/token'

    def post(self, request, *args, **kwargs):
        mobile = request.data.get('mobile')
        salt_key = os.environ.get('IHCM_API_TOKEN') or request.data.get('salt')

        text = "%s:%s:%s:%s" % (str(uuid.uuid1()), mobile, int(time.time() * 1000), str(uuid.uuid1()))
        cipher_text = AESCipher(key=salt_key).encrypt(raw=text)

        headers = {"Content-Type": "application/json"}
        api_path = settings.CIRCLE_API_HOST + self.TOKEN_API
        resp = requests.post(api_path, data=json.dumps(dict(mobtsk=cipher_text)), headers=headers)

        if resp.status_code == 200:
            data = resp.json()

            if data.get('code') == 200:
                return Response(data=dict(token=data.get('token')))

            logger.info('获取token失败<%s>: %s', self.TOKEN_API, data.get('message'))

        raise ValueError("获取用户X-Token失败")


class SetCircleTopPageApi(APIView):
    def post(self, request, *args, **kwargs):
        """ 帖子在标签列表中置顶 """
        ret = service.CircleBBSService(request=request).set_circle_top_page()
        data = dict(message=ret['msg'], code=601) if not ret['is_ok'] else None

        return Response(data=data)


class SetCircleStateApi(APIView):
    def post(self, request, *args, **kwargs):
        """ 设置帖子状态(隐藏或展示) """
        ret = service.CircleBBSService(request=request).set_circle_state()
        data = dict(message=ret['msg'], code=602) if not ret['is_ok'] else None

        return Response(data=data)


class CircleCommentApi(APIView):
    def post(self, request, *args, **kwargs):
        """ 帖子回复(管理后台回复) """
        ret = service.CircleBBSService(request=request).add_admin_comment()
        data = dict(message=ret['msg'], code=603) if not ret['is_ok'] else None

        return Response(data=data)


class ListCircleEventTrackingApi(APIView):
    def get(self, request, *args, **kwargs):
        """ bbs 埋点数据 (MAU, DAU, 发帖数与点赞数) """
        dt_fmt = "%Y-%m-%d"
        today = timezone.datetime.now().date()
        start = request.query_params.get("start_date")
        end = request.query_params.get("end_date")

        # ev_type: 0, 网站运营数据; 1, HR知乎运营数据
        ev_type = int(request.query_params.get("ev_type") or 0)

        start_date = timezone.datetime.strptime(start, dt_fmt) if start else today
        end_date = timezone.datetime.strptime(end, dt_fmt) if end else today
        circle_service = service.CircleBBSService(request=request)

        if ev_type == 0:
            result = circle_service.get_event_tracking_data(start_date, end_date)
        elif ev_type == 1:
            result = circle_service.get_hr_zhihu_event_tracking_data(start_date, end_date)
        else:
            raise ValueError('获取埋点运营数据错误！')

        logger.info('ListCircleEventTrackingApi -> start_date: %s, end_date: %s', start_date, end_date)
        return Response(data=result)



