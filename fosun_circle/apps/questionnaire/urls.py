from django.urls import re_path, path
from . import views

view_urlpatterns = [
    re_path("manage$", view=views.CreateQuestionnaireSurveyView.as_view(), name="survey_view_create"),
    re_path("list$", view=views.ListQuestionnaireSurveyView.as_view(), name="survey_view_list"),
    re_path("ding/push$", view=views.DingPushQuestionnaireSurveyView.as_view(), name="survey_ding_push"),
]

api_urlpatterns = [
    # 同步问卷(Ihcm至星圈)
    re_path(r"^survey/sync$", view=views.SyncSurveyVoteApi.as_view(), name="circle_survey_sync"),

    # 问卷列表(星圈)
    re_path("^survey/list$", view=views.ListQuestionnaireSurveyApi.as_view(), name="circle_survey_list"),

    # 修改问卷(星圈)
    re_path("^survey/update$", view=views.UpdateQuestionnaireSurveyApi.as_view(), name="circle_survey_update"),

    # 问卷统计分析(Odoo)
    re_path("^statistics/result$", view=views.StatisticsResultSurveyAPi.as_view(), name="survey_statistics_result"),

    # 问卷列表(Odoo)
    re_path("^vote/list$", view=views.ListSurveyVoteAPi.as_view(), name="survey_vote_list"),

    # 问卷投票等是否完成
    re_path(r"^vote/done$", view=views.DoneSurveyVoteApi.as_view(), name="survey_vote_done"),

    # 问卷详情(Odoo)
    re_path(r"^vote/detail$", view=views.DetailSurveyVoteApi.as_view(), name="survey_vote_detail"),
    re_path(r"^vote/save$", view=views.CreateSurveyVoteApi.as_view(), name="survey_vote_save"),

    re_path("question/image/upload$", view=views.UploadQuestionImageApi.as_view(), name="survey_media_upload"),
    re_path("save$", view=views.SaveQuestionnaireApi.as_view(), name="survey_save"),
    re_path("list$", view=views.ListQuestionnaireApi.as_view(), name="survey_list"),
    re_path("detail$", view=views.DetailQuestionnaireApi.as_view(), name="survey_detail"),
]
