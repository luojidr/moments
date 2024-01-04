import datetime
import os.path
import traceback
import typing

from django.db import connections, transaction
from rest_framework.response import Response

from fosun_circle.libs.log import dj_logger as logger


class CircleBBSService:
    PDF = 'pdf'
    TEXT = 'text'
    IMAGE = 'image'
    VIDEO = 'video'

    PDF_SUFFIX_LIST = [".pdf", ]
    IMAGE_SUFFIX_LIST = [".jpg", ".jpeg", ".png", ".svg", ".blob"]
    VIDEO_SUFFIX_LIST = [".mp4", ".avi", ".wmv", ".mpg", ".mpeg", ".mov", ".rm", ".ram"]

    def __init__(self, request, is_esg=False):
        self._request = request
        self._is_esg = is_esg
        self._connection = connections['bbs_user']

    @property
    def query_params(self):
        return getattr(self._request, "query_params", self._request.GET)

    @property
    def has_esg(self):
        if self._is_esg:
            return self._is_esg

        query_params = self.query_params
        wsgi_request = getattr(self._request, "_request", self._request)

        is_esg = query_params.get('is_esg')
        if is_esg in ['0', 'false']:
            is_esg = False
        elif is_esg in ['1', 'true']:
            is_esg = True
        else:
            assert not is_esg, "is_esg parameter is error!"

            api_invoker = getattr(wsgi_request, "api_invoker", None)
            is_esg = 'esg' in (api_invoker.name or '').lower() if api_invoker else False

        return is_esg

    def get_query_params(self):
        query_params = self.query_params

        is_esg = self.has_esg
        content = query_params.get('content')
        user_id = int(query_params.get('user_id') or 0)
        page = int(query_params.get('page') or 1)
        page_size = int(query_params.get('page_size') or 10)

        visible_range = query_params.get('visible_range', 'common')
        sorted_field = query_params.get('sorted_field', 'created_time')

        circle_ids = []
        circle_id = int(query_params.get('circle_id') or 0)
        circle_id and circle_ids.append(circle_id)

        tag_id = int(query_params.get('tag_id') or 0)
        if tag_id:
            sql = 'SELECT circle_id FROM "starCircle_circle2tag" WHERE tag_id=%s' % tag_id
            circle_ids.extend([item[0] for item in self._get_sql_results(sql)])

        params = dict(
            content=content, circle_ids=circle_ids, user_id=user_id,
            sorted_field=sorted_field, visible_range=visible_range,
            is_esg=is_esg, page=page, page_size=page_size
        )
        extra_params = {k: query_params[k] for k in query_params if k not in params}
        return dict(params, **extra_params)

    def _get_string_by_list(self, column_list):
        str_list = [isinstance(s, (str, bytes)) and s or str(s) for s in column_list]
        return ", ".join(str_list)

    def _get_sql_results(self, sql, fields=None, alias=None):
        if alias is None:
            conn = self._connection
        else:
            conn = connections[alias]

        cursor = conn.cursor()
        cursor.execute(sql)
        db_results = cursor.fetchall()

        if not fields:
            return db_results

        if db_results and len(db_results[0]) != len(fields):
            raise ValueError("fields字段数与SQL返回结果的列数不一致")

        return [dict(zip(fields, item)) for item in db_results]

    def _execute_sql(self, sql):
        cursor = self._connection.cursor()
        cursor.execute(sql)
        self._connection.commit()

    def _get_post_screen_type(self, image_list):
        post_type, screen_style = self.TEXT, None

        for img in image_list:
            _, ext = os.path.splitext(img["url"])
            ext = ext.lower()

            if ext in self.IMAGE_SUFFIX_LIST:
                post_type = self.IMAGE
            elif ext in self.VIDEO_SUFFIX_LIST:
                post_type = self.VIDEO
            elif ext in self.PDF_SUFFIX_LIST:
                post_type = self.PDF

        if post_type == self.VIDEO:
            url = image_list[0]["url"]
            filename, _ = os.path.splitext(os.path.basename(url))

            style = filename.split("_")[-1]
            screen_style = style if style in ["landscape", "vertical"] else None

        return post_type, screen_style

    def _get_user_mapping(self, user_ids):
        if not user_ids:
            return []

        fields = ['id', 'fullname', 'avatar', 'real_avatar', 'position_chz']
        sql = """
            SELECT id, fullname, avatar, real_avatar, "positionCh"
            FROM users_userinfo 
            WHERE  id IN (%s)
        """ % self._get_string_by_list(user_ids)

        db_results = self._get_sql_results(sql, fields=fields)
        return {item['id']: item for item in db_results}

    def _get_circle_data_from_db(
            self,
            content=None, circle_ids=None,
            visible_range=None, is_count=True, paginate=True):
        query_params = self.get_query_params()

        fields = [
            'id', 'created_time', 'content', 'comment_cnt', 'up_cnt', 'is_esg', 'is_show',
            'user_id', 'frame_img_url', 'is_actual', 'is_tag_page_top', 'visible_range'
        ]
        sql = """
            SELECT 
                id, created_time, content, "commentCount", "upCount",  is_esg, is_show,
                user_id, frame_img_url, is_actual, is_tag_page_top, visible_range
            FROM "starCircle_starcircle" 
        """
        where = "WHERE is_delete=false"

        content = content or query_params.get('content')
        if content:
            where += " AND content like '%%%s%%' " % content

        if query_params.get('user_id'):
            where += " AND user_id=%s " % query_params['user_id']

        circle_ids = circle_ids or query_params.get('circle_ids')
        if circle_ids:
            where += " AND id IN (%s) " % self._get_string_by_list(circle_ids)

        # ESG发帖单独逻辑
        if query_params.get('is_esg'):
            where += " AND is_esg=true"
        else:
            where += " AND is_esg=false"
            visible_range = query_params.get('visible_range') if visible_range is None else visible_range
            if visible_range:
                where += " AND visible_range='%s'" % visible_range

        # 置顶帖
        is_tag_page_top = query_params.get('is_tag_page_top')
        if (isinstance(is_tag_page_top, bool) and is_tag_page_top) or is_tag_page_top == 'true':
            where += ' AND is_tag_page_top=true '

        # 排序
        order_by = ''
        if query_params.get('sorted_field'):
            sorted_field = query_params['sorted_field']
            has_upper = any([c.isupper() for c in sorted_field])
            sorted_field = '"%s"' % sorted_field if has_upper else sorted_field
            order_by += ' ORDER BY %s DESC ' % sorted_field

        page_size = query_params['page_size']
        offset = (query_params['page'] - 1) * page_size

        if paginate:
            sql += where + order_by + " OFFSET %s LIMIT %s" % (offset, page_size)

        circle_list = self._get_sql_results(sql, fields=fields)

        if is_count:
            db_results = self._get_sql_results('SELECT COUNT(1) FROM "starCircle_starcircle" ' + where)
            total_count = db_results[0][0] if db_results else 0
        else:
            total_count = 0

        return dict(circle_list=circle_list, total_count=total_count)

    def _get_comment_data_from_db(
            self,
            is_circle=True, content=None, circle_ids=None,
            ids=None, is_esg=None, count=False, paginate=False):
        ids = [s for s in ids or [] if s]
        circle_ids = [s for s in circle_ids or [] if s]

        # is_circle: 默认根据发帖获取评论，否则不必依赖发帖直接获取相关评论
        if is_circle and not circle_ids and not ids:
            return dict(comment_list=[], total_count=0)

        where = ' WHERE is_delete=false '
        if circle_ids:
            where += "  AND circle_id IN (%s) " % self._get_string_by_list(circle_ids)

        if is_esg is not None:
            esg_bool = is_esg and 'true' or 'false'
            where += ' AND EXISTS (SELECT tbb.id FROM "starCircle_starcircle" tbb ' \
                     ' WHERE tbb.is_esg=%s AND tbb.id=tba.circle_id)' % esg_bool

        if ids:
            where += "  AND nid IN (%s) " % self._get_string_by_list(ids)

        if content:
            where += "  AND content like '%%%s%%' " % content

        db_results = self._get_sql_results('SELECT COUNT(1) FROM "starCircle_circlecomment" tba ' + where)
        total_count = db_results[0][0] if db_results else 0

        if count:
            fields = ['circle_id', 'cnt']
            sql = 'SELECT circle_id, COUNT(circle_id) FROM "starCircle_circlecomment" '
            where += ' GROUP BY circle_id'
        else:
            fields = ['nid', 'created_time', 'content', 'circle_id', 'is_show',
                      'user_id', "up_cnt", 'is_actual', 'parent_comment_id']
            sql = 'SELECT ' \
                  'nid, created_time, content, circle_id, is_show, user_id, "upCount", is_actual, "parentComment_id" ' \
                  'FROM "starCircle_circlecomment" tba '
            where += " ORDER BY created_time DESC "

            page = int(self.query_params.get('page', 1))
            page_size = int(self.query_params.get('page_size', 10))

            if paginate:
                where += ' OFFSET %s LIMIT %s ' % ((page - 1) * page_size, page_size)

        comment_list = self._get_sql_results(sql + where, fields=fields)
        return dict(comment_list=comment_list, total_count=total_count)

    def _get_image_mapping(self, circle_ids):
        if not circle_ids:
            return {}

        image_mapping = {}
        circle_ids_str = self._get_string_by_list(circle_ids)
        sql = 'SELECT id, url, circle_id FROM "starCircle_circleimage" WHERE circle_id IN (%s) ORDER BY id ASC'

        for item in self._get_sql_results(sql % circle_ids_str):
            url = item[1]
            circle_id = item[2]

            if url:
                image_mapping.setdefault(circle_id, []).append(dict(id=item[0], url=url))

        return image_mapping

    def _get_tag_mapping(self, circle_ids):
        tag_mapping = {}
        if not circle_ids:
            return tag_mapping

        circle_ids_str = self._get_string_by_list(circle_ids)
        sql = 'SELECT tag_id, circle_id FROM "starCircle_circle2tag" WHERE circle_id IN (%s)' % circle_ids_str
        db_results = self._get_sql_results(sql)
        tag_ids = [item[0] for item in db_results]

        tag_dict = {}
        tag_ids_str = self._get_string_by_list(tag_ids)

        if tag_ids_str:
            tag_sql = 'SELECT id, title FROM "starCircle_tag" ' \
                      'WHERE is_show=true AND is_delete=false AND id IN (%s)'% tag_ids_str
            tag_db_results = self._get_sql_results(tag_sql)
            tag_dict = {item[0]: item[1] for item in tag_db_results}

        for item in db_results:
            tag_id = item[0]
            circle_id = item[1]
            tag_title = tag_dict.get(tag_id)
            tag_list = tag_mapping.setdefault(circle_id, [])

            if not any([tag_id == it['id'] for it in tag_list]):
                tag_title and tag_list.append(dict(id=tag_id, title=tag_title))

        return tag_mapping

    def _get_up_mapping(self, ids, user_ids=None, up_type="circle"):
        assert up_type in ['circle', 'comment'], "点赞类型错误"

        if not ids:
            return {}

        if up_type == 'circle':
            table_name = '"starCircle_circleup"'
            fields = ['"isUp"', 'circle_id', 'user_id']
            where = "WHERE circle_id IN (%s)" % self._get_string_by_list(ids)
        else:
            table_name = '"starCircle_commentup"'
            fields = ['"isUp"', 'comment_id', 'user_id']
            where = "WHERE comment_id IN (%s)" % self._get_string_by_list(ids)

        if user_ids:
            where += " AND circle_id IN (%s)" % self._get_string_by_list(user_ids)

        sql = "SELECT %s FROM %s %s ORDER BY id ASC" % (','.join(fields), table_name, where)
        db_results = self._get_sql_results(sql)

        return {(item[1], item[2]): item[0] for item in db_results}

    def get_circle_list(self):
        circle_list, total_count = self._get_circle_data_from_db().values()

        circle_ids = [item['id'] for item in circle_list]
        circle_user_ids = [item['user_id'] for item in circle_list]
        circle_up_dict = self._get_up_mapping(ids=circle_ids, up_type='circle')

        # 评论条数
        comment_list = self._get_comment_data_from_db(circle_ids=circle_ids, count=True)['comment_list']
        comment_dict = {item['circle_id']: item['cnt'] for item in comment_list}

        user_mapping = self._get_user_mapping(user_ids=circle_user_ids)  # 发帖用户信息
        image_mapping = self._get_image_mapping(circle_ids)  # 图片、视频链接
        tag_mapping = self._get_tag_mapping(circle_ids)  # 发帖对应的标签

        for circle_item in circle_list:
            circle_id = circle_item['id']
            user_id = circle_item['user_id']
            is_up = circle_up_dict.get((circle_id, user_id), False)

            created_time = circle_item['created_time']
            circle_item['created_time'] = created_time and created_time.strftime("%Y-%m-%d %H:%M:%S") or ''

            image_list = image_mapping.get(circle_id, [])
            post_type, screen_style = self._get_post_screen_type(image_list)

            circle_item.update(
                is_up=is_up, image_list=image_list,
                post_type=post_type, screen_style=screen_style,
                user=user_mapping.get(user_id, {}),
                tag_list=tag_mapping.get(circle_id, []),
                comment_cnt=comment_dict.get(circle_id, 0)
            )

        return dict(list=circle_list, total_count=total_count)

    def get_comment_of_circle_list(self, is_circle=True, **kwargs):
        """ 发帖对应的评论 """
        circle_id = self.query_params.get('circle_id') or 0
        circle_ids = [circle_id] if is_circle else kwargs.pop('circle_ids', [])

        # 评论信息
        comment_dict = self._get_comment_data_from_db(is_circle=is_circle, circle_ids=circle_ids, paginate=True, **kwargs)
        comment_list, total_count = comment_dict['comment_list'], comment_dict['total_count']
        comment_ids = [item['nid'] for item in comment_list]
        comment_user_ids = [item['user_id'] for item in comment_list]
        comment_up_dict = self._get_up_mapping(ids=comment_ids, up_type='comment')

        # 父级评论信息
        parent_comment_ids = [item['parent_comment_id'] for item in comment_list]
        parent_comment_dict = self._get_comment_data_from_db(is_circle=is_circle, ids=parent_comment_ids, **kwargs)
        parent_comment_list = parent_comment_dict['comment_list']
        parent_actual_dict = {item['nid']: item['is_actual'] for item in parent_comment_list}

        parent_kv = {item['nid']: item['user_id'] for item in parent_comment_list}
        parent_user_mapping = self._get_user_mapping(user_ids=parent_kv.values())
        parent_user_dict = {nid: parent_user_mapping.get(p_uid, {}) for nid, p_uid in parent_kv.items()}

        user_mapping = self._get_user_mapping(user_ids=comment_user_ids)  # 评论的用户信息

        # 评论
        for comment_item in comment_list:
            comment_id = comment_item['nid']
            comment_user_id = comment_item['user_id']
            parent_comment_id = comment_item['parent_comment_id']
            comment_user = user_mapping.get(comment_user_id, {})

            comment_item['is_up'] = comment_up_dict.get((comment_id, comment_user_id))
            comment_item['fullname'] = comment_user.get('fullname', '')
            comment_item['real_avatar'] = comment_user.get('real_avatar', '')

            created_time = comment_item['created_time']
            comment_item['created_time'] = created_time and created_time.strftime("%Y-%m-%d %H:%M:%S") or ''

            parent_is_actual = parent_actual_dict.get(parent_comment_id)
            if parent_is_actual:
                parent_comment_nickname = parent_user_dict.get(parent_comment_id, {}).get('fullname', '')
            else:
                parent_comment_nickname = '匿名用户' if parent_is_actual is not None else ''

            comment_item['parent_comment_nickname'] = parent_comment_nickname

        return dict(list=comment_list, total_count=total_count)

    def get_comment_list(self):
        """ 所有评论 """
        circle_ids = None
        query_params = self.get_query_params()
        circle_text = query_params.get('circle_text')
        comment_text = query_params.get('comment_text')

        if circle_text:
            sql = """
                SELECT id FROM "starCircle_starcircle" 
                WHERE is_delete=false AND content like '%%%s%%' 
            """ % circle_text
            circle_ids = [v[0] for v in self._get_sql_results(sql)]

        comment_data = self.get_comment_of_circle_list(
            is_circle=False, content=comment_text,
            circle_ids=circle_ids, is_esg=False
        )
        comment_list = comment_data['list']
        total_count = comment_data['total_count']

        circle_ids = [cm['circle_id'] for cm in comment_list]
        circle_data = self._get_circle_data_from_db(
            circle_ids=circle_ids, visible_range='',
            is_count=False, paginate=False
        )
        circle_dict = {item['id']: item for item in circle_data['circle_list']}

        for comment_item in comment_list:
            comment_item['id'] = comment_item.pop('nid')

            circle_id = comment_item['circle_id']
            comment_item['circle'] = circle_dict.get(circle_id, {})

        return dict(list=comment_list, total_count=total_count)

    def set_comment_state(self):
        is_show = self._request.data.get('is_show')
        comment_id = self._request.data.get('comment_id') or 0

        params = (is_show and 'true' or 'false', str(comment_id))
        sql = 'UPDATE "starCircle_circlecomment" SET is_show=%s WHERE nid=%s'
        self._execute_sql(sql % params)

        return dict(msg="C端评论隐藏/显示完成", is_ok=True)

    def set_circle_top_page(self):
        is_top = self._request.data.get('is_top')
        circle_id = self._request.data.get('circle_id') or 0

        if not circle_id:
            return dict(msg="话题不存在", is_ok=False)

        params = (is_top and 'true' or 'false', str(circle_id))
        sql = 'UPDATE "starCircle_starcircle" SET is_tag_page_top=%s WHERE id=%s'
        self._execute_sql(sql % params)

        return dict(msg="话题标签置顶完成", is_ok=True)

    def set_circle_state(self):
        is_esg = self._request.data.get('is_esg')
        is_show = self._request.data.get('is_show')
        circle_id = self._request.data.get('circle_id') or 0

        if not circle_id:
            return dict(msg="话题不存在", is_ok=False)

        params = (is_show and 'true' or 'false', str(circle_id))
        sql = 'UPDATE "starCircle_starcircle" SET is_show=%s WHERE id=%s'

        with transaction.atomic():
            if is_esg:
                # ESG需要回调积分接口
                pass

            self._execute_sql(sql % params)

        return dict(msg="C端隐藏/显示完成", is_ok=True)

    def add_admin_comment(self):
        user_id = self._request.data.get('user_id') or 0
        circle_id = self._request.data.get('circle_id') or 0
        content = self._request.data.get('content') or ''
        is_actual = self._request.data.get('is_actual')

        user_sql = 'SELECT id, "isForbidden" FROM users_userinfo WHERE id=%s'
        user_db_ret = self._get_sql_results(user_sql % str(user_id), fields=['id', 'is_forbidden'])

        if user_db_ret and user_db_ret[0]['is_forbidden']:
            return dict(msg="您已经被禁言，请联系运营！", is_ok=False)

        comment_sql = """
            INSERT INTO "starCircle_circlecomment"
            (circle_id, user_id, content, is_delete, is_show, is_actual, created_time, update_time, "createTime", "upCount")
            VALUES (%s, %s, '%s', false, true, %s, 'NOW()', 'NOW()', current_date, 0)
        """
        params = (str(circle_id), str(user_id), content, is_actual and 'true' or 'false')
        self._execute_sql(comment_sql % params)

        circle_sql = 'UPDATE "starCircle_starcircle" SET "commentCount" = "commentCount" + 1 WHERE id=%s'
        self._execute_sql(circle_sql % (str(circle_id), ))

        return dict(msg="管理端评论提交成功", is_ok=True)

    def _get_ev_db_mobiles(self, where: str):
        sql = 'SELECT b."phoneNumber" FROM event_tracking_uv a JOIN users_userinfo b ON a.user_id=b.id '
        db_ret = self._get_sql_results(sql + where, fields=['mobile'])
        logger.info('_get_ev_mobiles -> sq: %s', sql + where)

        mobile_list = list({item['mobile'] for item in db_ret if item['mobile']})
        return mobile_list

    def _get_ev_db_dau_list(self, where: str, multiple: int = 1):
        dau_sql = """
            SELECT 
                EXTRACT(YEAR FROM tracking_time) AS yy,
                EXTRACT(MONTH FROM tracking_time) AS mm,
                EXTRACT(DAY FROM tracking_time) AS dd,
                COUNT(DISTINCT user_id),
                COUNT(*) * {multiple}
            FROM event_tracking_uv 
            {where} 
            GROUP BY yy, mm, dd ORDER BY yy, mm, dd
        """.format(where=where, multiple=multiple)
        db_dau_ret = self._get_sql_results(dau_sql, fields=["yy", "mm", "dd", "dau_cnt", "pv"])
        logger.info('_get_ev_db_dau_list -> dau_sql: %s', dau_sql)

        return db_dau_ret

    def _get_ev_db_login_list(self, where: str):
        login_sql = """
            SELECT 
                EXTRACT(YEAR FROM tracking_time) AS yy,
                EXTRACT(MONTH FROM tracking_time) AS mm,
                EXTRACT(DAY FROM tracking_time) AS dd,
                COUNT(id)
            FROM event_tracking_uv 
            {where} AND tracking_type=1
            GROUP BY yy, mm, dd ORDER BY yy, mm, dd
        """.format(where=where)
        db_login_ret = self._get_sql_results(login_sql, fields=["yy", "mm", "dd", "login_cnt"])
        logger.info('_get_ev_db_login_list -> login_sql: %s', login_sql)

        return db_login_ret

    def _get_ev_db_bbs_list(self, start: str, end: str, visible_range: typing.Union[None, str] = None):
        bbs_sql = """
            SELECT 
                EXTRACT(YEAR FROM created_time) AS yy,
                EXTRACT(MONTH FROM created_time) AS mm,
                EXTRACT(DAY FROM created_time) AS dd,
                COUNT(id),
                SUM("upCount")
            FROM "starCircle_starcircle" 
            {where}
            GROUP BY yy, mm, dd ORDER BY yy, mm, dd
        """
        where = " WHERE created_time >= '%s' AND created_time <= '%s' " % (start, end)

        if visible_range:
            where += " AND visible_range='%s' " % visible_range

        bbs_sql = bbs_sql.format(where=where)
        db_bbs_list = self._get_sql_results(bbs_sql, fields=["yy", "mm", "dd", "post_cnt", "star_cnt"])
        logger.info('_get_ev_db_bbs_list -> bbs_sql: %s', bbs_sql)

        return db_bbs_list

    def _get_ev_db_biz_mau_list(self, mobiles: typing.List[str]):
        mobile_str = ", ".join("'%s'" % s for s in mobiles)
        biz_sql = """
                    SELECT a.dep_name, COUNT(a.dep_name) FROM circle_ding_department a
                    JOIN circle_user_department_relation b
                    ON a.dep_id = b.first_dep AND a.is_alive=TRUE AND b.is_alive=TRUE
                    JOIN circle_users cc
                    ON b.usr_id = cc.usr_id
                    WHERE cc.phone_number IN (%s)
                    GROUP BY a.dep_name
                """
        if mobile_str:
            biz_mau_list = self._get_sql_results(biz_sql % mobile_str, fields=['name', 'cnt'], alias='default')
        else:
            biz_mau_list = []

        return biz_mau_list

    def _get_one_dict(self, items: typing.List[dict], current_date: datetime.date):
        y, m, d = current_date.year, current_date. month, current_date.day
        item_list = [item for item in items if int(item['yy'] == y) and int(item["mm"]) == m and int(item["dd"]) == d]

        return item_list and item_list[0] or {}

    def get_event_tracking_data(self, start_date: datetime.datetime, end_date: datetime.datetime):
        start = start_date.strftime("%Y-%m-%d") + " 00:00:00"
        end = end_date.strftime("%Y-%m-%d") + " 23:59:59"
        where = " WHERE tracking_time >= '%s' AND tracking_time <= '%s'" % (start, end)

        mobile_list = self._get_ev_db_mobiles(where=where)
        db_dau_ret = self._get_ev_db_dau_list(where=where, multiple=9)
        db_login_ret = self._get_ev_db_login_list(where=where)
        db_bbs_list = self._get_ev_db_bbs_list(start, end, visible_range=None)
        biz_mau_list = self._get_ev_db_biz_mau_list(mobiles=mobile_list)

        result = dict(mau_cnt=len(mobile_list), dau_list=[], biz_mau_list=biz_mau_list)

        while end_date >= start_date:
            dau_dict = self._get_one_dict(db_dau_ret, end_date)
            bbs_dict = self._get_one_dict(db_bbs_list, end_date)
            login_dict = self._get_one_dict(db_login_ret, end_date)

            result["dau_list"].append(dict(
                date=end_date.strftime("%Y-%m-%d"), pv=dau_dict.get("pv", 0),
                dau_cnt=dau_dict.get("dau_cnt", 0), login_cnt=login_dict.get("login_cnt", 0),
                post_cnt=bbs_dict.get("post_cnt", 0), star_cnt=bbs_dict.get("star_cnt", 0),
            ))

            end_date = end_date + datetime.timedelta(days=-1)

        return result

    def get_hr_zhihu_event_tracking_data(self, start_date: datetime.datetime, end_date: datetime.datetime):
        start = start_date.strftime("%Y-%m-%d") + " 00:00:00"
        end = end_date.strftime("%Y-%m-%d") + " 23:59:59"
        where = " WHERE tracking_time >= '%s' AND tracking_time <= '%s' AND tracking_type IN (6, 7)" % (start, end)

        mobile_list = self._get_ev_db_mobiles(where=where)
        db_dau_ret = self._get_ev_db_dau_list(where=where, multiple=1)
        db_bbs_list = self._get_ev_db_bbs_list(start, end, visible_range='oversea')
        biz_mau_list = self._get_ev_db_biz_mau_list(mobiles=mobile_list)

        result = dict(mau_cnt=len(mobile_list), dau_list=[], biz_mau_list=biz_mau_list)

        while end_date >= start_date:
            dau_dict = self._get_one_dict(db_dau_ret, end_date)
            bbs_dict = self._get_one_dict(db_bbs_list, end_date)

            result["dau_list"].append(dict(
                date=end_date.strftime("%Y-%m-%d"),
                dau_cnt=dau_dict.get("dau_cnt", 0), pv=dau_dict.get("pv", 0),
                post_cnt=bbs_dict.get("post_cnt", 0), star_cnt=bbs_dict.get("star_cnt", 0),
            ))

            end_date = end_date + datetime.timedelta(days=-1)

        return result

    def get_slideShow_list(self):
        query_params = self.get_query_params()
        key = query_params.get('key')
        page_size = query_params['page_size']
        offset = (query_params['page'] - 1) * page_size

        fields = ['id', 'name', 'image_url', 'link', 'note']
        sql = 'SELECT id, name, "imageUrl", link, note FROM banner_banner '
        where = "WHERE is_delete=false "

        if key:
            where += " AND name like '%%%s%%' " % key

        db_banner_ret = self._get_sql_results('SELECT COUNT(1) FROM banner_banner ' + where)
        total_count = db_banner_ret[0][0]

        sql += where + " ORDER BY id DESC OFFSET %s LIMIT %s" % (offset, page_size)
        banner_list = self._get_sql_results(sql, fields=fields)

        return dict(list=banner_list, total_count=total_count)

    def operate_slideShow(self):
        action = self._request.data.pop('action')

        if action == 'create':
            sql = """
                INSERT INTO banner_banner (name, "imageUrl", link, note, created_time, update_time, is_show, is_delete) 
                VALUES ('{name}', '{image_url}', '{link}', '{note}', NOW(), NOW(), false, false) 
                """
        elif action == 'update':
            sql = """
                UPDATE banner_banner 
                SET name='{name}', "imageUrl"='{image_url}', link='{link}', note='{note}', update_time=NOW()
                WHERE id={id}
                """
        elif action == 'delete':
            sql = 'UPDATE banner_banner SET is_delete=true WHERE id={id}'
        else:
            raise ValueError(f'action: {action}操作不允许')

        self._execute_sql(sql.format(**self._request.data))

    def get_ddshare_list(self):
        query_params = self.get_query_params()
        key = query_params.get('key')
        page_size = query_params['page_size']
        offset = (query_params['page'] - 1) * page_size

        where = ''
        fields = ['id', 'title', 'content', 'image', 'url', 'page', 'share_type']
        sql = 'SELECT id, title, content, image, url, page, "shareType" FROM share_share '

        if key:
            query = ["title like '%%%s%%'", "content like '%%%s%%'", "page like '%%%s%%'"]
            where = " WHERE " + ' OR '.join([q % key for q in query])

        db_share_ret = self._get_sql_results('SELECT COUNT(1) FROM share_share ' + where)
        total_count = db_share_ret[0][0]

        sql += where + " ORDER BY id DESC OFFSET %s LIMIT %s" % (offset, page_size)
        share_list = self._get_sql_results(sql, fields=fields)

        return dict(list=share_list, total_count=total_count)

    def operate_ddshare(self):
        action = self._request.data.pop('action')

        if action == 'create':
            sql = """
                INSERT INTO share_share (title, content, image, url, page, "shareType") 
                VALUES ('{title}', '{content}', '{image}', '{url}', '{page}', 0) 
            """
        elif action == 'update':
            sql = """
                UPDATE share_share 
                SET title='{title}', content='{content}', image='{image}', url='{url}', page='{page}'
                WHERE id={id}
            """
        elif action == 'delete':
            sql = 'DELETE FROM share_share WHERE id={id}'
        else:
            raise ValueError(f'action: {action}操作不允许')

        self._execute_sql(sql.format(**self._request.data))

    def get_tag_list(self):
        query_params = self.get_query_params()
        key = query_params.get('key')
        page_size = query_params['page_size']
        offset = (query_params['page'] - 1) * page_size

        fields = ['id', 'created_time', 'is_show', 'title', 'tag_desc', 'is_top', 'circle_cnt']
        sql = """
            SELECT 
                aa.id, aa.created_time, aa.is_show, aa.title, aa.tag_desc, aa.is_top, 
                (
                    SELECT COUNT(*) FROM "starCircle_circle2tag" 
                    WHERE tag_id=aa.id AND circle_id IN 
                        (
                        SELECT id FROM "starCircle_starcircle" 
                        WHERE is_delete=FALSE AND is_show=true
                        )
                )
            FROM "starCircle_tag" aa
        """
        where = " WHERE aa.is_delete=false "

        if key:
            query = ["aa.title like '%%%s%%'", "aa.tag_desc like '%%%s%%'"]
            where += " AND " + " (%s) " % ' OR '.join([q % key for q in query])

        db_share_ret = self._get_sql_results('SELECT COUNT(*) FROM "starCircle_tag" aa ' + where)
        total_count = db_share_ret[0][0]

        sql += where + " ORDER BY aa.created_time DESC, aa.is_show DESC OFFSET %s LIMIT %s" % (offset, page_size)

        tag_list = []
        for item in self._get_sql_results(sql, fields=fields):
            created_time = item.pop('created_time')
            item['created_time'] = created_time and created_time.strftime("%Y-%m-%d %H:%M:%S") or ''
            tag_list.append(item)

        return dict(list=tag_list, total_count=total_count)

    def operate_tag(self):
        data = self._request.data
        action = self._request.data.pop('action')

        if action == 'add_tag':
            sql = """
                INSERT INTO "starCircle_tag"
                (created_time, update_time, is_show, is_delete, title, is_recommend, is_official, is_top, tag_desc)
                VALUES (NOW(), NOW(), true, false, '%s', false, true, false, '')
            """
            params = (data.get('title'), )
        elif action == 'set_show':
            sql = 'UPDATE "starCircle_tag" SET is_show=%s WHERE id=%s'
            params = (data.get('is_show') and 'true' or 'false', data.get('id'))
        elif action == 'set_top':
            sql = 'UPDATE "starCircle_tag" SET is_top=%s WHERE id=%s'
            params = (data.get('is_top') and 'true' or 'false', data.get('id'))
        else:
            raise ValueError(f'action: {action}操作不允许')

        self._execute_sql(sql % params)
