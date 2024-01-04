import asyncio

# https://mp.weixin.qq.com/s/fCWQAT-O27mbi8UvKIrjWw

# 获取实例化的事件循环（可能是正在执行的）
loop1 = asyncio.get_event_loop()
# 获取当前正在运行的事件循环实例
loop2 = asyncio.get_running_loop()
print(loop1)
print(loop2)

# 创建一个新的循环实例
#   存在问题
#       由于 asyncio 中的循环与循环策略的概念紧密耦合，因此不建议通过循环构造函数创建循环实例。否则，我们可能会遇到范围问题，
#       因为全局 asyncio.get_event_loop 函数只检索自己创建的循环或通过 asyncio.set_event_loop 设置的循环。
#   解决方案
#       要创建一个新的事件循环实例，我们将使用 asyncio.new_event_loop 的 API
#       注意：此 api 不会更改当前安装的事件循环，但会初始化（asyncio）全局事件循环策略 - 如果之前未初始化的话。
#       另一个问题是我们将新创建的循环附加到事件循环策略的观察程序，以确保我们的事件循环监视 UNIX 系统上新生成的子进程的终止








