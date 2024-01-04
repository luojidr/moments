import json
import logging

from django.conf import settings
from django.db import DatabaseError, NotSupportedError

from users.models import BbsUserModel
from users.models import OdooDingDepartmentModel as DingDepartmentModel

logger = logging.getLogger("django")
logger.info("DATABASE_APPS_ROUTER_MAPPING: %s" % json.dumps(settings.DATABASE_APPS_ROUTER_MAPPING, indent=4))


class DatabaseRouter(object):
    """ MySQL database master from slave """

    no_logging_app_label = ["silk", "django_celery_beat"]
    databases_mapping = settings.DATABASES
    apps_router_mapping = settings.DATABASE_APPS_ROUTER_MAPPING

    def db_for_write(self, model, **hints):
        """ Write Database """
        app_label = model._meta.app_label
        model_label = model._meta.label
        model_name = model._meta.model_name

        # 特殊处理: BbsUserModel 数据源在其他数据库
        if model_label == BbsUserModel._meta.label:
            raise NotSupportedError("BBS人员表不允许修改")
        elif model_name.startswith("odoo") or "intf_" in model._meta.db_table:
            raise NotSupportedError("钉钉部门表不允许修改")

        if app_label not in self.apps_router_mapping:
            raise DatabaseError("`DATABASE_APPS_ROUTER_MAPPING` config not exist app: %s" % app_label)

        if app_label not in self.no_logging_app_label and settings.DEBUG:
            logger.info("DatabaseRouter.db_for_write() => model use db: %s, app_label: %s\n"
                        % (self.apps_router_mapping[app_label], app_label)
                        )

        return self.apps_router_mapping[app_label]

    def db_for_read(self, model, **hints):
        """ Read Database """
        app_label = model._meta.app_label
        model_label = model._meta.label                 # 'users.OdooDingDepartmentModel'
        model_name = model._meta.model_name             # 'odoodingdepartmentmodel'
        model_object_name = model._meta.object_name     # 'OdooDingDepartmentModel'

        # 特殊处理: BbsUserModel 数据源在其他数据库
        if model_label == BbsUserModel._meta.label:
            return "bbs_user"
        elif model_name.startswith("odoo") or "intf_" in model._meta.db_table:
            return "ding_department"

        if app_label not in self.apps_router_mapping:
            raise DatabaseError("`DATABASE_APPS_ROUTER_MAPPING` config not exist app: %s" % app_label)

        db_slave = self.apps_router_mapping[app_label] + "_slave"

        if db_slave not in self.databases_mapping:
            raise DatabaseError("`DATABASES` config not exist db: %s" % db_slave)

        if app_label not in self.no_logging_app_label and settings.DEBUG:
            logger.info("DatabaseRouter.db_for_read() => model use db: %s, app_label: %s\n" % (db_slave, app_label))

        return db_slave

    def allow_relation(self, obj1, obj2, **hint):
        """ Object whether to run the association operation """
        return True  # 需要注意一下原理(当两个表有关联时，外键，多对多)

    def allow_syncdb(self, db, model):
        return None

    def allow_migrate(self, db, app_label, model=None, **hints):
        """ Make sure the auth app only appears in the 'auth_db' database."""

        if app_label in self.apps_router_mapping:
            if settings.DEBUG:
                logger.info("DatabaseRouter.allow_migrate() 001 => db1:{}, app_label:{}, "
                            "db2:{}".format(db, app_label, self.apps_router_mapping[app_label]))
            return db == self.apps_router_mapping[app_label]
        else:
            if settings.DEBUG:
                logger.info("DatabaseRouter.allow_migrate() 002 => db:{}, app_label:{}, "
                            "model:{}, hints: {}".format(db, app_label, model, hints))

        return None
