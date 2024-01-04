from django.urls import re_path, path

from . import views

api_urlpatterns = [
    re_path(r'fosunlink/(?P<path>.*?)$', view=views.FosunlinkGatewayApi.as_view(), name='fosunlink_gateway_api'),
]
