from django.conf import settings
from django.urls import re_path, path

from monitor import views

# 为了符合swagger的展示方便，强烈建议在同一app内使用相同前缀
api_urlpatterns = [
    # 自定义钉钉机器人(运维告警)
    re_path(r"robot/send$", view=views.DDCustomRobotWebhookApi.as_view(), name="dd_custom_robot_send_api"),
]

view_urlpatterns = [
    re_path(r"celery/flower$", view=views.FlowerView.as_view(), name="monitor_flower"),
    re_path(r"inner/404$", view=views.Inner404View.as_view(), name="monitor_inner_404"),
    re_path(r"devops/notification$", view=views.DevOpsNotificationView.as_view(), name="dd_devops_notify_view"),

    re_path(r"error/(?P<error_code>\d+)$", view=views.ErrorPageView.as_view(), name="inner_4xx_5xx_page"),
]
