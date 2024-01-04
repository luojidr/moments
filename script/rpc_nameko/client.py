import cProfile
from nameko.standalone.rpc import ClusterRpcProxy
# 使用cProfile测试性能

config = {
    'AMQP_URI': "pyamqp://admin:admin013431@127.0.0.1"
}


def test():
    with ClusterRpcProxy(config) as cluster_rpc:
        rs = cluster_rpc.greet_server.hello("hellø")


if __name__ == '__main__':
    cProfile.run("test()")
