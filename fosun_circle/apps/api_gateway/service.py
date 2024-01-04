import json
from fosun_circle.libs.log import dj_logger
from fosun_circle.core.okhttp.http_util import HttpUtil

logger = dj_logger


class FosunlinkService:
    API_HOST = 'https://www.fosunlink.com'

    @staticmethod
    def get_result(path, query_params=None):
        track_api = FosunlinkService.API_HOST + '/api/' + path
        params = {k: query_params.get(k, '') for k in query_params or {}}
        resp = HttpUtil(track_api).get(params=params)
        logger.info("FosunlinkService => track_api: %s, params: %s", track_api, params)

        return resp.get('data', {})

