import json
import os.path
import logging
import traceback
from typing import List

import requests
from django.conf import settings
from django.utils import timezone
from django.db import connections, connection

from rest_framework import status

logger = logging.getLogger('django')


class ESGService:
    ESG_SCHEMA = os.getenv("ESG_SCHEMA")
    ESG_HOST = os.getenv("ESG_HOST")
    ESG_CALLBACK_AFTER_POSTED_API = 'esg/miniapp/quest_record/StarPostingCallBack'

    def __init__(self):
        self._connection = connections['bbs_user']

    def _get_user_job_code(self, mobile):
        cursor = connection.cursor()
        sql = "SELECT ding_job_code FROM circle_users WHERE phone_number=%s LIMIT 1"
        cursor.execute(sql, params=(mobile, ))
        db_result = cursor.fetchone()

        return db_result[0] if db_result else ''

    def _get_circle_image_list(self, circle_id: int) -> List[str]:
        cursor = self._connection.cursor()
        sql = 'SELECT circle_id, url FROM "starCircle_circleimage" WHERE circle_id=%s ORDER BY id ASC'
        cursor.execute(sql, params=(circle_id, ))
        db_results = cursor.fetchall()

        return [item[1] for item in db_results if item[1]]

    def _get_circle_content(self, circle_id: int) -> str:
        cursor = self._connection.cursor()
        sql = 'SELECT content FROM "starCircle_starcircle" WHERE id=%s'
        cursor.execute(sql, params=(circle_id, ))
        db_result = cursor.fetchone()

        return db_result[0] if db_result else ''

    def invoke_callback_after_posted(self, mobile: str, circle_id: int, quest_id: int):
        headers = {'Content-Type': 'application/json'}
        url = '{schema}://{host}/{api}'.format(
            schema=self.ESG_SCHEMA,
            host=self.ESG_HOST,
            api=self.ESG_CALLBACK_AFTER_POSTED_API
        )
        data = dict(
            questId=int(quest_id or 0),
            jobCode=self._get_user_job_code(mobile),
            content=self._get_circle_content(circle_id),
            img=json.dumps(self._get_circle_image_list(circle_id)),
            createTime=(timezone.datetime.now() + timezone.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
        )
        logger.info('ESGService.invoke_callback_after_posted -> url: %s, data: %s', url, json.dumps(data, indent=4))

        try:
            r = requests.post(url, data=json.dumps(data), headers=headers)
            logger.info('ESGService.invoke_callback_after_posted -> status-code: %s, ret: %s', r.status_code, r.text)

            r_data = r.json()
            http_200 = status.HTTP_200_OK

            if r.status_code == http_200 and r_data.get('code') in [http_200, status.HTTP_201_CREATED]:
                return dict(is_ok=True, msg='ok')

            msg = "ESG接口回调信息: %s" % (r_data.get('msg') or "")
        except Exception as e:
            msg = str(e)
            logger.error('ESGService.invoke_callback_after_posted -> callback error: %s', e)
            logger.error(traceback.format_exc())

        return dict(is_ok=False, msg=msg)
