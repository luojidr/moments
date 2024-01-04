import re
import json

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.utils.html import strip_spaces_between_tags


class SpacelessMiddleware(MiddlewareMixin):
    """  Remove Spaces between HTML tags with Spaceless """
    force_spaceless = False
    HTML_CONTENT_TYPE = 'text/html'
    JSON_CONTENT_TYPE = 'application/json'

    SPACE_REGEX = re.compile(r' +', re.M | re.S)
    LINE_BREAK_REGEX = re.compile(r'\n', re.M | re.S)
    COMMENT_REGEX = re.compile(r'<!--.*?-->', re.M | re.S)
    VUE_TEMPLATE_REGEX = re.compile(r'<template>.*?</template>', re.M | re.S)

    def can_spaceless(self, response, is_html=False, is_json=False):
        content_type = response.get('Content-Type')

        if not content_type:
            return False

        if is_html:
            return self.HTML_CONTENT_TYPE in content_type

        if is_json:
            return self.JSON_CONTENT_TYPE in content_type

        return False

    def is_hybrid(self, response):
        """ A hybrid of html and json """
        # Mixed Content maybe have Html to Vue
        try:
            if self.can_spaceless(response, is_json=True):
                if self.VUE_TEMPLATE_REGEX.search(response.content.decode()):
                    data = json.loads(response.content)
                    if 'html' in data:
                        return True
        except json.JSONDecodeError:
            pass

        return False

    def clean_whitespaces(self, content, is_vue=False):
        if isinstance(content, bytes):
            content = content.decode()

        content = strip_spaces_between_tags(content.strip())        # remove HTML spaces between tags
        content = self.COMMENT_REGEX.sub("", content)               # remove HTML comment, like, eg <!--...-->
        content = self.SPACE_REGEX.sub(" ", content)                # remove HTML verbose spaces

        if is_vue:
            content = self.LINE_BREAK_REGEX.sub("", content)        # remove linebreak

        return content

    def process_response(self, request, response):
        if response.status_code == 200:
            if self.can_spaceless(response, is_html=True):
                response.content = self.clean_whitespaces(response.content)
            elif self.is_hybrid(response):
                hybrid_data = json.loads(response.content)
                content = self.clean_whitespaces(hybrid_data.pop('html'), is_vue=True)
                response.content = json.dumps(dict(hybrid_data, html=content))

        return response
