from nameko.rpc import rpc


class GreetServer(object):
    name = "greet_server"

    @rpc
    def hello(self, name):
        return name
    # 使用@rpc 装饰器定义RPC服务