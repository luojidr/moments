from django.urls import re_path, path
from . import views

view_urlpatterns = [
    path("list", view=views.ListLotteryActivityView.as_view(), name='lottery_activity_view_list'),
    path("detail", view=views.DetailLotteryActivityView.as_view(), name='lottery_activity_view_detail'),
]

api_urlpatterns = [
    # 抽奖活动列表
    re_path("^activity/list$", view=views.ListLotteryActivityApi.as_view(), name="lottery_activity_list"),
    re_path("^activity/detail$", view=views.LotteryActivityApi.as_view(), name="lottery_activity_detail"),
    re_path("^activity/operate$", view=views.CreateUpdateLotteryActivityApi.as_view(), name="lottery_activity_operate"),

    re_path("^participant/list$", view=views.ListLotteryParticipantApi.as_view(), name="lottery_participant_list"),
    re_path("^award/list$", view=views.ListLotteryAwardApi.as_view(), name="lottery_award_list"),
    re_path("^award/create$", view=views.CreateLotteryAwardApi.as_view(), name="lottery_award_create"),
    re_path("^lucky/win$", view=views.LuckyWinLotteryApi.as_view(), name="lottery_lucky_win"),
    re_path("^lucky/message/operate", view=views.LuckyPushLotteryApi.as_view(), name="lottery_lucky_msg_operate"),

    # 抽奖消息H5接口
    re_path("^lucky/winner/detail", view=views.LuckyWinnerDetailLotteryApi.as_view(), name="lottery_win_h5"),
]
