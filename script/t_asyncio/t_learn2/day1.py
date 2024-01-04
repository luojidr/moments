"""
重要概念：
event_loop 事件循环：
    程序开启一个无限的循环，程序员会把一些函数（协程）注册到事件循环上。当满足事件发生的时候，调用相应的协程函数。

coroutine 协程：
    协程对象，指一个使用async关键字定义的函数，它的调用不会立即执行函数，而是会返回一个协程对象。
    协程对象需要注册到事件循环，由事件循环调用。

future 对象： 代表将来执行或没有执行的任务的结果。它和task上没有本质的区别

task 任务：
    一个协程对象就是一个原生可以挂起的函数，任务则是对协程进一步封装，其中包含任务的各种状态。
    Task 对象是 Future 的子类，它将 coroutine 和 Future 联系在一起，将 coroutine 封装成一个 Future 对象。

async/await 关键字：
    python3.5 用于定义协程的关键字，async定义一个协程，await用于挂起阻塞的异步调用接口。其作用在一定程度上类似于yield。
"""
import time
import asyncio


async def hello(name):
    print('Hello,', name)


def async_run():
    # 定义协程对象
    coroutine = hello("World")

    # 定义事件循环对象容器
    loop = asyncio.get_event_loop()

    # 将协程转为task任务或future
    task = loop.create_task(coroutine)
    # task = asyncio.ensure_future(coroutine)

    # 将task任务扔进事件循环对象中并触发
    loop.run_until_complete(task)


def vs_yield_from():
    # 1) yield from 不能出现在关键字async定义的函数里
    # 2) yield from 后面可接 可迭代对象，也可接future对象/协程对象
    pass


def vs_await():
    # 1) await 使用必须在关键字async定义的函数里，要么不使用，不能使用在普通函数里
    # 1) await 后面必须要接 future对象/协程对象
    pass


async def _sleep(x):
    # time.sleep(2)  # 异步中使用同步方法，没有性能提高,与通不一样
    await asyncio.sleep(2)  # 模拟IO阻塞，让CPU主动挂起（暂停）
    return '{}暂停了2秒！'.format(x)


def callback(future):
    # print(dir(future))
    # print(future.get_name())
    print('{}这里是回调函数，获取返回结果是：{}'.format(future.get_name(), future.result()))


def bind_callback():
    """ 绑定回调函数 """
    start = time.time()
    task_list = []

    for i in range(10):
        coroutine = _sleep(i)
        task = asyncio.ensure_future(coroutine)

        # 添加回调函数
        task.add_done_callback(callback)
        task_list.append(task)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(task_list))
    print("花费的时间：", time.time() - start)


if __name__ == '__main__':
    bind_callback()

