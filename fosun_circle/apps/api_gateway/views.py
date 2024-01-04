from rest_framework.views import APIView
from rest_framework.response import Response

from fosun_circle.libs.log import dj_logger
from .service import FosunlinkService


class FosunlinkGatewayApi(APIView):
    def get(self, request, *args, **kwargs):
        path = kwargs.get('path')
        query_params = request.query_params
        dj_logger.info('FosunlinkGatewayApi => kwargs: %s, query_params: %s', kwargs, query_params)

        data = FosunlinkService.get_result(path, query_params=query_params)
        return Response(data=data)

