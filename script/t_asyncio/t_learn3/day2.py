"""
1) asyncio.gather:
    gather 的意思是「搜集」，也就是能够收集协程的结果，而且要注意，它会按输入协程的顺序保存的对应协程的执行结果。

2) asyncio.wait:
    done, pending = await asyncio.wait([a(), b()])
    返回值有 2 项，第一项表示完成的任务列表 (done)，第二项表示等待 (Future) 完成的任务列表 (pending)，
    每个任务都是一个 Task 实例，由于这 2 个任务都已经完成，所以可以执行task.result()获得协程返回值。

这里总结下它俩的区别的第一层区别:
    (1) asyncio.gather 封装的 Task 全程黑盒，只告诉你协程结果。
    (2) asyncio.wait 会返回封装的 Task (包含已完成和挂起的任务)，如果你关注协程执行结果你需要从对应 Task 实例里面用 result 方法自己拿。

    为什么说「第一层区别」，asyncio.wait看名字可以理解为「等待」，所以返回值的第二项是 pending 列表，
    但是看上面的例子，pending 是空集合，那么在什么情况下，pending 里面不为空呢？这就是第二层区别：asyncio.wait支持选择返回的时机。

    (3) asyncio.wait支持一个接收参数 【return_when】，在默认情况下，asyncio.wait会等待全部任务完成 (return_when='ALL_COMPLETED')，
    它还支持 FIRST_COMPLETED（第一个协程完成就返回）和 FIRST_EXCEPTION（出现第一个异常就返回）

3) asyncio.create_task vs loop.create_task vs asyncio.ensure_future
    3.1) asyncio.create_task: 完全等价 loop.create_task
        参数：是一个协程

    3.2) asyncio.ensure_future：
        参数：除了接受协程，还可以是 Future 对象或者 awaitable 对象
            1.如果参数是协程，其实底层还是用的 loop.create_task，返回 Task 对象
            2.如果是 Future 对象会直接返回
            3.如果是一个 awaitable 对象会 await 这个对象的__await__方法，再执行一次 ensure_future，最后返回 Task 或者 Future

4) asynccontextmanager
    async 版本的 with 要用async with，另外要注意yield await func()这句，相当于 yield +await func()

"""


import time
import asyncio
from contextlib import asynccontextmanager


async def a():
    print('Suspending a')
    await asyncio.sleep(3)
    print('Resuming a')
    return 'a'


async def b():
    print('Suspending b')
    await asyncio.sleep(1)
    print('Resuming b')
    return 'b'


async def main():
    return_value_a, return_value_b = await asyncio.gather(a(), b())
    print(return_value_a, return_value_b)


@asynccontextmanager
async def async_timed(func):
    start = time.perf_counter()
    yield await func()
    print(f'Cost: {time.perf_counter() - start}')


async def s1():
    return await asyncio.gather(a(), b())


async def async_main():
    async with async_timed(s1) as rv:
        print(f'Result: {rv}')


# asyncio.run(main())
asyncio.run(async_main())
