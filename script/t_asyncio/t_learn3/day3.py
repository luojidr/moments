"""
1) 成功回调
    task = loop.create_task(coro)
    task.add_done_callback(callback)  # callback 普通函数， 参数为future对象
    task2.add_done_callback(partial(callback, n=11))  # callback 有多参数

2) 调度回调
    asyncio 提供了 3 个按需回调的方法，都在 Eventloop 对象上，而且也支持参数

    2.1) call_soon 立刻回调
        call_soon 按照注册到事件循环上回调函数，按顺序回调，每个回调函数只调用一次，此外回调函数的参数在回调时被传入

    2.2) call_later 安排回调在给定的时间 (单位秒) 后执行

    2.3) call_at 安排回调在给定的时间执行，注意这个时间要基于loop.time()获取当前时间

"""
import asyncio
from functools import partial


async def a():
    await asyncio.sleep(1)
    return 'A'


def callback(future):
    print(f'Result callback: {future.result()}')


def callback2(future, n):
    # add_done_callback方法也是支持参数的，但是需要用到functools.partial
    print(f'Result callback2: {future.result()}, N: {n}')


def success_cb_main():
    loop = asyncio.get_event_loop()
    task = loop.create_task(a())
    task.add_done_callback(callback)

    task2 = loop.create_task(a())
    task2.add_done_callback(partial(callback2, n=11))

    loop.run_until_complete(asyncio.wait([task, task2]))


def make_done(future, result):
    print(f'Set to make_done: {result}')
    future.set_result(result)


async def b1():
    loop = asyncio.get_event_loop()
    future = asyncio.Future()
    loop.call_soon(make_done, future, 'the result')
    loop.call_soon(partial(print, "Hello", flush=True))
    loop.call_soon(partial(print, "Greeting", flush=True))

    print(f'Done: {future.done()}')
    await asyncio.sleep(0)
    print(f'Done: {future.done()}, Result: {future.result()}')


def call_soon_main():
    # 1. call_soon 可以用来设置任务的结果：在 mark_done 里面设置
    # 2. 通过 2 个 print 可以感受到 call_soon 支持参数
    # 3. 最重要的就是输出部分了，首先 fut.done () 的结果是 False，因为还没到下个事件循环，sleep (0) 就可以切到下次循环，
    #    这样就会调用三个 call_soon 回调，最后再看 fut.done () 的结果就是 True，
    #    而且 < code>fut.result () 可以拿到之前在 mark_done 设置的值了
    loop = asyncio.get_event_loop()
    loop.run_until_complete(b1())


async def b2():
    loop = asyncio.get_event_loop()
    fut = asyncio.Future()
    loop.call_later(2, make_done, fut, 'the result')
    loop.call_later(1, partial(print, 'Hello'))
    loop.call_later(1, partial(print, 'Greeting'))
    print(f'Done: {fut.done()}')
    await asyncio.sleep(2)
    print(f'Done: {fut.done()}, Result: {fut.result()}')


def call_later_main():
    # 注意 3 个回调的延迟时间时间要<=sleep 的，要不然还没来及的回调程序就结束了
    loop = asyncio.get_event_loop()
    loop.run_until_complete(b2())


async def b3():
    loop = asyncio.get_event_loop()
    now = loop.time()
    fut = asyncio.Future()
    loop.call_at(now + 2, make_done, fut, 'the result')
    loop.call_at(now + 1, partial(print, 'Hello', flush=True))
    loop.call_at(now + 1, partial(print, 'Greeting', flush=True))
    print(f'Done: {fut.done()}')
    # await asyncio.sleep(1)  # 有没有都可以，sleep 时间可以小于3个回调给定的时间（即sleep任意时间）
    print(f'Done: {fut.done()}, Result: {fut.result()}')


def call_at_main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(b2())


if __name__ == '__main__':
    # success_cb_main()
    # call_soon_main()
    # call_later_main()
    call_at_main()












