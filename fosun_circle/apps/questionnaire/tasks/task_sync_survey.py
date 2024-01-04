import traceback
from multiprocessing.dummy import Pool as ThreadPool

from django_redis import get_redis_connection

from config.celery import celery_app
from fosun_circle.libs.log import task_logger as logger
from fosun_circle.libs.utils.crypto import AESCipher
from questionnaire.service import SurveyVoteService
from questionnaire.models import QuestionnaireModel


@celery_app.task
def sync_survey(user_id=None, **kwargs):
    """ 同步问卷 """
    params = dict(page=1, size=1000, state='open')
    data = SurveyVoteService().get_survey_list(params)
    ref_md5_fmt = "{ref_id}-{title}-{desc}-{img_url}-{status}"

    queryset = QuestionnaireModel.objects.filter(source='ihcm', is_del=False).all()
    ref_md5_dict = {obj.ref_md5: obj for obj in queryset}

    for item in data.get('list', []):
        kwargs = dict(
            ref_id=item.get('questionnaire_id'), title=item.get('title', ''),
            desc=item.get('desc', ''), img_url=item.get('img_url', ''),
            status=item.get('state', ''),
        )
        ref_md5 = AESCipher.crypt_md5(ref_md5_fmt.format(**kwargs))
        attrs = dict(
            user_id=user_id, source='ihcm', save_time=item.get('createTime'),
            creator=item.get('creator') or '', ref_md5=ref_md5, **kwargs
        )

        if ref_md5 not in ref_md5_dict:
            obj = QuestionnaireModel(**attrs)
        else:
            obj = ref_md5_dict[ref_md5]
            obj.save_attributes(**attrs)
            del ref_md5_dict[ref_md5]

        obj.save()

    queryset.filter(ref_md5__in=list(ref_md5_dict.keys())).update(is_del=True, status='close')


