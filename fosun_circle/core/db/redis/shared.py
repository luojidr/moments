from rediscluster import RedisCluster

from config.conf import RedisSharedConfig


class RedisShared(RedisCluster):
    """ Redis Cluster
        https://redis-py-cluster.readthedocs.io/en/master/
        https://www.jianshu.com/p/c00871913a41
    """

    def __init__(self, host=None, port=None, startup_nodes=None, **kwargs):
        if startup_nodes is None:
            startup_nodes = self.shared_config["startup_nodes"]

        kwargs["decode_responses"] = self.shared_config["decode_responses"]
        super(RedisShared, self).__init__(host=host, port=port, startup_nodes=startup_nodes, **kwargs)

    @property
    def shared_config(self):
        if hasattr(self, "_shared_config"):
            return self._shared_config

        prefix = "REDIS_"
        shared_config = {}

        for attr_name, attr_val in RedisSharedConfig.__dict__.items():
            if not attr_name.startswith(prefix) or not attr_name.isupper():
                continue

            attr_name = attr_name[len(prefix):].lower()
            shared_config[attr_name] = attr_val

        self.__shared_config = shared_config
        return shared_config

    def client_kill_filter(self, _id=None, _type=None, addr=None, skipme=None):
        raise NotImplementedError('Method not yet implemented')

    def atomic_transaction(self):
        """ 使用Lura进行原子事务操作 (要么全执行，要么全不执行) """

    def acquire_lock(self):
        """ 获取分布式锁 - 实现上下文管理器
        https://github.com/SPSCommerce/redlock-py
        """


