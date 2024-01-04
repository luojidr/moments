from django.urls import re_path
from werobot.contrib.django import make_view

from wechatBot.utils.wechatBot import robot

# 为了符合swagger的展示方便，强烈建议在同一app内使用相同前缀
api_urlpatterns = [
    re_path(r"robot/$", view=make_view(robot), name="wechat_robot"),
]

view_urlpatterns = [

]
