from django.urls import re_path, path

from . import views

# 为了符合swagger的展示方便，强烈建议在同一app内使用相同前缀
api_urlpatterns = [
    # 部门搜索列表
    re_path(r"^department/list$", view=views.ListDepartmentApi.as_view(), name="esg_dep_list_api"),

    # 入口部门列表
    re_path(r"^entry/department/list$", view=views.ListEntryDepartmentApi.as_view(), name="esg_entry_dep_list_api"),

    # 用户入口权限
    re_path(r"^entry/user/permission$", view=views.EntryUserPermissionApi.as_view(), name="esg_entry_user_permission_api"),

    # 添加或修改入口部门
    re_path(r"^entry/department/operate$", view=views.OperateEntryDepartmentApi.as_view(), name='esg_create_update_dep_api'),

    # ESG用户权限
    re_path(r"^user/admin/list$", view=views.ListUserAdminApi.as_view(), name='esg_user_admin_api'),
    re_path(r"^user/admin/operate$", view=views.OperateUserAdminApi.as_view(), name='esg_user_admin_operate_api'),

    # Esg动作场景(包括对外接口)
    re_path(r"^task/action/list$", view=views.ListTaskActionApi.as_view(), name='esg_task_action_list_api'),

    # Esg动作场景管理
    re_path(r"^task/action/operate$", view=views.OperateTaskActionApi.as_view(), name='esg_task_action_operate_api'),

    # ESG 发帖页面的Tips（标签、placeholder）
    re_path(r"^task/action/tips$", view=views.TaskActionTipsApi.as_view(), name="esg_task_action_esg_api"),

    # ESG 发帖后将发帖数据回调给ESG后台
    re_path(r"^posted/callback$", view=views.CallbackAfterPostedApi.as_view(), name="esg_callback_after_posted"),
]

view_urlpatterns = [
    re_path(r"^user/admin$", view=views.UserAdminView.as_view(), name="esg_user_admin_view"),
    re_path(r"^entry/department/list$", view=views.EntryDepartmentView.as_view(), name="esg_entry_department_view"),
    re_path(r"^task/action/list$", view=views.TaskActionView.as_view(), name="esg_task_action_list_view"),
    re_path(r"bbs/mgr$", view=views.CircleEsgView.as_view(), name="bbs_circle_esg_list_view"),
]
