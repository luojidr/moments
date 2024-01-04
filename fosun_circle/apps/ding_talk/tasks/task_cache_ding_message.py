import traceback
from multiprocessing.dummy import Pool as ThreadPool

from django_redis import get_redis_connection

from config.celery import celery_app
from fosun_circle.libs.log import task_logger as logger
from ding_talk.serializers import PushDingMsgLogSerializer

step_size = 2000
expire_time = 24 * 60 * 60

expire_keys_lua = """
for i=1, ARGV[1], 1 do
    redis.call("EXPIRE", KEYS[i], ARGV[2]);
end
"""


def bulk_insert_fingerprints(bulk_mappings):
    """ 命令行：
    redis-cli -h [ip] -p [port]-a [pwd] keys "key_*" | xargs -i redis-cli -h ip -p [port] -a [pwd] expire {}[秒]
    rg: redis-cli -h 127.0.0.1 -p 6481 -a 123456 keys "falconSing*" | xargs -i redis-cli -h 127.0.0.1 -p 6481 -a 123456 expire {} 3600
    """
    redis_conn = get_redis_connection()

    try:
        if not isinstance(bulk_mappings, dict):
            raise ValueError("bulk_mappings must be dict")

        redis_conn.mset(bulk_mappings)
        cmd = redis_conn.register_script(expire_keys_lua)
        cmd(keys=list(bulk_mappings.keys()), args=[len(bulk_mappings), expire_time])

        # with redis_conn.pipeline(transaction=False) as p:
        #     for key, value in bulk_mappings.items():
        #         # redis_conn.set(key, value, expire_time)
        #         redis_conn.expire(key, expire_time)
        #
        #     p.execute()  # 批量执行

        logger.info("bulk_insert_fingerprints ok: cnt:%s", len(bulk_mappings))
    except Exception as e:
        traceback.format_exc()
        logger.error("bulk_set_fingerprint error: %s", e)
        logger.error(traceback.format_exc())


@celery_app.task
def cache_ding_message_fingerprint(**kwargs):
    """ 钉钉消息体和已发记录缓存到Redis中 """
    # pool = ThreadPool()
    try:
        serializer = PushDingMsgLogSerializer()

        # msg_log_fingerprint_dict = serializer.get_sent_message_log_fingerprints()
        msg_log_fingerprint_dict = []
        message_body_fingerprint_mappings = serializer.get_message_body_fingerprint_mappings()

        logger.info("cache_ding_message_fingerprint msg_log_fingerprint size:%s", len(msg_log_fingerprint_dict))
        logger.info("cache_ding_message_fingerprint ding_message_fingerprint size:%s", len(message_body_fingerprint_mappings))

        bulk_body_mappings = []
        body_fingerprint_dict = {}

        # 钉钉消息体的指纹与主键的映射
        for index, (fingerprint, ding_msg_id) in enumerate(message_body_fingerprint_mappings.items(), 1):
            key = serializer.DING_MSG_BODY_KEY % fingerprint
            body_fingerprint_dict[key] = ding_msg_id

            if len(body_fingerprint_dict) % step_size == 0:
                bulk_body_mappings.append(dict(body_fingerprint_dict))
                body_fingerprint_dict = {}
        else:
            bulk_body_mappings.append(dict(body_fingerprint_dict))

        # 批量插入redis, 可能引起 BrokenPipeError
        # pool.map(bulk_insert_fingerprints, bulk_body_mappings)

        bulk_log_mappings = []
        log_fingerprint_dict = {}

        # 已发送钉钉消息记录的redis缓存
        for index, (fingerprint, log_item) in enumerate(msg_log_fingerprint_dict.items(), 1):
            app_id = log_item.get("app_id")
            ding_msg_id = log_item.get("ding_msg_id")
            receiver_mobile = log_item.get("receiver_mobile")

            if app_id and receiver_mobile:
                key = serializer.DING_MSG_LOG_KEY % (app_id, ding_msg_id, receiver_mobile)
                log_fingerprint_dict[key] = fingerprint

                if len(log_fingerprint_dict) % step_size == 0:
                    bulk_log_mappings.append(dict(log_fingerprint_dict))
                    log_fingerprint_dict = {}
        else:
            bulk_log_mappings.append(dict(log_fingerprint_dict))

        # 批量插入redis, 可能引起 BrokenPipeError
        # [message.py:133] [message:ack_log_error] CRITICAL Couldn't ack 17, reason:BrokenPipeError(32, 'Broken pipe')

        # pool.map(bulk_insert_fingerprints, bulk_log_mappings)
        #
        # pool.close()
        # pool.join()

        bulk_mappings_list = []
        bulk_mappings_list.extend(bulk_body_mappings)
        bulk_mappings_list.extend(bulk_log_mappings)

        for bulk_mappings in bulk_mappings_list:
            bulk_insert_fingerprints(bulk_mappings)
            pass
    except Exception as e:
        logger.error("cache_ding_message_fingerprint err:%s", e)
        logger.error(traceback.format_exc())

