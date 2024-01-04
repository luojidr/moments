from django.urls import re_path, path

from . import views

# 为了符合swagger的展示方便，强烈建议在同一app内使用相同前缀
urlpatterns = []

api_urlpatterns = [
    # 星圈帖子点赞或评论的推送
    # HR知乎等等消息推送
    path(r"message/action/log/notify", view=views.CircleActionLogApi.as_view(), name="circle_action_log_add"),

    # 2022年员工年度总结
    path(r'annual/summary', view=views.CircleAnnualSummaryApi.as_view(), name='circle_annual_summary'),

    # bbs 用户搜索(发帖时搜索)
    re_path(r'bbs/user/search', view=views.BbsFuzzySearchUserApi.as_view(), name='bbs_fuzzy_user_search'),

    # 话题标签列表（抽奖使用）
    re_path("^tag/list$", view=views.ListCircleTagLotteryApi.as_view(), name="tag_list_lottery_api"),

    # 话题标签（列表、添加）
    re_path("^bbs/tag$", view=views.CircleTagApi.as_view(), name="esg_tag_api"),

    # 用户搜索（普通关键字搜索）
    re_path(r'^bbs/user/query$', view=views.ListCircleUserApi.as_view(), name='bbs_fuzzy_user_query'),

    # 管理后台或ESG API查询
    re_path(r"^bbs/list$", view=views.ListCircleApi.as_view(), name='bbs_circle_list_api'),
    re_path(r"^bbs/detail$", view=views.DetailCircleApi.as_view(), name='bbs_circle_detail_api'),

    # 帖子对应的评论
    re_path(
        r"^bbs/comment_of_posted/list$",
        view=views.ListCommentOfCircleApi.as_view(),
        name='bbs_comment_of_circle_list_api'
    ),

    # BBS 用户Token API
    re_path(r"^user/bbs/gettoken$", view=views.UserXTokenApi.as_view(), name='bbs_user_token_api'),

    # 标签列表帖子置顶
    re_path(r"^bbs/tag/top/set$", view=views.SetCircleTopPageApi.as_view(), name="bbs_tag_circle_top_api"),

    # 隐藏或展示帖子状态
    re_path(r"^bbs/state/set$", view=views.SetCircleStateApi.as_view(), name="bbs_circle_state_api"),

    # 管理后台回复
    re_path(r"^bbs/comment/add$", view=views.CircleCommentApi.as_view(), name="bbs_circle_comment_api"),

    # BBS评论
    re_path(r"^bbs/comment/list$", view=views.ListCommentApi.as_view(), name='bbs_comment_list_api'),

    # 隐藏或展示评论状态
    re_path(r"^bbs/comment/state/set$", view=views.SetCommentStateApi.as_view(), name="bbs_comment_state_api"),

    # 话题标签列表
    re_path(r"^bbs/tag/list$", view=views.ListTagApi.as_view(), name="bbs_tag_list_api"),

    # 话题标签操作
    re_path(r"^bbs/tag/operate$", view=views.OperationTagApi.as_view(), name="bbs_tag_operation_api"),

    # BBS 埋点数据统计
    re_path(r"^bbs/event-tracking/dau/list$", view=views.ListCircleEventTrackingApi.as_view(), name='bbs_dau_list_api'),

    # 轮播图
    re_path(r"^bbs/slideshow$", view=views.CircleSlideshowApi.as_view(), name='bbs_slideshow_api'),
    re_path(r"^bbs/ddShare$", view=views.CircleDDShareApi.as_view(), name='bbs_ddShare_api'),
]

view_urlpatterns = [
    re_path(r"bbs/mgr$", view=views.CircleView.as_view(), name="bbs_circle_list_view"),
    re_path(r"bbs/comment/mgr$", view=views.CircleCommentView.as_view(), name="bbs_comment_list_view"),
    re_path(r"bbs/operations/mgr$", view=views.CircleOperationsView.as_view(), name="bbs_operations_view"),

    # 轮播图
    re_path(r"bbs/slideshow/mgr$", view=views.CircleSlideshowView.as_view(), name="bbs_slideshow_view"),
    # 钉钉分享（Card）
    re_path(r"bbs/ddShare/mgr$", view=views.CircleDDShareView.as_view(), name="bbs_ddShare_view"),
    # 标签管理
    re_path(r"bbs/tag/mgr$", view=views.TagView.as_view(), name="bbs_tag_view"),
]
