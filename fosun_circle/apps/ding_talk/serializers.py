import re
import time
import json
import traceback
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.db.models import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django_redis import get_redis_connection

from django_celery_beat.models import PeriodicTask, CrontabSchedule

from .models import DingAppTokenModel, DingMsgPushLogModel, DingMessageModel
from .models import DingAppMediaModel, DingMsgRecallLogModel, DingPeriodicTaskModel
from users.models import CircleUsersModel
from fosun_circle.core.globals import local_user
from fosun_circle.libs.exception import PhoneValidateError
from fosun_circle.libs.log import dj_logger as logger
from fosun_circle.libs.utils.snow_flake import Snowflake
from fosun_circle.libs.utils.crypto import BaseCipher

user_model_cls = get_user_model()


class DingAppTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DingAppTokenModel
        fields = DingAppTokenModel.fields()
        read_only_fields = ["app_token"]

    def create(self, validated_data):
        model_cls = self.Meta.model
        instance = model_cls.objects.filter(agent_id=validated_data.get("agent_id", 0)).first()

        if instance is None:
            instance = model_cls(**validated_data)

        instance.save_attributes(**validated_data)
        instance.app_token = instance.encrypt_token()
        instance.expire_time = int(time.time()) + 20 * 365 * 24 * 60 * 60
        instance.save()

        return instance

    def update(self, instance, validated_data):
        validated_data["app_token"] = instance.encrypt_token()
        validated_data["expire_time"] = int(time.time()) + 20 * 365 * 24 * 60 * 60

        return super().update(instance, validated_data)


class DingMessageSerializer(serializers.ModelSerializer):
    app = DingAppTokenSerializer(read_only=True)

    class Meta:
        model = DingMessageModel
        fields = DingMessageModel.fields() + ["app"]
        read_only_fields = ['msg_type_cn', 'source_cn', 'ihcm_survey_id']

    def get_cleaned_data(self, validated_data):
        source_map = dict(self.Meta.model.SOURCE_CHOICES)
        msg_type_map = dict(self.Meta.model.MSG_TYPE_CHOICES)

        validated_data['app_id'] = self.initial_data['app_id']
        validated_data['source_cn'] = source_map[validated_data['source']]
        validated_data['msg_type_cn'] = msg_type_map[validated_data['msg_type']]

    def create(self, validated_data):
        self.get_cleaned_data(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self.get_cleaned_data(validated_data)
        return super().update(instance, validated_data)

    @classmethod
    def get_ding_message_cache(cls, queryset, target, field=None):
        field = field or 'ding_msg_id'
        attr_name = "_DingMsgCache_%s" % id(target)

        if not hasattr(target, attr_name):
            ding_msg_ids = [getattr(obj, field, 0) for obj in queryset]
            msg_queryset = cls.Meta.model.objects.filter(id__in=ding_msg_ids).select_related('app')
            msg_serializer = cls(msg_queryset, many=True)

            msg_map = {item['id']: item for item in msg_serializer.data}
            setattr(target, attr_name, msg_map)

            return msg_map

        return getattr(target, attr_name)


class ListDingMessageLogSerializer(serializers.ModelSerializer):
    ding_msg = serializers.SerializerMethodField()
    app_name = serializers.SerializerMethodField()
    app_token = serializers.SerializerMethodField()
    receive_time = serializers.SerializerMethodField()
    # receive_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, help_text="接受时间")

    class Meta:
        model = DingMsgPushLogModel
        fields = DingMsgPushLogModel.fields() + ["app_name", "app_token", "ding_msg", "receive_time"]

    def get_ding_msg(self, obj):
        ding_msg_cache_map = DingMessageSerializer.get_ding_message_cache(self.instance, target=self)
        return ding_msg_cache_map.get(obj.ding_msg_id, {})

    def get_app_name(self, obj):
        ding_msg_cache_map = DingMessageSerializer.get_ding_message_cache(self.instance, target=self)
        return ding_msg_cache_map.get(obj.ding_msg_id, {}).get('app', {}).get('app_name', '')

    def get_app_token(self, obj):
        ding_msg_cache_map = DingMessageSerializer.get_ding_message_cache(self.instance, target=self)
        return ding_msg_cache_map.get(obj.ding_msg_id, {}).get('app', {}).get('app_token', '')

    def get_receive_time(self, obj):
        receive_time = obj.receive_time.strftime('%Y-%m-%d %H:%M:%S')
        return receive_time == "1979-01-01 00:00:00" and "-" or receive_time


class ListPushDingMsgLogSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        """ 暂未用到批量更新 """

    def create(self, validated_data):
        """ 批量创建
        @:param validated_data: list
        """
        start_bulk_time = time.time()
        logger.info("ListDingMsgPushSerializer ===>>> Start bulk_create")

        # 校验通过后, self.initial_data 与 validated_data 数据一致, 除了 validated_data 的每个字典中不包含 app_token
        # mobile与jobCode
        mobile_list = [item["receiver_mobile"] for item in validated_data]
        user_query_kwargs = dict(phone_number__in=mobile_list, is_del=False)
        user_queryset = CircleUsersModel.objects.filter(**user_query_kwargs).values("phone_number", "ding_job_code")
        mobile_jobCode_dict = {user_item["phone_number"]: user_item["ding_job_code"] for user_item in user_queryset}

        # 微应用信息
        app_token_list = [item["app_token"] for item in self.initial_data]
        plain_token_list = [DingAppTokenModel.decipher_text(_app_token) for _app_token in app_token_list]
        agent_id_list = [int(_plain_token.split(":", 1)[0]) for _plain_token in plain_token_list]

        app_query_kwargs = dict(agent_id__in=agent_id_list, is_del=False)
        app_queryset = DingAppTokenModel.objects.filter(**app_query_kwargs).values("id", "agent_id")
        app_agent_dict = {app_item["agent_id"]: app_item["id"] for app_item in app_queryset}

        bulk_obj_list = []
        model_cls = self.child.Meta.model

        # 钉钉消息主体指纹
        ding_message_body_mapping = {}
        ding_message_log_mapping = {}
        start_parse_time = time.time()

        for index, data in enumerate(self.initial_data):
            message_data = dict(data, **validated_data[index])
            new_validated_data = self.child.derive_value(message_data)

            plain_token = DingAppTokenModel.decipher_text(new_validated_data["app_token"])
            agent_id = int(plain_token.split(":", 1)[0])

            # 消息主体指纹
            app_id = app_agent_dict.get(agent_id)
            new_validated_data["app_id"] = app_id

            # 消息主体指纹获取消息id
            ding_msg_id = self.child.get_or_create_message_id(new_validated_data, ding_message_body_mapping)
            is_cached = new_validated_data.pop("is_cached", True)  # 消息是否需要缓存，默认缓存

            # 补充消息记录信息并过滤消息记录指纹
            mobile = new_validated_data["receiver_mobile"]
            new_validated_data.update(ding_msg_id=ding_msg_id, receiver_job_code=mobile_jobCode_dict.get(mobile, ""))

            log_fingerprint = self.child.get_log_fingerprint(validated_data=new_validated_data)
            has_fingerprint = self.child.has_log_fingerprint(app_id, ding_msg_id, mobile, log_fingerprint)

            if is_cached:
                if not has_fingerprint:
                    ding_message_log_mapping[(app_id, ding_msg_id, mobile)] = log_fingerprint
                    bulk_obj_list.append(model_cls.create_object(force_insert=False, **new_validated_data))
            else:
                bulk_obj_list.append(model_cls.create_object(force_insert=False, **new_validated_data))

        end_parse_time = time.time()
        logger.info("ListPushDingMsgLogSerializer ===>>> Parse Cost:%s", end_parse_time - start_parse_time)
        instance_list = model_cls.objects.bulk_create(bulk_obj_list)  # bulk_obj_list 太大可能引起批量插入的性能下降

        end_bulk_time = time.time()
        log_args = (end_bulk_time - start_bulk_time, end_bulk_time - end_parse_time)
        logger.info("ListDingMsgPushSerializer ===>>> End bulk_create, All Cost: %s, Bulk Insert Cost: %s", *log_args)

        # self.child.bulk_insert_fingerprint_to_redis(ding_message_body_mapping, ding_message_log_mapping)
        return instance_list


class PushDingMsgLogSerializer(serializers.ModelSerializer):
    DING_MSG_BODY_KEY = "ding_body:%s"
    DING_MSG_LOG_KEY = "ding_log:app_id:%s:ding_msg_id:%s:mobile:%s"

    app_token = serializers.SerializerMethodField(help_text="微应用token")
    receiver_mobile = serializers.CharField(max_length=50000, help_text="推送的手机号")

    class Meta:
        model = DingMsgPushLogModel
        fields = DingMsgPushLogModel.fields() + ["app_token"]
        read_only_fields = [
            "app_id", "msg_type_cn", "sender", "send_time",
            "receiver_job_code", "receive_time", "is_read", "read_time", "is_success",
            "traceback", "task_id", "request_id", "source_cn", "is_done"
        ]

        list_serializer_class = ListPushDingMsgLogSerializer

    def get_message_body_fingerprint(self, message_value):
        """ 钉钉消息主体指纹 """
        fields = DingMessageModel.fields()
        'msg_text' not in message_value and message_value.update(msg_text="")
        required_fields = [name for name in self.fingerprint_fields if name in fields]

        message_fingerprint_rule = ":".join(["{%s}" % col for col in required_fields])
        message_fingerprint = message_fingerprint_rule.format(**message_value)

        return BaseCipher.crypt_md5(message_fingerprint)

    def get_message_body_fingerprint_mappings(self):
        """ 钉钉消息体的指纹映射 """
        ding_msg_body_result = {}
        start_time = time.time()
        # queryset = DingMessageModel.objects.filter(is_del=False).all()

        msg_fields = DingMessageModel.fields(exclude=("source_cn", "msg_type_cn", "ihcm_survey_id"))
        msg_sql = "SELECT {columns} FROM circle_ding_message_info " \
                  "WHERE is_del=false".format(columns=",".join(msg_fields))
        msg_body_results = self.query_raw_sql(msg_sql, using=None, columns=msg_fields)

        for ding_msg_item in msg_body_results:
            fingerprint = self.get_message_body_fingerprint(ding_msg_item)
            ding_msg_body_result[fingerprint] = ding_msg_item["id"]

        logger.info("get_message_body_fingerprint_mappings cost time: %s", time.time() - start_time)
        return ding_msg_body_result

    def get_message_id_from_redis(self, fingerprint):
        redis_conn = get_redis_connection()

        key = self.DING_MSG_BODY_KEY % fingerprint
        app_id = redis_conn.get(key)

        return app_id and int(app_id) or None

    def get_or_create_message_id(self, data, cached_message_body_mapping=None):
        """ 获取或创建 DingMessageModel 对象 """
        assert isinstance(cached_message_body_mapping, dict), "缓存参数必须传 dict 类型"

        message_id = int(data.pop("message_id", 0))

        if message_id:
            # 批量时每次请求DingMessageModel， 可能造成性能下降
            tmp_cache_msg_attr = "TmpCacheMessageObject_%s" % message_id

            if hasattr(self, tmp_cache_msg_attr):
                message_obj = getattr(self, tmp_cache_msg_attr)
            else:
                message_obj = DingMessageModel.objects.filter(id=message_id, is_del=False).first()
                if not message_obj:
                    raise ObjectDoesNotExist("DingMessageModel<id: %s>不存在" % message_id)

                setattr(self, tmp_cache_msg_attr, message_obj)

            ding_msg_id = message_obj.id
            ding_msg_dict = message_obj.to_dict(exclude=["id"])
            data.update(ding_msg_dict)  # 可能没有消息主体消息，更新

            fingerprint_data = {k: ding_msg_dict.get(k, '') for k in self.fingerprint_fields}
            message_body_fingerprint = self.get_message_body_fingerprint(fingerprint_data)
        else:
            message_body_fingerprint = self.get_message_body_fingerprint(data)
            # First get message from Redis, then to `cache_message_body_mapping`
            msg_id_from_redis = self.get_message_id_from_redis(message_body_fingerprint)

            if not msg_id_from_redis:
                if cached_message_body_mapping.get(message_body_fingerprint):
                    ding_msg_id = cached_message_body_mapping[message_body_fingerprint]
                else:
                    ding_msg_obj = DingMessageModel.create_object(**data)
                    ding_msg_id = ding_msg_obj.id

                # 存入 Redis 中
                redis_conn = get_redis_connection()
                body_key = self.DING_MSG_BODY_KEY % message_body_fingerprint
                redis_conn.set(body_key, ding_msg_id, ex=7 * 24 * 60 * 60)
            else:
                ding_msg_id = msg_id_from_redis

        cached_message_body_mapping[message_body_fingerprint] = ding_msg_id  # 暂存
        return ding_msg_id

    @classmethod
    def derive_value(cls, validated_data):
        """ 自定义类方法 """
        snow_alg = Snowflake(1, 1)
        source_mapper = dict(DingMessageModel.SOURCE_CHOICES)
        msg_type_mapper = dict(DingMessageModel.MSG_TYPE_CHOICES)

        source = int(validated_data.get("source", 0))
        msg_text = validated_data.get("msg_text", "")

        if source == 1:     # 星喜积分
            msg_text = re.sub(r"<!--.*?-->", "", msg_text)
            validated_data.update(msg_text=msg_text.strip())

        validated_data.update(
            is_read=False, is_success=False,
            send_time=datetime.now(), msg_uid=snow_alg.get_id(),
            sender=local_user.mobile if local_user else "sys",
            source_cn=source_mapper.get(validated_data.get("source"), ""),
            msg_type_cn=msg_type_mapper.get(validated_data.get("msg_type"), 0)
        )

        return validated_data

    def get_sent_message_log_fingerprints(self, mobile_list=None, app_ids=None, is_raw=False):
        """ 获取最近30天内已发送的消息的指纹,用于过滤，避免重发 (改进：快速过滤: 布隆过滤)

        :param mobile_list, 手机号列表
        :param app_ids, 微应用列表
        :param is_raw, 是否使用原生sql查询
        """
        validated_data_list = []
        app_ids = app_ids or []
        mobile_list = mobile_list or []
        start_time = time.time()

        log_model_cls = self.Meta.model
        log_model_fields = set(log_model_cls.fields())
        fingerprint_fields = self.fingerprint_fields

        # 钉钉消息体和关联微应用
        start_ts002 = time.time()
        msg_fields = DingMessageModel.fields(exclude=("source_cn", "msg_type_cn", "ihcm_survey_id"))

        if not is_raw:
            orm_query = dict(is_del=False)
            app_ids and orm_query.update(app_id__in=app_ids)
            msg_queryset = DingMessageModel.objects.filter(**orm_query).values(*msg_fields)
            msg_mapping_dict = {msg_item["id"]: msg_item for msg_item in msg_queryset}
        else:
            sql_where = "WHERE is_del=false "
            if app_ids:
                sql_where += " AND app_id in (%s)" % ",".join([str(_id) for _id in app_ids])

            msg_sql = "SELECT {msg_columns} FROM circle_ding_message_info ".format(msg_columns=", ".join(msg_fields))
            msg_queryset = self.query_raw_sql(msg_sql + sql_where, columns=msg_fields)
            msg_mapping_dict = {msg_item["id"]: msg_item for msg_item in msg_queryset}

        start_ts003 = time.time()
        msg_cost_time = start_ts003 - start_ts002
        logger.info("get_sent_message_log_fingerprints Message body cost time: %s, is_raw: %s", msg_cost_time, is_raw)

        # 筛选对应的消息记录
        ding_msg_ids = list(msg_mapping_dict.keys())
        latest_sent_time = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")

        if not is_raw:
            orm_query = dict(ding_msg_id__in=ding_msg_ids, send_time__gt=latest_sent_time)
            mobile_list and orm_query.update(receiver_mobile__in=list(set(mobile_list)))
            log_msg_queryset = log_model_cls.objects.filter(**orm_query).values("receiver_mobile", "ding_msg_id")
            logger.info("get_sent_message_log_fingerprints log_msg_queryset SQL:%s", log_msg_queryset.query)
        else:
            sql_where = " WHERE send_time >= '%s' " % latest_sent_time
            sql_where += " ding_msg_id IN (%s) " % ",".join([str(did) for did in ding_msg_ids])
            if mobile_list:
                sql_where += " receiver_mobile IN (%s)".join(["'%s'" % m for m in set(mobile_list)])

            log_columns = ["receiver_mobile", "ding_msg_id"]
            log_sql = "SELECT {columns} FROM circle_ding_msg_push_log ".format(columns=",".join(log_columns))
            log_msg_queryset = self.query_raw_sql(sql=log_sql + sql_where, columns=log_columns)

        for log_msg_item in log_msg_queryset:
            ding_msg_id = log_msg_item["ding_msg_id"]
            item = dict(ding_msg_id=ding_msg_id)

            for field_name in fingerprint_fields:
                if field_name not in log_model_fields:
                    ding_msg_item = msg_mapping_dict.get(ding_msg_id) or {}
                    item[field_name] = ding_msg_item.get(field_name, "")
                else:
                    item[field_name] = log_msg_item[field_name]

            validated_data_list.append(item)

        logger.info("get_sent_message_log_fingerprints MsgLog cost time: %s", time.time() - start_ts003)
        logger.info("get_sent_message_log_fingerprints total cost time: %s", time.time() - start_time)

        return {self.get_log_fingerprint(validated_data=item): item for item in validated_data_list}

    def has_log_fingerprint(self, app_id, ding_msg_id, mobile, check_fingerprint):
        redis_conn = get_redis_connection()

        key = self.DING_MSG_LOG_KEY % (app_id, ding_msg_id, mobile)
        old_fingerprint = redis_conn.get(key)

        return old_fingerprint == check_fingerprint

    def bulk_insert_fingerprint_to_redis(self, bulk_body_mappings=None, bulk_log_mappings=None, timeout=None):
        """ 批量插入Redis,使用 Lua 可极大提升性能

        :param bulk_body_mappings: dict, eg:｛fingerprint: ding_msg_id｝ => {'804cac0dc22aff073fgy': 1234}
        :param bulk_log_mappings: dict,
                eg:{(app_id, ding_msg_id, mobile): fingerprint} => {(1, 2134, '13570921106'): '476743867646a97'}
        :param timeout: int, expire time to redis key

        # 使用 pipeline 优于单次设置过期时间，但是量大时依然很慢
            with redis_conn.pipeline(transaction=False) as p:
                for key, value in bulk_mappings.items():
                    # redis_conn.set(key, value, expire_time)
                    redis_conn.expire(key, expire_time)

                p.execute()  # Bulk execution

        """
        types = (dict, type(None))
        if not isinstance(bulk_body_mappings, types) or not isinstance(bulk_log_mappings, types):
            raise ValueError("bulk_body_mappings or bulk_log_mappings not dict")

        timeout = timeout or 15 * 60 * 60
        redis_conn = get_redis_connection()
        expire_lua = """
            for i=1, ARGV[1], 1 do
                redis.call("EXPIRE", KEYS[i], ARGV[2]);
            end
        """
        cmd = redis_conn.register_script(expire_lua)

        try:
            bulk_body_fp_mappings = {
                self.DING_MSG_BODY_KEY % body_fingerprint: ding_msg_id
                for body_fingerprint, ding_msg_id in (bulk_body_mappings or {}).items()
            }
            redis_conn.mset(bulk_body_fp_mappings)
            cmd(keys=list(bulk_body_fp_mappings.keys()), args=[len(bulk_body_fp_mappings), timeout])

            # {(app_id, ding_msg_id, mobile): fingerprint}
            bulk_log_fp_mappings = {
                self.DING_MSG_LOG_KEY % key: log_fingerprint
                for key, log_fingerprint in (bulk_log_mappings or {}).items()
            }

            # File "/data/app/fosun_circle/apps/ding_talk/serializers.py", line 448, in bulk_insert_fingerprint_to_redis
            #     redis_conn.mset(bulk_log_fp_mappings)
            #   File "/usr/lib/python3.10/site-packages/redis/client.py", line 1053, in mset
            #     return self.execute_command('MSET', *items)
            #   File "/usr/lib/python3.10/site-packages/redis/client.py", line 668, in execute_command
            #     return self.parse_response(connection, command_name, **options)
            #   File "/usr/lib/python3.10/site-packages/redis/client.py", line 680, in parse_response
            #     response = connection.read_response()
            #   File "/usr/lib/python3.10/site-packages/redis/connection.py", line 629, in read_response
            #     raise response
            # redis.exceptions.ResponseError: wrong number of arguments for 'mset' command
            # redis-py version 2.10.6 -> 3.0.1
            redis_conn.mset(bulk_log_fp_mappings)
            cmd(keys=list(bulk_log_fp_mappings.keys()), args=[len(bulk_log_fp_mappings), timeout])

            log_args = (len(bulk_body_fp_mappings), len(bulk_log_fp_mappings))
            logger.info("Fingerprint to Redis Count (Message Fingerprint: %s, Log Fingerprint: %s) OK",  *log_args)
        except Exception as e:
            logger.error(traceback.format_exc())

    @property
    def fingerprint_fields(self):
        msg_log_fields = ["receiver_mobile"]
        msg_fields = ["app_id", "source", "msg_type", "msg_title", "msg_media", "msg_text", "msg_url", "msg_pc_url"]

        return msg_log_fields + msg_fields

    def get_log_fingerprint(self, validated_data=None):
        """ 消息发送记录的唯一性指纹 """
        model_cls = self.Meta.model
        fingerprint_fields = self.fingerprint_fields
        fingerprint_info = ":".join(["{%s}" % _field for _field in fingerprint_fields])

        if validated_data:
            msg_kwargs = {k: validated_data.get(k, "") for k in fingerprint_fields}
        else:
            raise ValidationError("无法获取消息指纹")

        fingerprint_msg = fingerprint_info.format(**msg_kwargs)
        md5 = BaseCipher.crypt_md5(fingerprint_msg)

        return md5

    def query_raw_sql(self, sql, params=None, using=None, columns=()):
        """ 原生sql查询 """
        model_cls = self.Meta.model
        using = using or DEFAULT_DB_ALIAS
        connection = connections[using]
        cursor = connection.cursor()

        cursor.execute(sql, params=params)
        result = cursor.fetchall()
        mapping_result = [dict(zip(columns, item)) for item in result]

        return mapping_result

    def create(self, validated_data):
        logger.info("PushDingMsgLogSerializer.create ===>>> signal create")

        # app_token = validated_data.pop("app_token", None)  # app_token 只读字段,只能从 initial_data 中获取
        model_cls = self.Meta.model
        app_token = self.initial_data.get("app_token")

        if not app_token:
            raise PermissionError("<app_token> 为空, 钉钉消息无法推送")

        app_obj = DingAppTokenModel.get_app_by_token(app_token=app_token)
        agent_id = app_obj.agent_id

        if not app_obj:
            raise ObjectDoesNotExist("agent_id<%s> 没有找到记录" % agent_id)

        receiver_mobile = validated_data["receiver_mobile"]
        users = CircleUsersModel.objects.filter(phone_number=receiver_mobile).values("ding_job_code")
        ding_job_code = users[0]["ding_job_code"] if users else validated_data.get("receiver_job_code", "")

        message_data = dict(validated_data, app_id=app_obj.id, **self.initial_data)
        message_data.update(receiver_job_code=ding_job_code)
        new_validated_data = self.derive_value(message_data)

        # 钉钉消息主体指纹
        ding_message_body_mapping = {}
        ding_message_log_mapping = {}
        ding_msg_id = self.get_or_create_message_id(new_validated_data, ding_message_body_mapping)
        is_cached = new_validated_data.pop("is_cached", True)  # 消息是否需要缓存，默认缓存

        # 消息记录指纹
        new_validated_data["ding_msg_id"] = ding_msg_id
        log_fingerprint = self.get_log_fingerprint(validated_data=new_validated_data)
        has_fingerprint = self.has_log_fingerprint(app_obj.id, ding_msg_id, receiver_mobile, log_fingerprint)

        # 历史消息指纹(星喜积分:source=1 除外) => 被优化了
        if is_cached:
            if not has_fingerprint:
                instance_list = model_cls.create_object(**new_validated_data)
                ding_message_log_mapping[(app_obj.id, ding_msg_id, receiver_mobile)] = log_fingerprint
            else:
                logger.info("%s.create() 钉钉消息已存在" % self.__class__.__name__)
                instance_list = []
        else:
            instance_list = model_cls.create_object(**new_validated_data)

        # self.bulk_insert_fingerprint_to_redis(ding_message_body_mapping, ding_message_log_mapping)
        return instance_list

    def get_app_token(self, obj):
        return obj.app.app_token


class DingAppMediaSerializer(serializers.ModelSerializer):
    app = DingAppTokenSerializer()
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    media_type_cn = serializers.SerializerMethodField(help_text="媒体文件名称")

    class Meta:
        model = DingAppMediaModel
        fields = DingAppMediaModel.fields(exclude=("media", )) + ["app", "media_type_cn", "creator", "create_time"]

    def get_media_type_cn(self, obj):
        model = self.Meta.model
        media_mapping = dict(model.MEDIA_TYPE_CHOICE)

        return media_mapping.get(obj.media_type)


class ListRecallMsgLogSerializer(serializers.ModelSerializer):
    ding_msg = serializers.SerializerMethodField()
    recall_time = serializers.SerializerMethodField(required=False, help_text="撤回时间")
    recall_ret = serializers.SerializerMethodField(required=False, help_text="撤回结果")
    recall_ret_raw = serializers.SerializerMethodField(required=False, help_text="撤回结果2")

    class Meta:
        model = DingMsgRecallLogModel
        fields = DingMsgRecallLogModel.fields() + ["ding_msg", "recall_time", "recall_ret_raw"]

    def get_ding_msg(self, obj):
        ding_msg_cache_map = DingMessageSerializer.get_ding_message_cache(self.instance, target=self)
        return ding_msg_cache_map.get(obj.ding_msg_id, {})

    def get_recall_time(self, obj):
        # 可以用drf的自动转换时间格式
        recall_time = obj.recall_time.strftime('%Y-%m-%d %H:%M:%S')
        return recall_time == "1979-01-01 00:00:00" and "-" or recall_time

    def get_recall_ret(self, obj):
        if not obj.recall_ret:
            return

        try:
            recall_ret = json.dumps(json.loads(obj.recall_ret), indent=4)
        except json.JSONDecodeError:
            recall_ret = obj.recall_ret

        return recall_ret.replace("\n", "<br/>").replace(" ", "&nbsp;")

    def get_recall_ret_raw(self, obj):
        return obj.recall_ret


class DingPeriodicTaskSerializer(serializers.ModelSerializer):
    crontab = serializers.SerializerMethodField(default=None, allow_null=True, help_text="任务Cron")
    enabled = serializers.SerializerMethodField(default=None, allow_null=True, help_text="任务状态")
    push_range_py = serializers.SerializerMethodField(default=None, allow_null=True, help_text="推送范围(Dict)")
    option_users = serializers.SerializerMethodField(default=None, allow_null=True, help_text="下拉列表推送人员")
    app_name = serializers.SerializerMethodField(default=None, allow_null=True, help_text="定时任务所属APP")

    # drf自动转换时间格式
    deadline_run_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, help_text="截止执行时间")

    class Meta:
        model = DingPeriodicTaskModel

        _required_fields = model.fields() + ["enabled", "crontab", "push_range_py", "option_users", 'app_name']
        fields = _required_fields
        read_only_fields = _required_fields

    def _get_periodic_mapping(self):
        attr_name = "periodic_mapping_%s" % id(self)

        if not hasattr(self, attr_name):
            periodic_task_ids = [obj.beat_periodic_task_id for obj in self.instance]
            periodic_queryset = PeriodicTask.objects.filter(id__in=periodic_task_ids).values('id', 'enabled')
            periodic_mapping = {periodic_item['id']: periodic_item for periodic_item in periodic_queryset}

            setattr(self, attr_name, periodic_mapping)
            return periodic_mapping

        return getattr(self, attr_name)

    def _get_option_user_list(self):
        from users.views import ListFuzzyRetrieveUserApi
        attr_name = "option_user_list_%s" % id(self)

        if not hasattr(self, attr_name):
            mobile_list = []

            for obj in self.instance:
                receiver_mobile = json.loads(obj.push_range).get('receiver_mobile', '')
                mobile_list.extend([s.strip() for s in receiver_mobile.split(",") if s.strip()])

            option_user_list = ListFuzzyRetrieveUserApi().get_option_user_list_by_mobile(mobile_list)
            setattr(self, attr_name, option_user_list)
            return option_user_list

        return getattr(self, attr_name)

    def _get_crontab_mapping(self):
        attr_name = "crontab_mapping_%s" % id(self)

        if not hasattr(self, attr_name):
            crontab_ids = [obj.beat_cron_id for obj in self.instance]
            crontab_fields = ['id', 'minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year', 'timezone']
            crontab_queryset = CrontabSchedule.objects.filter(id__in=crontab_ids).values(*crontab_fields)
            crontab_mapping = {
                crontab_item['id']: dict(crontab_item, timezone=str(crontab_item['timezone']))
                for crontab_item in crontab_queryset
            }

            setattr(self, attr_name, crontab_mapping)
            return crontab_mapping

        return getattr(self, attr_name)

    def get_enabled(self, obj):
        periodic_mapping = self._get_periodic_mapping()
        beat_periodic_task_id = obj.beat_periodic_task_id
        task_enabled = periodic_mapping.get(beat_periodic_task_id, {}).get('enabled') or False

        return task_enabled

    def get_crontab(self, obj):
        crontab_mapping = self._get_crontab_mapping()
        return crontab_mapping.get(obj.beat_cron_id) or {}

    def get_push_range_py(self, obj):
        return json.loads(obj.push_range)

    def get_option_users(self, obj):
        option_user_list = self._get_option_user_list()
        receiver_mobile = json.loads(obj.push_range).get('receiver_mobile', '')
        mobile_list = [s.strip() for s in receiver_mobile.split(",") if s.strip()]

        return [option for m in mobile_list for option in option_user_list if m == option["phone_number"]]

    def get_app_name(self, obj):
        ding_msg_cache_map = DingMessageSerializer.get_ding_message_cache(
            queryset=self.instance,
            target=self,
            field='message_id'
        )
        return ding_msg_cache_map.get(obj.message_id, {}).get('app', {}).get('app_name', '')

