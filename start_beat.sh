nohup python3 manage.py runserver 0.0.0.0:8000 > /tmp/tmp.log 2>&1 &
celery -A config.celery beat -l info