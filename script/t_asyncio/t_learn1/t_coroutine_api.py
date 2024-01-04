import time
import asyncio
from functools import partial
from collections.abc import Coroutine


async def hello(name):
    print('Hello,', name)


@asyncio.coroutine
def hello2():
    # 异步调用asyncio.sleep(1):
    yield from asyncio.sleep(1)


def is_coroutine():
    coro = hello('xxxx')
    coro2 = hello2()
    print('hello is coroutine1:', isinstance(coro, Coroutine))
    print('hello is coroutine2:', asyncio.iscoroutine(coro))

    print('hello2 is coroutine1:', isinstance(coro2, Coroutine))
    print('hello2 is coroutine2:', asyncio.iscoroutine(coro2))


async def download(url):
    # 事件循环+同步调用API
    print('start download url')
    time.sleep(2)  # 同步
    print('end download url')


async def async_download(url):
    # 事件循环+异步调用API
    print('start async download url')
    await asyncio.sleep(2)  # 异步
    print('end async download url')


async def async_download_cb(url):
    # 事件循环+异步调用API
    print('start async async_download_cb url')
    await asyncio.sleep(2)  # 异步
    print('end async async_download_cb url')
    return "hello world"  # 协程返回的结果


def callback(url, future):
    print("Callback回调了:", url)


if __name__ == '__main__':
    start = time.time()
    loop = asyncio.get_event_loop()

    tasks = [
        download('www.baidu.com'),
        download("www.baidu.com")
    ]

    async_tasks = [
        async_download('www.baidu.com'),
        async_download("www.baidu.com")
    ]

    future = asyncio.gather(async_download_cb("www.baidu.com"))
    future.add_done_callback(partial(callback, 'www.baidu.com'))

    # loop.run_until_complete(asyncio.wait(tasks))   # 4.0872s(同步)
    # loop.run_until_complete(asyncio.wait(async_tasks))   # 4.2.0032s(异步)

    # 利用partial函数包装callback，因为add_done_callback添加回调只接受一个参数,所以这里必须得用partial包装成一个函数，
    # 那相应的callback需要在增加一个参数url，而且这个url必须放在参数前面，这样的话我们就可以在回调的时候传递多个参数了。
    loop.run_until_complete(future)   # 4.2.0032s(异步)
    print(time.time() - start)

    # 注意：async_download 是函数， async_download() 才是一个协程

    # 1) loop.run_until_complete 方法的参数：
    # 1.1) asyncio.wait(coro_list)
    # 1.2) loop.create_task(coro)
    # 1.3) loop.ensure_future(coro)

    # asyncio.wait()
    # 2) 高阶API asyncio.wait 用法: 运行所有协称/Task/Future，直到他们完成，而它本身就是一个协称，
    #                              所以可以被事件循环run_until_complete调度

    # asyncio.gather()
    # 3) 高阶API asyncio.gather 用法:该函数是high-level的，就是高度抽象的，它比wait更加灵活和方便
    # 3.1) asyncio.gather 参数是一个协程或future对象的列表（或可迭代对象）
    # 3.2) 返回一个future对象

    # asyncio.run()
    # 4) asyncio.run 参数接受一个协程对象，封装了事件循环， 不需要你自己再声明 loop
    #    通常与asyncio.gather 一起使用

    # 5) 协程/Task/Future执行完后的回调
    # future = asyncio.gather(download(''))
    # future.add_done_callback(partial(callback, ""))
    # loop.run_until_complete(future)
    print("协称运行的结果：", future.result())

    is_coroutine()


