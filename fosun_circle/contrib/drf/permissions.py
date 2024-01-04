import logging

from django.urls import resolve
from rest_framework import permissions
from rest_framework import exceptions

from rest_framework import authentication
from rest_framework_jwt import authentication

from fosun_circle.middleware import get_request_view_class

logger = logging.getLogger("django")


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    自定义权限只允许对象的所有者编辑它。
    """
    def get_auth_exempt(self, request):
        request = request or self.request
        view_cls = get_request_view_class(request=request)

        return getattr(view_cls, "AUTH_EXEMPT", False)

    def has_permission(self, request, view):
        """ request 基本权限校验 """
        auth_exempt = self.get_auth_exempt(request)

        if auth_exempt:
            logger.info("IsOwnerOrReadOnly.has_permission: View<%s> 已豁免认证<AUTH_EXEMPT>" % self.__class__)
            return True

        token = request.COOKIES.get("X-Auth") or request.headers.get("X-Auth")
        if token is None:
            raise exceptions.PermissionDenied("你没有权限访问此接口, X-Auth为空")

        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # 读取权限允许任何请求，
        # 所以我们总是允许GET，HEAD或OPTIONS请求。
        if request.method in permissions.SAFE_METHODS:
            return True

        # 只有该snippet的所有者才允许写权限。
        return obj.owner == request.user
