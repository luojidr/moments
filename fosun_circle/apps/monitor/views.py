import os
import re
import uuid

from django.shortcuts import render
from django.utils import timezone
from django.conf import settings
from django.views.generic import View, TemplateView
from django_redis import get_redis_connection

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import Throttled

from fosun_circle.libs import redis_helpers
from fosun_circle.core.views import SingleVueView
from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.libs.utils.crypto import BaseCipher
from fosun_circle.core.ding_talk.robot import DDCustomRobotWebhook


# Create your views here.
class FlowerView(SingleVueView):
    template_name = "monitor/celery_flower.html"

    def get_queryset(self):
        if settings.DEBUG:
            url = "http://192.168.190.128:5555/"
        else:
            url = "https://flower.focuth.com/"

        return dict(url=url, otp_data=dict(code_2fa="", url_2fa=""))


class Inner404View(SingleVueView):
    template_name = "monitor/404.html"


class ErrorPageView(View):
    def get(self, request, *args, **kwargs):
        error_code = int(kwargs.get('error_code', 0))
        if error_code not in [500, 404, 403]:
            raise ValueError('Error page must is 500, 404 or 403.')

        template_name = '%s.html' % error_code
        return render(request, template_name)


class DevOpsNotificationView(TemplateView):
    template_name = "monitor/devops_notify.html"

    def get_context_data(self, **kwargs):
        redis = get_redis_connection()
        error_id = self.request.GET.get('error_id')

        if not error_id or not redis.exists(error_id):
            raise ValueError("Not found error's message.")

        error_kwargs = redis.hgetall(error_id)
        context = super().get_context_data(**kwargs)
        context.update(**error_kwargs)

        return context


class DDCustomRobotWebhookApi(APIView):
    throttle_classes = ()

    PUSH_ID = 1000
    ERROR_KEY_PREFIX = 'dd_robot'
    ERROR_RETRY_EXPIRATION = 5 * 60             # 5m 同一错误不重发
    ERROR_VISIBLE_EXPIRATION = 7 * 24 * 3600    # 7d 错误详情页面过期
    IGNORE_EXCEPTIONS = [Throttled]

    def _get_unique_error_id(self, error_time=None):
        error_time = error_time or timezone.datetime.now() + timezone.timedelta(hours=8)
        error_str = error_time.strftime('%Y-%m-%d %H:%M:%S')
        key_suffix = re.compile(r'[-:\s]').sub("", error_str + "_" + str(uuid.uuid1()))

        return '%s_%s' % (self.ERROR_KEY_PREFIX, key_suffix)

    def _to_redis(self, error_id, err_kwargs):
        redis_helpers.hset(error_id, mapping=err_kwargs, expires=self.ERROR_VISIBLE_EXPIRATION)

    def _is_retry(self, project_name, task_name, error_msg, **kwargs):
        # 同一项目同一任务同一错误5m内不重发
        redis = get_redis_connection(alias='redis_db1')
        error_args = (project_name, task_name, error_msg)
        key = 'dd_robot_retry:%s' % BaseCipher.crypt_md5("%s:%s:%s" % error_args)

        if redis.set(key, 1, ex=self.ERROR_RETRY_EXPIRATION, nx=True):
            logger.info('DD Alarm => project_name: %s, task_name: %s, error_msg: %s', *error_args)
            return True

        return False

    def _get_failed_message(self):
        request = self.request
        title = request.data.get('title')
        push_time = timezone.datetime.now() + timezone.timedelta(hours=8)

        error_url = request.data.get('error_url', "")
        error_id = self._get_unique_error_id(error_time=push_time)
        error_detail = request.data.get('error_detail', "")

        if any([err_cls.__name__ in error_detail for err_cls in self.IGNORE_EXCEPTIONS]):
            return {}

        if not error_url:
            error_url = "{host}/{error_page_url}?error_id={error_id}".format(
                host=settings.CIRCLE_HOST, error_id=error_id,
                error_page_url=settings.CIRCLE_ERROR_PAGE_URL,
            )

        error_kwargs = dict(
            title=title,
            run_time=request.data.get('run_time'),
            error_msg=request.data.get('error_msg', ""),
            error_detail=error_detail,
            error_time=request.data.get('error_time'),
            task_name=request.data.get('task_name'),
            project_name=request.data.get('project_name'),
            error_url=error_url, push_time=push_time.strftime('%Y-%m-%d %H:%M:%S')
        )

        text = "### {title}\n\n > " \
               "项目: {project_name}\n\n > " \
               "任务名称: {task_name}\n\n > " \
               "执行时间：{run_time}\n\n > " \
               "出错时间：{error_time}\n\n > " \
               "状态：Failure: {error_msg}\n\n " \
               "######   您可以点击查看 [查看错误详情]({error_url}) {push_time}".format(**error_kwargs)

        if not self._is_retry(**error_kwargs):
            return {}

        self._to_redis(error_id, error_kwargs)
        return dict(msgtype='markdown', title=title, text=text)

    def post(self, request, *args, **kwargs):
        """ 自定义钉钉机器人推送消息 """
        if request.data.get('push_id') == self.PUSH_ID:
            msg_form = self._get_failed_message()
        else:
            msg_form = request.data.get('form')

        # 仅生产与本地可推送告警
        app_env = os.getenv("APP_ENV") or os.getenv('ENVIRONMENT') or request.data.get('app_env')
        is_send = (app_env or "").upper() in ['PROD', 'LOCAL', 'PRD']

        if msg_form and is_send:
            DDCustomRobotWebhook(
                webhook=request.data.get('webhook_url'),
                access_token=request.data.get('access_token'),
                secret=request.data.get('secret'),
                keywords=request.data.get('keywords')
            ).send(
                at_mobiles=request.data.get('at_mobiles') or [],
                at_user_ids=request.data.get('at_user_ids') or [],
                is_at_all=request.data.get('is_at_all') or False,
                **msg_form
            )

        return Response(data=None)

