from django.urls import re_path, path

from . import views

# 为了符合swagger的展示方便，强烈建议在同一app内使用相同前缀
api_urlpatterns = [
    re_path(r"^health/check", view=views.HealthCheckApi.as_view(), name="health_check"),     # 健康检查

    # crontab 表达式解析
    re_path(r"^cron/parse$", view=views.CronParseApi.as_view(), name="cron_parser"),

    # PDF 转 Image
    re_path(r"^pdf2image$", view=views.PDF2ImageApi.as_view(), name="pdf2image_api"),
]

view_urlpatterns = [
    path(r"file/export/test", view=views.FileExportTestApi.as_view(), name="file_export_test"),
    path(r"kpi/download", view=views.DownloadKPIView.as_view(), name="kpi_download"),
    path(r"tag/topic/download", view=views.DownloadTagTopicView.as_view(), name="tag_topic_download"),
    path(r"download/state", view=views.StateDownloadView.as_view(), name="download_state"),
    re_path(r"^survey/download$", view=views.SurveyDownloadView.as_view(), name="survey_download"),
    re_path(r"^survey/download/state$", view=views.StateSurveyDownloadApi.as_view(), name="survey_download_state"),
]
