import json
import re
import traceback
from functools import wraps
from urllib.parse import urlparse

import requests
from pyquery import PyQuery

from django.utils import timezone

from config.celery import celery_app
from fosun_circle.libs.decorators import to_retry
from fosun_circle.libs.log import task_logger as logger


def wrap_exception(func):
    @wraps(func)
    def deco(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
            return ret
        except Exception as e:
            logger.error("task_spider_news => %s err: %s", func.__name__, e)
            logger.error(traceback.format_exc())

    return deco


class SpiderNews:
    date_regex = re.compile(r'\d{4}-\d\d-\d\d', re.S | re.M)
    SALT_KEY = 'Gtr4F'
    TOKEN = 'vt10llXm5ioP5Ryx'
    SAVE_API = 'https://www.fosunlink.com'

    def __init__(self, url, lang, start_date=None):
        self._url = url
        self._lang = lang
        self._start_date = start_date

    @to_retry
    @wrap_exception
    def get_html(self, url=None):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/115.0.0.0 Safari/537.36',
        }
        resp = requests.get(url=url or self._url, headers=headers)
        return resp.content

    @wrap_exception
    def get_news_url_list(self,):
        news_list = []
        today = timezone.datetime.today().strftime('%Y-%m-%d')

        result = urlparse(self._url)
        base_url = result.scheme + '://' + result.netloc
        doc = PyQuery(url=self._url, encoding='utf-8')

        for node in doc('div.news_list #ajaxList li').items():
            new_date = node('.index_time').text()
            new_title = node('h3.fnt_26.line36').text()
            new_url = node('.news_more a').attr('href')

            match = self.date_regex.search(new_date)
            news_date = match and match.group(0)

            skip_cond1 = self._start_date is None and news_date != today
            skip_cond2 = self._start_date and news_date < self._start_date

            if skip_cond1 or skip_cond2:
                logger.info('New title: %s date: %s, url: %s => was skip', new_title, new_date, new_url)
                continue

            new_url = new_url.strip()
            news_list.append(base_url + new_url)

        return news_list

    @wrap_exception
    def parse_html(self, url):
        result = urlparse(url)
        base_url = result.scheme + '://' + result.netloc

        document = PyQuery(url=url, encoding='utf-8')
        title = document('h1.fnt_36').text().strip()

        news_date = document('span.posttime').text().strip()
        match_date = self.date_regex.search(news_date)
        news_date = match_date and match_date.group(0)

        summary = ''
        summary_doc = document('div.edit_con_original.edit-con-original p')

        # 处理新闻摘要
        for index, node in enumerate(summary_doc.items()):
            summary = (node.text() or "").strip()

            if len(summary) > 50:
                break

        # 处理正文(图片链接)
        content_doc = document('div.edit_con_original.edit-con-original')

        for img_node in content_doc('img').items():
            img_url = img_node.attr('src')

            if not img_url or img_url.startswith('http'):
                continue

            if img_url.startswith('/'):
                img_node.attr('src', base_url + img_url)

        content = content_doc.html()
        return dict(
            title=title, news_date=news_date,
            summary=summary, content=content, lang=self._lang
        )

    @wrap_exception
    def save_to_fosunlink(self, data):
        logger.info('SpiderNews.save_to_fosunlink => Data: %s', data)
        headers = {
            "Content-Type": "application/json",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/115.0.0.0 Safari/537.36',
        }

        r = requests.post(self.SAVE_API, data=json.dumps(data), headers=headers)
        logger.info('SpiderNews.save_to_fosunlink => StatusCode: $s, Ret: %s', r.status_code, r.content)


@celery_app.task
def spider_news_to_fosunlink(start_date=None, **kwargs):
    """ Fosunlink 新闻自动爬取(暂时未用到) """
    news_urls = [
        ('https://www.fosun.com/news/news.html', 'zh_cn'),      # 中文简体
        ('https://zh.fosun.com/news/index.html', 'zh_tw'),      # 中文繁体
        ('https://en.fosun.com/news/index.html', 'en'),         # 英文
        ('https://www.fosun.com/jp/news/index.html', 'ja'),     # 日语
        ('https://www.fosun.com/fr/news/index.html', 'fr'),     # 法语
        ('https://www.fosun.com/de/news/index.html', 'de'),     # 德语
        ('https://www.fosun.com/pt/news/index.html', 'pt'),     # 葡萄牙语
    ]

    for url, lang in news_urls:
        sn = SpiderNews(url=url, lang=lang, start_date=start_date)
        news_url_list = sn.get_news_url_list()

        for each_url in news_url_list:
            news_data = sn.parse_html(url=each_url)
            sn.save_to_fosunlink(data=news_data)

