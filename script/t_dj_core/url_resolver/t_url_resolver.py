import os.path
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.conf import settings
from django.urls.resolvers import URLResolver, RegexPattern, RoutePattern


def get_resolver(urlconf=None):
    if urlconf is None:
        urlconf = settings.ROOT_URLCONF
    return _get_cached_resolver(urlconf)


def _get_cached_resolver(urlconf=None):
    return URLResolver(RegexPattern(r'^/'), urlconf)


if __name__ == "__main__":
    # resolver = get_resolver()
    #
    # for pattern in resolver.url_patterns:
    #     print(pattern)
    #
    # path = "/api/v1/circle/ding/apps/message/list"
    # resolver_match = resolver.resolve(path=path)
    # print("resolver_match:", resolver_match)

    rp = RegexPattern(r"/kpi/(?P<user_id>\d+?)/(?P<path>.+)$")
    print(rp.match("/kpi/12502/x_css/selectors"))
