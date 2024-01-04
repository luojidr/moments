import os.path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

import asyncio
from asgiref.sync import async_to_sync, sync_to_async
from functools import wraps
from script.t_dj_core.t_middleware.middleware import AMiddleware, BMiddleware, CMiddleware


def response_for_exception(request, exc):
    print(request, exc)


def call_response(*args, **kwargs):
    print("Now call call_response")
    return "AAA"


def convert_exception_to_response(get_response):
    if asyncio.iscoroutinefunction(get_response):
        @wraps(get_response)
        async def inner(request):
            try:
                response = await get_response(request)
            except Exception as exc:
                response = await sync_to_async(response_for_exception, thread_sensitive=False)(request, exc)
            return response
        return inner
    else:
        @wraps(get_response)
        def inner(request):
            try:
                response = get_response(request)
            except Exception as exc:
                response = response_for_exception(request, exc)
            return response
        return inner


def load_middleware():
    handler = convert_exception_to_response(call_response)
    middleware_list = [AMiddleware, BMiddleware, CMiddleware][::-1]

    for _middleware in middleware_list:
        try:
            print("1 => handler:", handler)
            adapted_handler = handler
            print("2 => adapted_handler:", adapted_handler)
            mw_instance = _middleware(adapted_handler)
        except:
            print("Error")
        else:
            handler = adapted_handler
            print("3 => handler:", handler)

        handler = convert_exception_to_response(mw_instance)
        print("4 => handler:", handler)
        print("\n")

    print("5 => handler:", handler)
    _middleware_chain = handler

    return _middleware_chain


if __name__ == "__main__":
    request = "REQUEST"
    middleware_chain = load_middleware()
    resp = middleware_chain(request)

    print(resp)
