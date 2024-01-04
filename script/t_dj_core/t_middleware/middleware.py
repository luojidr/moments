from django.utils.deprecation import MiddlewareMixin

"""
(1): 一个请求 request 会经过如下流程(程序没有任何错误的情况)
    process_request(不会返回response) -> process_view(不会返回response) -> view(返回response) -> 
    process_template_response(没有exc) -> process_response
    
(2): 如果 process_view 有 raise exc
    当前的 process_request(无exc, 不会返回response) -> 当前的 process_response
    
(3): 如果 view 有 raise exc
    process_request(无exc, 不会返回response) -> process_view(无exc, 不会返回response) -> view(有exc) -> 
    process_exception(无exc) -> process_template_response(无exc) -> process_response
    
(4): 如果 process_template_response 有 raise exc
    process_request(无exc, 不会返回response) -> process_view(无exc, 不会返回response) -> view(无exc, 返回response) -> 
    process_template_response(有exc) -> process_exception(无exc)  -> process_response
    
(4): 如果单纯的 process_exception 有 raise exc, 不会有任何影响
"""


class AMiddleware(MiddlewareMixin):
    def process_request(self, request):
        print("A process_request")

    def process_response(self, request, response):
        print("A process_response")
        return response


class BMiddleware(MiddlewareMixin):
    def process_request(self, request):
        print("B process_request")

    def process_response(self, request, response):
        print("B process_response")
        return response


class CMiddleware(MiddlewareMixin):
    def process_request(self, request):
        print("C process_request")

    def process_response(self, request, response):
        print("C process_response")
        return response

