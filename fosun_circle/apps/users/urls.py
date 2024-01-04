from django.urls import re_path, path
from . import views


# 为了符合swagger的展示方便，强烈建议在同一app内使用相同前缀
view_urlpatterns = [
    path("index/", view=views.IndexView.as_view(), name="index"),
    path("login/", view=views.LoginView.as_view(), name="login"),
    path("register/", view=views.RegisterView.as_view(), name="register"),
    path("logout/", view=views.LogoutView.as_view(), name="logout"),
]

api_urlpatterns = [
    # 验证码
    path(r"users/sms/code", view=views.UserSmsCodeApi.as_view(), name="user_login_sms"),

    # csrf token
    path(r"users/csrf/token", view=views.CsrfTokenApi.as_view(), name="user_csrf_token"),

    # UUC User
    re_path(r"^users/uuc/employee/detail$", view=views.DingEmployeeApi.as_view(), name='user_uuc_employee'),

    # Ding User API
    re_path(r"^users/ding/getinfo$", view=views.DingDingUserApi.as_view(), name='user_dd_user_api'),

    # 搜索用户
    path(r"users/fuzzy/retrieve", view=views.ListFuzzyRetrieveUserApi.as_view(), name="fuzzy_query_users"),

    # 部门树
    path(r"department/tree", view=views.DepartmentRetrieveApi.as_view(), name="department_tree"),

    # mail code
    path(r"users/mail/code/check", view=views.SendEmailCodeApi.as_view(), name="mail_code"),

    # rest password
    path(r"users/reset/password", view=views.ResetPasswordApi.as_view(), name="reset_password"),

    # Two factor auth
    re_path(r"^users/2fa$", view=views.TwoFactorAuthenticationApi.as_view(), name="two_factor_auth_api"),

    # Confirm two factor
    re_path(r"users/auth/2fa/check$", view=views.ConfirmTwoFactorApi.as_view(), name="confirm_2fa"),

    # App 首页权限接口
    re_path(r"users/permission$", view=views.UserPermissionApi.as_view(), name="user_permission_api"),
]
