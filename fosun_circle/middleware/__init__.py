import types
import traceback

from django.urls import resolve
from django.core.exceptions import ValidationError


def get_request_view_class(request):
    callback = None
    resolver_match = request.resolver_match

    if resolver_match is None:
        resolver_match = resolve(request.path)

    try:
        callback = resolver_match.func
        view_class = callback.view_class    # 基于类视图: isinstance(callback, types.MethodType)
    except AttributeError:
        view_class = None                   # 基于函数视图: isinstance(callback, types.FunctionType)
        traceback.format_exc()

    if isinstance(callback, types.MethodType) and view_class is None:
        raise ValidationError("request<%s> haven't view class" % request)
    elif isinstance(callback, types.FunctionType):
        view_class = resolver_match.func

    return view_class
