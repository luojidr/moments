"""
asyncio 并发的正确 / 错误姿势:
最好的姿势就是（自己理解的）:
    asyncio.wait([coro1, coro2, ...])
    asyncio.gather(*[coro1, coro2, ...])

"""
import time
import asyncio


async def a():
    print('Suspending a')
    await asyncio.sleep(3)
    print('Resuming a')


async def b():
    print('Suspending b')
    await asyncio.sleep(1)
    print('Resuming b')


async def s1():
    # await 后直接跟协程，同步
    await a()
    await b()


def show_perf(func):
    print('*' * 20)
    start = time.perf_counter()
    asyncio.run(func())
    print(f'{func.__name__} Cost: {time.perf_counter() - start}')


async def c1():
    await asyncio.gather(a(), b())  # 异步
    # await asyncio.wait([a(), b()])  # 异步


async def c3():
    task1 = asyncio.create_task(a())
    # task1 = asyncio.ensure_future(a())  # ensure_future 的结果也是Task对象
    task2 = asyncio.create_task(b())
    # task2 = asyncio.ensure_future(b())

    # await 后面跟 Task对象，异步
    await task1
    await task2


async def c4():
    task = asyncio.create_task(b())
    # task2 = asyncio.create_task(b())
    # 异步：第一个await后必须是协程，才有异步效果
    await a()
    await task
    # await task2


async def c5():
    task = asyncio.create_task(b())
    # 同步：第一个await后Task对象，同步效果
    await task
    await a()


async def s2():
    # await 后直接跟 asyncio.create_task(...) 同步
    await asyncio.create_task(a())
    await asyncio.create_task(b())


if __name__ == '__main__':
    # show_perf(s1)    # s1 Cost: 4.0039639000000005
    # show_perf(c1)    # c1 Cost: 3.0060238
    # show_perf(c3)    # c3 Cost: 3.0032561
    # show_perf(c4)    # c4 Cost: 3.0078058
    # show_perf(c5)    # c5 Cost: 4.0047058
    show_perf(s2)    # s2 Cost: 4.0025566




