import json
import base64
import traceback

import requests

from config.conf.dingtalk import DingTalkConfig
from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.libs.token_helpers import TokenHelper


class SurveyVoteService:
    SURVEY_SAVE_API = '/fosun/v1.0/fosun_vote/survey/answer/save'
    SURVEY_DETAIL_API = "/fosun/v1.0/fosun_vote/survey/detail"
    SURVEY_LIST_API = "/fosun/v1.0/fosun_vote/survey/list"
    SURVEY_RESULT_API = "/fosun/v1.0/fosun_vote/survey/statistics/result"
    QUERY_SQL_API = "/fosun/v1.0/fosun_vote/survey/raw_data"

    def __init__(self, ticket=None, app_scope=None):
        self._helper = TokenHelper(ticket, app_scope)

    def _get_data_by_ihcm(self, url, params=None, body=None, method="GET"):
        assert method in ["GET", "POST"], "Api 方法错误."

        data = None
        survey_host = DingTalkConfig.IHCM_SURVEY_HOST
        survey_api = survey_host + url
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
        }

        tokens = dict(self._helper.get_token(), )

        try:
            if method == "GET":
                params = dict(params or {}, **tokens)
                'mobile' not in params and params.update(mobile=self._helper.api_ticket)
                resp = requests.get(survey_api, params=params, headers=headers)

                logger.info("Odoo survey GET url:%s, params:%s\nText:%s", survey_api, params, resp.text)
                result = resp.json().get("data", {})
            else:
                body = dict(body or {}, **tokens)
                'mobile' not in body and body.update(mobile=self._helper.api_ticket)
                headers.update({"Content-Type": "application/json"})

                resp = requests.post(survey_api, params=params, data=json.dumps(body), headers=headers)
                logger.info("Odoo survey POST url:%s, data:%s\nText:%s", survey_api, body, resp.text)
                result = resp.json().get("result", {})

            code = result.get("code")
            status_code = resp.status_code

            if status_code == 200 and code == 200:
                data = result.get("data")
            else:
                data = result
        except Exception as e:
            logger.error(traceback.format_exc())

        return data

    def get_survey_list(self, query_params, ding_survey_ids=(), auth_user=None):
        """ ihcm 问卷列表

        :param query_params:    dict, query parameters
        :param ding_survey_ids: list, filtering survey id, get all survey for empty
        :param auth_user: permission to get survey for which users

        :return: dict, survey list
        """
        ding_survey_ids = ding_survey_ids or []
        params = dict(
            page=query_params.get("page", 1), size=query_params.get("size", 10),
            keyword=query_params.get("keyword"), state=query_params.get("state") or "",
        )

        survey_result = self._get_data_by_ihcm(
            self.SURVEY_LIST_API,
            params=params, body=dict(survey_ids=ding_survey_ids), method="POST"
        ) or {}

        return dict(count=survey_result.pop("count", 0), list=survey_result.pop("list", []))

    def get_survey_list_by_auth(self, survey_list, auth_user=None, login_mobile=""):
        if not auth_user:
            return []

        if auth_user.is_superuser:
            survey_list = survey_list
        elif auth_user.is_vote_admin:
            survey_list = [_item for _item in survey_list if _item["creator"] == login_mobile]
        else:
            survey_list = []

        return survey_list

    def get_survey_statistics_result(self, survey_id):
        return self._get_data_by_ihcm(
            self.SURVEY_RESULT_API,
            params=dict(questionnaire_id=survey_id)
        ) or {}

    def get_survey_detail(self, survey_id, mobile=None):
        return self._get_data_by_ihcm(
            self.SURVEY_DETAIL_API,
            params=dict(mobile=mobile, questionnaire_id=survey_id)
        ) or {}

    def save_survey_detail(self, mobile, survey_data):
        return self._get_data_by_ihcm(
            self.SURVEY_SAVE_API,
            params=dict(mobile=mobile),
            body=survey_data, method="POST"
        ) or {}

    def get_sql_results(self, sql):
        sql_list = sql if isinstance(sql, (list, tuple)) else [sql]
        dump = json.dumps(sql_list).encode("utf-8")

        data = self._get_data_by_ihcm(
            self.QUERY_SQL_API,
            body=dict(raws=base64.b64encode(dump).decode("u8")),
            method="POST"
        ) or []

        if not data:
            return []

        if len(sql_list) == 1:
            return data[0]["list"]

        return data
