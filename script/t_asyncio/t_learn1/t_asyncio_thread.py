"""
到这个题目大家觉得很慌，我都协程并发处理数据了，为什么还需要线程？孰轻孰重我们当然想的清楚，
但是这里的门道就是一句话：
    我不管你异步编程多么NB，我就是想一边用异步，一边调用同步阻塞的代码，我不管我就这样用，你就说能不能办到？
    这可把我难倒了，上节课不是说了异步编程核心原则：
            要异步，所有的都要异步，
    感觉与其背道而驰啊。
经过一番研究发现：草率了，异步中可以调用同步的代码，但是吃相比较难看而已罢了。

https://mp.weixin.qq.com/s?__biz=MzUzMTUxMzYyNQ==&mid=2247484351&idx=1&sn=4a09a24bbc7a6b93684c1a1a26f4a4d3&chksm=fa402bc9cd37a2df5252aba5e4c13479ad3aee4211917768ec642d9945089145f46c4c3d0c63&cur_album_id=1939261491778551809&scene=189#wechat_redirect
asyncio中协称如何被事件循环调度的-Future/Task
Future对象：
    在asyncio中，如何才能得到异步调用的结果呢？
    先设计一个对象，异步调用执行完的时候，就把结果放在它里面，这种对象称之为未来对象。未来对象有一个result方法，
    可以获取未来对象的内部结果。还有个set_result方法，是用于设置result的。set_result设置的是什么，
    调用result得到的就是什么。Future对象可以看作下面的Task对象的容器。

Task对象：
    一个协程就是一个原生可以挂起的函数，Task则是对象协程的进一步封装，里面可以包含协程在执行时的各种状态。

Task和Future与协程的关系：
    Task是Future的派生类，它有一个核心step方法，这个方法和协程调度有关，但是这个方法只有Task独有，Future是没有的，但是Future
    有set_result方法，这个方法可以被Future和Task共同调用。
    同时Task是Future和协程之间的桥梁，因为Task执行结束的时候会调用Future的set_result方法，这样Future通过result方法就会知道
    协程运行的结果，所以说Future想要知道协程的运行结果，那么必须将协程绑定Task，这样Task才能把结果设置到Future中。

协程如何被事件循环调度：
    对于协程来说，是没有办法直接放到事件循环里面运行的，需要Task对象（任务）。而我们之前直接将协程扔进loop中是因为asyncio
    内部会有检测机制，如果是协程的话，会自动将协程包装成一个Task对象。例如：
        import asyncio

        async def coroutine():
            print("hello world")

        if __name__ == "__main__":
            loop = asyncio.get_event_loop()
            # 如何创建一个任务呢？
            task = loop.create_task(coroutine())
            loop.run_until_complete(task)

        运行结果：hello world
"""

import time
import asyncio
from concurrent.futures.thread import ThreadPoolExecutor


def run():
    # 同步阻塞代码
    time.sleep(2)


async def run1():
    # 异步代码
    await asyncio.sleep(2)


async def coroutine():
    print("hello world")


def sync_run():
    # 等同于同步下的线程池执行同步函数
    loop = asyncio.get_event_loop()
    start = time.time()
    executor = ThreadPoolExecutor()  # 初始化线程池
    tasks = []
    for i in range(100):
        task = loop.run_in_executor(executor, run)
        tasks.append(task)
    loop.run_until_complete(asyncio.wait(tasks))  # 异步调用
    print("sync_run total time: ", time.time() - start)


def async_run():
    # 纯异步
    loop = asyncio.get_event_loop()
    start = time.time()
    tasks = []
    for i in range(100):
        tasks.append(run1())
    loop.run_until_complete(asyncio.wait(tasks))
    print("async_run total time: ", time.time() - start)


def run_coro():
    loop = asyncio.get_event_loop()
    # 如何创建一个任务呢？
    task = loop.create_task(coroutine())
    loop.run_until_complete(task)


if __name__ == '__main__':
    # sync_run()
    # async_run()
    run_coro()
