import logging
import environ

env = environ.Env()
logger = logging.getLogger("django")
APP_ENV = env.str("APP_ENV", "DEV")

logger.info("Ding talk use APP_ENV: %s", APP_ENV)


class DingTalkConfig(object):
    """ 仅限的钉钉配置 (数智助理) """
    if APP_ENV == 'DEV':
        DING_AGENT_ID = 2716771760
        DING_CORP_ID = ""
        DING_APP_KEY = ""
        DING_APP_SECRET = ""
    else:
        DING_AGENT_ID = 941215726
        DING_CORP_ID = ""
        DING_APP_KEY = ""
        DING_APP_SECRET = ""

    IHCM_SURVEY_HOST = ""
    # 星集团总部部门ID
    DING_FOSUN_GROUP_HEAD_ROOT_ID = ""

