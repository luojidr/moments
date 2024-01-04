from django.urls import re_path
from . import views

view_urlpatterns = [
    re_path("^group/list$", view=views.GroupView.as_view(), name="permissions_group_view"),
    re_path("^menu/list$", view=views.MenuView.as_view(), name="permissions_menu_view"),

    re_path("^invoker/client/list$", view=views.ApiInvokerClientView.as_view(), name="permissions_invoker_client_view"),

    re_path(r"^invoker/urls/list", view=views.ApiInvokerPathView.as_view(), name='permissions_invoker_path_view'),
]

api_urlpatterns = [
    re_path("^menu/tree$", view=views.MenuTreeApi.as_view(), name="permissions_menu_tree"),
    re_path("^menu/app/select$", view=views.MenuAppSelectApi.as_view(), name="permissions_menu_app_select"),
    re_path("^menu/order/select$", view=views.MenuOrderSelectApi.as_view(), name="permissions_menu_order_select"),
    re_path("^group/list$", view=views.ListGroupApi.as_view(), name="permissions_group_list"),
    re_path("^group/operate$", view=views.OperateGroupApi.as_view(), name="permissions_group_operate"),

    re_path("^menu/list$", view=views.ListMenuApi.as_view(), name="permissions_menu_list_api"),
    re_path("^menu/operate$", view=views.OperateMenuApi.as_view(), name="permissions_menu_operate_api"),

    re_path(
        "^invoker/client/list$",
        view=views.ListInvokerClientApi.as_view(),
        name="permissions_invoker_client_list_api"
    ),

    re_path(
        "^invoker/client/opreate$",
        view=views.OperateInvokerClientApi.as_view(),
        name="permissions_invoker_client_operate_api"
    ),

    re_path(
        "^invoker/url/list$",
        view=views.ListInvokerUrlApi.as_view(),
        name="permissions_invoker_client_list_api"
    ),

    re_path(
        r"^invoker/url/opreate$",
        view=views.OperateInvokerPathApi.as_view(),
        name='permissions_invoker_path_operate_api'
    ),
]

token_api_urlpatterns = [
    re_path("^gettoken$", view=views.AccessTokenInvokerClientApi.as_view(), name="gettoken_api"),
]


