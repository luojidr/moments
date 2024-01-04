from django.conf import settings
from django.urls import re_path, path

from ding_talk import views

# 为了符合swagger的展示方便，强烈建议在同一app内使用相同前缀
api_urlpatterns = [
    # 通过 DingCode 获取用户jwt Token
    re_path("^user/by/code$", view=views.ObtainUserByCodeApi.as_view(), name="get_user_by_code_api"),

    # 钉钉所有应用 token 信息列表
    path(r"apps/list", view=views.ListDingAppTokenApi.as_view(), name="ding_app_token_list"),

    # 根据 id, 获取钉钉具体应用 token 信息
    re_path(r"^apps/(?P<pk>\d+)$", view=views.RetrieveDingAppTokenApi.as_view(), name="ding_app_token_id"),

    # 根据 agent_id, 获取钉钉具体应用 token 信息
    re_path(r"^apps/agent_id/(?P<agent_id>\d+)$", view=views.RetrieveDingAppTokenByAgentIdApi.as_view(), name="ding_app_token_agent_id"),

    # 添加钉钉应用 token 信息
    path(r"apps/token/add", view=views.CreateDingAppTokenApi.as_view(), name="ding_app_token_add"),

    # 发送钉钉应用消息
    re_path(r"apps/message/send$", view=views.SendDingAppMessageApi.as_view(), name="ding_app_msg_send"),

    # 根据部门发送钉钉消息
    re_path(
        r"apps/message/send/by/department$",
        view=views.SendDingMessageByDepartmentApi.as_view(), name="ding_app_msg_send_by_department"
    ),

    # 获取微应用消息推送列表
    re_path(r"apps/message/list$", view=views.ListDingPushMsgLogApi.as_view(), name="ding_app_msg_list"),

    # Ding Media 文件保存
    re_path(r"apps/message/media/upload$", view=views.UploadDingMessageMediaApi.as_view(), name="ding_msg_media_upload"),

    re_path(r"apps/message/media/success$", view=views.SuccessDingMessageMediaApi.as_view(), name="ding_msg_media_success"),

    re_path(r"apps/message/media/list$", view=views.ListDingMessageMediaApi.as_view(), name="ding_msg_media_list"),

    # 获取消息推送详情
    re_path(r"apps/message/(?P<pk>\d+)/detail$", view=views.DetailDingPushMsgLogApi.as_view(), name="ding_app_msg_list"),

    # 撤回已发送的钉钉消息
    re_path(r"apps/message/recall$", view=views.RecallDingAppMsgTaskApi.as_view(), name="ding_app_msg_recall"),

    # 二次提醒钉钉消息
    re_path("apps/message/again/alert$", view=views.AlertAgainDingAppMsgApi.as_view(), name="ding_msg_alert_or_bulk_again"),

    # 钉钉消息详情
    re_path("apps/message/detail$", view=views.DetailDingAppMsgApi.as_view(), name="ding_msg_detail"),

    # Ihcm 问卷列表
    re_path("apps/survey/list$", view=views.ListIhcmSurveyApi.as_view(), name="apps_survey_list"),

    # 话题列表
    re_path("apps/topic/list$", view=views.ListCircleTopicApi.as_view(), name="apps_topic_list"),

    # 推送消息表单查询数据
    re_path("apps/message/form$", view=views.FormDataMessageApi.as_view(), name="apps_message_form"),

    # xlsx批量手机号
    re_path("apps/message/batch_mobiles/upload", view=views.BatchMobileExcelUploadApi.as_view(), name="batch_mobiles_upload"),

    # 钉钉消息回撤(列表与撤回接口)
    re_path(r"apps/message/recall/log$", view=views.RecallMsgLogApi.as_view(), name="recall_msg_log"),

    # 钉钉消息主体列表
    re_path(r"apps/message/info/list$", view=views.ListDingMessageInfoApi.as_view(), name="message_info_list"),

    # 动态管理定时任务(Api)
    re_path(r"apps/message/periodic/task/operate$", view=views.OperatePeriodicTaskApi.as_view(), name="periodic_task_operate"),

    # 获取部门下拉菜单
    re_path(r"apps/department/select/list$", view=views.SelectDepartmentApi.as_view(), name="select_department_menu"),

    # 管理消息体
    re_path(r"apps/message/info/operate$", view=views.OperateMessageInfoApi.as_view(), name="message_operate"),
]

view_urlpatterns = [
    re_path(r"message/create$", view=views.CreateDingMessageView.as_view(), name="ding_message_create"),
    re_path(r"message/list$", view=views.ListDingMessageLogView.as_view(), name="ding_message_list"),
    re_path(r"message/media$", view=views.ListDingMessageMediaView.as_view(), name="ding_message_media"),
    re_path(r"message/recall/log$", view=views.RecallMsgLogView.as_view(), name="ding_recall_log_list"),

    # 动态管理定时任务(View)
    re_path(r"message/periodic/task/add$", view=views.AddPeriodicTaskView.as_view(), name="ding_periodic_task_add"),
    re_path(r"message/periodic/task/list$", view=views.ListPeriodicTaskView.as_view(), name="ding_periodic_task_list"),
    re_path(r"message/periodic/topic/add$", view=views.AddMessageInfoView.as_view(), name="ding_periodic_topic_add"),

]
