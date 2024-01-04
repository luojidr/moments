import json
from nameko.web.handlers import http


class HttpServer:
    name = "http_server"

    @http("GET", "/get/<int:value>")
    def get_method(self, request, value):
        obj = {'value': value}
        return json.dumps(obj)

    @http('POST', '/post')
    def post_method(self, request):
        data = request.get_data(as_text=True)
        return u"received: {}".format(data)