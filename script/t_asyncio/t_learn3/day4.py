"""
同步逻辑，怎么利用 asyncio 实现并发呢？
    答案是用run_in_executor。在一开始我说过开发者创建 Future 对象情况很少，主要是用run_in_executor，
    就是让同步函数在一个执行器 (executor) 里面运行:
"""
import time
import asyncio
import concurrent
from functools import partial


def a():
    time.sleep(1)
    return 'A'


async def b():
    await asyncio.sleep(1)
    return 'B'


def show_perf(func):
    print('*' * 20)
    start = time.perf_counter()
    asyncio.run(func())
    print(f'{func.__name__} Cost: {time.perf_counter() - start}')


async def c1():
    # 异步、同步，混合使用
    # 可以看到用run_into_executor可以把同步函数逻辑转化成一个协程，且实现了并发。
    # 这里要注意细节，就是函数 a 是【普通函数】，不能写成协程

    size = 30
    tasks = []
    loop = asyncio.get_running_loop()

    for i in range(size):
        # run_in_executor 参数 executor 被传入None, 表示：选择默认的 executor
        # 默认线程执行器：concurrent.futures.ThreadPoolExecutor
        task = loop.run_in_executor(None, a)
        tasks.append(task)

    await asyncio.gather(*(tasks + [b()]))
    # await asyncio.gather(b(), *tasks)  # 与上面等价


async def c3():
    # 使用进程池来是想并发（同步+异步）
    size = 30
    tasks = []
    loop = asyncio.get_running_loop()

    with concurrent.futures.ProcessPoolExecutor() as e:
        for i in range(size):
            # run_in_executor 参数 executor 被传入None, 表示：选择默认的 executor
            # 默认线程执行器：concurrent.futures.ThreadPoolExecutor
            task = loop.run_in_executor(e, a)
            tasks.append(task)

        res = await asyncio.gather(*(tasks + [b()]))
        # res = await asyncio.gather(b(), *tasks)
        print(res)


if __name__ == '__main__':
    # show_perf(c1)       # c1 Cost: 3.0189645
    show_perf(c3)       # c3 Cost: 5.0759308, 线程池好像比进程池稍快点




