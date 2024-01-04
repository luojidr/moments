import os
import django

# os.environ.setdefault("APP_ENV", "PROD")
env = os.environ.get('APP_ENV', 'DEV')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.%s" % env.lower())
django.setup()

from fosun_circle.core.db.migrate import MigrateDatabase

# MigrateDatabase('default', 'migrate_dest').get_related_models(QuestionnaireModel)
MigrateDatabase(
    'default', 'migrate_dest',
    chunk_size=2000,
    ignore_tables=['circle_ding_msg_push_log']
).migrate()
