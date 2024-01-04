"""dj_backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os
import logging

from django.contrib import admin
from django.views.static import serve
from django.urls import path, include, re_path
from django.conf import settings

try:
    from django.conf.urls import url
except ImportError:
    from django.urls import path as url

logging.warning("settings.DEBUG：{0}".format(settings.DEBUG))


def download_staticfiles(request=None, is_static=False):
    logging.warning("download_staticfiles => is_static:%s", is_static)

    if not is_static:
        media_root = settings.MEDIA_ROOT
        filename = request.GET.get("filename", "/")
        return serve(request=request, path=filename, document_root=media_root)

    # 处理静态文件
    def static(req, path):
        document_root = settings.STATICFILES_DIRS[0]
        return serve(request=req, path=path, document_root=document_root)

    return static


urlpatterns = [
    path("admin/", admin.site.urls),
    # path('health/', include('health_check.urls')),      # PRD Useless
]

# Dev env to add mysql debug toolbar
if settings.DEBUG:
    from rest_framework_swagger.views import get_swagger_view

    schema_view = get_swagger_view(title='星圈客户端 Swagger Api', )
    urlpatterns += [
        re_path(r"^docs-swagger/", schema_view, name="swagger_docs"),
        # path('', include('django_celery_jobs.urls')),
    ]

    if getattr(settings, 'ACTIVE_DEBUG_TOOLBAR', False):
        import debug_toolbar
        urlpatterns += [url(r'^__debug__/', include(debug_toolbar.urls))]

    # Django-silk
    if getattr(settings, 'ACTIVE_SILK', False):
        urlpatterns.append(path(r'silk/profile', include('silk.urls', namespace='django_silk')))

from common import urls as common_urls
from users import urls as users_urls
from questionnaire import urls as questionnaire_urls
from ding_talk import urls as ding_urls
from aliyun import urls as aliyun_urls
from monitor import urls as monitor_urls
from wechatBot import urls as wechat_urls
from circle import urls as circle_urls
from lottery import urls as lottery_urls
from api_gateway import urls as gateway_urls
from permissions import urls as permissions_urls
from esg import urls as esg_urls

# K8S Deprecated
# if settings.IS_DOCKER:
#     urlpatterns += [re_path(r'^static(?P<path>.*)$', download_staticfiles(is_static=True), name='static')]
# logging.warning('Environ: APP_ENV: %s, IS_DOCKER: %s', os.getenv('APP_ENV', 'DEV'), settings.IS_DOCKER)

urlpatterns += [
    re_path("^$", view=users_urls.views.IndexView.as_view(), name="index"),
    re_path(r"^circle/user/", include(users_urls.view_urlpatterns)),
    re_path(r"^api/v1/circle/", include(users_urls.api_urlpatterns)),
    re_path(r"^api/v1/circle/", include(permissions_urls.token_api_urlpatterns)),

    re_path(r"^circle/questionnaire/", include(questionnaire_urls.view_urlpatterns)),
    re_path(r"^api/v1/circle/questionnaire/", include(questionnaire_urls.api_urlpatterns)),

    re_path(r"^circle/ding/", include(ding_urls.view_urlpatterns)),
    re_path(r"^api/v1/circle/ding/", include(ding_urls.api_urlpatterns)),

    re_path(r"^circle/aliyun/", include(aliyun_urls.view_urlpatterns)),
    re_path(r"^api/v1/circle/aliyun/", include(aliyun_urls.api_urlpatterns)),

    # 下载文件
    re_path(
        # r"^%s/(?P<path>.*)/download$" % re.escape(settings.MEDIA_URL.lstrip('/')),
        r"^circle/static/$", download_staticfiles, name="static_serve"
    ),

    # 自定义文件预览(静态文件) path
    re_path(
        "^%s/(?P<key_name>.*)$" % settings.MEDIA_URL.strip("/"),
        view=ding_urls.views.PreviewBucketMediaApi.as_view(), name="media_preview"
    ),

    re_path(r"^circle/monitor/", include(monitor_urls.view_urlpatterns)),
    re_path(r"^api/v1/circle/monitor/", include(monitor_urls.api_urlpatterns)),

    re_path(r"^api/v1/circle/wechat/", include(wechat_urls.api_urlpatterns)),

    re_path(r"^api/v1/circle/common/", include(common_urls.api_urlpatterns)),

    re_path(r"^circle/common/", include(common_urls.view_urlpatterns)),

    re_path(r"^circle/", include(circle_urls.view_urlpatterns)),
    re_path(r"^api/v1/circle/", include(circle_urls.api_urlpatterns)),

    re_path(r"^circle/lottery/", include(lottery_urls.view_urlpatterns)),
    re_path(r"^api/v1/lottery/", include(lottery_urls.api_urlpatterns)),

    re_path(r"^api/v1/gateway/", include(gateway_urls.api_urlpatterns)),

    re_path(r"^circle/permissions/", include(permissions_urls.view_urlpatterns)),
    re_path(r"^api/v1/permissions/", include(permissions_urls.api_urlpatterns)),

    re_path(r'^circle/esg/', include(esg_urls.view_urlpatterns)),
    re_path(r'^api/v1/esg/', include(esg_urls.api_urlpatterns)),
]
