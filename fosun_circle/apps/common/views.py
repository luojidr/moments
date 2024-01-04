import re
import uuid
import os.path
import traceback
from datetime import date

import cv2
import requests

from django.conf import settings
from django.http import Http404
from django.views import View
from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django_redis import get_redis_connection
from rest_framework.generics import GenericAPIView
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from croniter import croniter

from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.core.files.export import FileExport
from questionnaire.models import QuestionnaireModel
from questionnaire.utils import export_survey
from fosun_circle.core.ali_oss.upload import AliOssFileUploader
from fosun_circle.libs.pdf2image import pdf2image
from ding_talk.models import DingPeriodicTaskModel


class HealthCheckApi(GenericAPIView):
    throttle_classes = ()
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """ 健康检查 """
        return Response()


class CronParseApi(APIView):
    @staticmethod
    def get_cron_run_time_list(cron_expr, max_run_times=0, ding_cron_id=None):
        cron_expr_list = [s.strip() for s in (cron_expr or "").split(" ") if s.strip()]

        if len(cron_expr_list) != 5:
            return Response(data=dict(list=[], code=501, message='crontab表达式错误'))

        if ding_cron_id:
            ding_cron_obj = DingPeriodicTaskModel.objects.filter(id=ding_cron_id).first()
            deadline_run_time = ding_cron_obj and ding_cron_obj.deadline_run_time
        else:
            deadline_run_time = None

        run_time_list = []
        if settings.IS_DOCKER:
            start_time = timezone.datetime.now() + timezone.timedelta(hours=8)
        else:
            start_time = timezone.datetime.now()

        cron = croniter(" ".join(cron_expr_list), start_time)

        # 显示最近10次执行时间
        for i in range(max_run_times or 10):
            next_run_time = cron.get_next(timezone.datetime)

            if deadline_run_time and next_run_time > deadline_run_time:
                continue

            run_time_list.append(next_run_time.strftime("%Y-%m-%d %H:%M:%S"))

        return run_time_list

    def get(self, request, *args, **kwargs):
        """ 解析 linux crontab 运行时间 """
        cron_expr = request.query_params.get("cron_expr")
        ding_cron_id = request.query_params.get("ding_cron_id")
        max_run_times = int(request.query_params.get('max_run_times') or 0)
        run_time_list = self.get_cron_run_time_list(cron_expr, max_run_times, ding_cron_id)

        return Response(data=run_time_list)


class PDF2ImageApi(APIView):
    def post(self, request, *args, **kwargs):
        data = []
        up_fd = request.FILES.get('file')
        img_url = request.data.get('img_url')
        is_first = bool(request.data.get('is_first', 0))

        if img_url:
            r = requests.get(img_url)
            content = r.content
        else:
            content = up_fd.read()

        media_path = settings.TMP_ATTACHMENT_DIR
        # 因 default_storage 的文件存储依赖与 MEDIA_ROOT 配置，即在改目录下保存，但 Docker 在改目录下无权限保存，
        storage = FileSystemStorage(location=media_path)
        filename = os.path.join(str(uuid.uuid1()).replace('-', '') + ".pdf")
        relative_name = storage.save(filename, ContentFile(content))

        img_list = pdf2image(os.path.join(media_path, relative_name), img_dir=media_path)
        uploader = AliOssFileUploader()

        for img_path in img_list:
            ret = uploader.complete_upload(img_path, is_check=False)
            data.append(ret['url'])

            if is_first:
                break

        return Response(data=data)


class FileExportTestApi(View):
    def get(self, request, *args, **kwargs):
        """ KPI 下载 """
        filename = request.GET.get("filename")
        if not filename:
            raise Http404

        return FileExport(filename=filename).make_response()


class DownloadKPIView(View):
    def get(self, request, *args, **kwargs):
        """ KPI 下载 """
        start_date = request.GET.get("start_date") or str(date.today())
        end_date = request.GET.get("end_date") or str(date.today())

        params = dict(start_date=start_date, end_date=end_date)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"}
        resp = requests.get("https://fosunapi.focuth.com/api/event/tracking/dau/list", params=params, headers=headers)

        if resp.status_code == 200:
            data = resp.json()
            dau_list = data.get("dau_list", [{}])
            biz_mau = data.get("biz_mau", {})

            dau_headers = ["日期", "发帖数", "点赞数", "登录数", "DAU", "PV"]
            keys = ["date", "post_cnt", "star_cnt", "login_cnt", "dau_cnt", "pv"]
            value_list = [[item.get(k, "") for k in keys] for item in dau_list]
            value_list.insert(0, dau_headers)
            value_list.extend([["MAU合计", data.get("mau", 0)], []])

            biz_keys = list(biz_mau.keys())
            biz_values = [biz_mau[key] for key in biz_keys]
            value_list.extend([biz_keys, biz_values])

            filename = os.path.join(settings.MEDIA_ROOT, str(uuid.uuid1()) + ".xlsx")
            file_export = FileExport(filename, attachment_name="KPI运营数据")
            file_export.write_data(value_list)

            return file_export.make_response()

        raise Http404


class DownloadTagTopicView(View):
    IMG_WIDTH = 300
    IMG_HEIGHT = 400
    SAVE_DIR_PATH = '/tmp/excel_img'

    def _get_circle_info_list(self, tag_id):
        conn = connections["bbs_user"]
        cursor = conn.cursor()

        # 获取标签对应的话题
        sql = """
            SELECT 
                c.id AS tagId,
                c.title AS tagName,
                a.id AS circleId,
                a.content AS content,
                (CASE WHEN a.is_actual THEN u.fullname ELSE '匿名用户' END) AS username,
                a."upCount" AS postCnt
            FROM "starCircle_starcircle" a
            JOIN "starCircle_circle2tag" b ON a.id=b.circle_id AND a.is_delete=false
            JOIN "starCircle_tag" c ON b.tag_id = c.id
            JOIN users_userinfo u ON a.user_id=u.id
            WHERE b.tag_id=%s 
            ORDER BY a.created_time 
        """
        fields = ["tagId", "tagName", "circleId", "content", "username", "postCnt"]
        cursor.execute(sql, (tag_id,))
        circle_list = [dict(zip(fields, item)) for item in cursor.fetchall()]

        # 获取话题的图片链接
        circle_ids = [item["circleId"] for item in circle_list]
        img_sql = """
            SELECT 
                a.id AS circleId, b.url AS imgUrl
            FROM "starCircle_starcircle" a
            JOIN "starCircle_circleimage" b 
            ON a.id=b.circle_id AND a.is_delete=FALSE AND a.screen_style = ''
            WHERE b.is_delete=FALSE AND b.url <> '' AND a.id IN %s
        """

        if circle_ids:
            cursor.execute(img_sql, (tuple(circle_ids),))
            db_img_ret = cursor.fetchall()
        else:
            db_img_ret = []

        # 获取话题的评论
        comment_sql = """
            SELECT 
                a.circle_id AS circleId,
                (CASE WHEN a.is_actual THEN u.fullname ELSE '匿名用户' END) AS username,
                a.content AS content
            FROM "starCircle_circlecomment" a
            JOIN users_userinfo u ON a.user_id=u.id AND a.is_delete=false
            WHERE a.circle_id IN %s
        """

        if circle_ids:
            cursor.execute(comment_sql, (tuple(circle_ids),))
            db_comment_ret = cursor.fetchall()
        else:
            db_comment_ret = []

        # 数据集成
        for circle_item in circle_list:
            circle_id = circle_item["circleId"]
            url_list = circle_item.setdefault("imgUrl", [])
            comment_list = circle_item.setdefault("comment", [])

            for img_item in db_img_ret:
                if circle_id == img_item[0]:
                    url_list.append(img_item[1])

            for comment_item in db_comment_ret:
                if circle_id == comment_item[0]:
                    comment_list.append(dict(zip(["circleId", "username", "content"], comment_item)))

        return circle_list

    def _get_excel_values_list(self, tag_id):
        text_regex = re.compile(r'<.*?>', re.S | re.M)
        circle_list = self._get_circle_info_list(tag_id)

        filename_list = []
        excel_values_list = [["标签", "用户名", "内容", "点赞数", "图片1", "图片2"]]

        for item in circle_list:
            content = text_regex.sub('', item["content"])
            values = [item["tagName"], item["username"], content, item["postCnt"]]

            for img_url in item["imgUrl"]:
                req = requests.get(img_url)
                filename = self.compress_and_resize_image(req.content, self.SAVE_DIR_PATH)

                if filename:
                    values.append(dict(type="img", filename=filename,
                                       options={"x_scale": self.IMG_WIDTH, "y_scale": self.IMG_HEIGHT}
                                       ))
                    filename_list.append(filename)

            excel_values_list.append(values)
            for comment_item in item["comment"]:
                comment_text = text_regex.sub('', comment_item["content"])
                excel_values_list.append(["评论", comment_item["username"], comment_text])
            else:
                # excel_values_list.append([])  # Newline
                pass

        return excel_values_list, filename_list

    def compress_and_resize_image(self, img_bytes, save_path, ext="jpg"):
        """ compress and resize """
        if ext not in ['jpg', 'jpeg', 'png']:
            raise ValueError("Image format not allowed!")

        if not img_bytes:
            return

        src_filename = os.path.join(save_path, str(uuid.uuid1()) + "_src." + ext)
        post_filename = os.path.join(save_path, str(uuid.uuid1()) + "_post." + ext)

        if ext == "png":
            rate = 9
            quality = cv2.IMWRITE_PNG_COMPRESSION
        else:
            rate = 50
            quality = cv2.IMWRITE_JPEG_QUALITY

        try:
            with open(src_filename, "wb") as fp:
                fp.write(img_bytes)

            # 压缩图片
            img = cv2.imread(src_filename)
            resize_img = cv2.resize(img, dsize=(self.IMG_WIDTH, self.IMG_HEIGHT))
            cv2.imwrite(post_filename, resize_img, [quality, rate])

        except:
            logger.error(traceback.format_exc())
        finally:
            os.remove(src_filename)

        return post_filename

    def _get_attachment_name(self, tag_id):
        conn = connections["bbs_user"]
        cursor = conn.cursor()

        cursor.execute('SELECT title FROM "starCircle_tag" WHERE is_delete=false AND id=%s', (tag_id,))
        dn_ret = cursor.fetchone()

        return dn_ret and dn_ret[0] or "empty"

    def get(self, request, *args, **kwargs):
        """ 标签的相关话题 下载 """
        tag_id = request.GET.get("tag_id", 0)
        task_id = request.GET.get("task_id")

        if task_id is None:
            raise ValueError("DownloadTagTopicApi => 下载任务 task_id 不能为空.")

        cache.set(task_id, 0, 10 * 60)
        os.makedirs(self.SAVE_DIR_PATH, exist_ok=True)
        excel_values, file_list = self._get_excel_values_list(tag_id)
        filename = os.path.join(self.SAVE_DIR_PATH, str(uuid.uuid1()) + ".xlsx")

        try:
            file_export = FileExport(filename, attachment_name=self._get_attachment_name(tag_id))
            response = file_export.make_response(excel_values)
            logger.info("DownloadTagTopicApi => 临时附件已生成")

            cache.set(task_id, 1, 10 * 60)
            return response
        except:
            logger.error(traceback.format_exc())
        finally:
            for file_name in os.listdir(self.SAVE_DIR_PATH):
                _, ext = os.path.splitext(file_name)

                if ext[1:].lower() in ['jpg', 'jpeg', 'png']:
                    os.remove(os.path.join(self.SAVE_DIR_PATH, file_name))


class StateDownloadView(View):
    def get(self, request, *args, **kwargs):
        """ 任务下载状态 """
        task_id = request.GET.get("task_id", "none")
        download_state = cache.get(task_id)

        if download_state is not None:
            if int(download_state) == 1:
                state = "ok"
                msg = "%s 任务附件下载已完成" % task_id
            else:
                state = "going"
                msg = "%s 任务附件正在下载中" % task_id
        else:
            state = "empty"
            msg = "%s 任务不存在" % task_id

        return JsonResponse(data=dict(state=state, msg=msg))


class SurveyDownloadView(View):
    SURVEY_REDIS_KEY = 'odoo_survey_%s'

    def get(self, request, *args, **kwargs):
        conn = get_redis_connection()

        survey_id = request.GET.get("survey_id")
        redis_key = self.SURVEY_REDIS_KEY % survey_id
        conn.delete(redis_key)

        survey_sql = "SELECT title FROM survey_survey WHERE id=%s" % survey_id
        attachment_name = export_survey.get_survey_data(survey_sql)[0][0]

        survey_obj = QuestionnaireModel.objects.filter(is_del=False, ref_id=survey_id).first()

        if survey_obj is None:
            raise ValueError('问卷<survey_id: %s>不存在' % survey_id)

        conn.set(redis_key, 'downloading', ex=30 * 60 * 60)
        is_required_user = not survey_obj.is_anonymous
        values_list = export_survey.export_survey_detail(survey_id=survey_id, is_required_user=is_required_user)
        filename = os.path.join(settings.TMP_ATTACHMENT_DIR, str(uuid.uuid1()) + ".xlsx")
        file_export = FileExport(filename=filename, attachment_name=attachment_name)

        conn.set(redis_key, 'finished', ex=30 * 60 * 60)
        return file_export.make_response(values=values_list)


class StateSurveyDownloadApi(APIView):
    def get(self, request, *args, **kwargs):
        conn = get_redis_connection()
        survey_id = request.query_params.get("survey_id")
        redis_key = SurveyDownloadView.SURVEY_REDIS_KEY % survey_id
        state = conn.get(redis_key)

        return Response(data=dict(state=state))



