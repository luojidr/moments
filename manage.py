#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from config.settings import Config


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', Config.DJANGO_SETTINGS_MODULE)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    execute_from_command_line(sys.argv)

    # Docker uwsgi 启动命令
    #  run_command:
    #  ['uwsgi', '--module=config.wsgi:application', '--env',
    #  'DJANGO_SETTINGS_MODULE=config.settings.prod', '--master',
    #  '--http=0.0.0.0:8000', '--processes=2', '--logto=/tmp/uwsgi.log',
    #  '--harakiri=600', '--max-requests=1000', '--vacuum']

    # 无Nginx时, 使用 whitenoise 来管理Django的静态文件资产
    # Cmd: python manage.py collectstatic ignore directory (https://www.codenong.com/8269883/)
    # collectStaticCmd = python manage.py collectstatic
    # eg 1: {collectStaticCmd} --ignore=admin --ignore=django_extensions ...
    # eg 2: {collectStaticCmd} -i admin -i django_extensions -i rest_framework -i ckeditor -i rest_framework_swagger

    # 使用 django-compress 进一步压缩css, js文件
    # Cmd: python manage.py compress [--force]

    # 与 whitenoise 一起使用时
    # collectStaticCmd = python manage.py collectstatic
    # 1: {collectStaticCmd} -i admin -i django_extensions -i rest_framework -i ckeditor -i rest_framework_swagger
    # 2: python manage.py compress [--force]


if __name__ == '__main__':
    main()
