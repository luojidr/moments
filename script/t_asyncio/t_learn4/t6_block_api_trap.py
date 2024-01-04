"""
使用 asyncio ,那么必须使用所有和 IO 相关的异步库，否则程序会执行同步那样，没有任何性能提高
"""
import asyncio
import requests

from script.t_asyncio.t_learn4.t4_async_timed import async_timed, delay


@async_timed()
async def block_get():
    url = 'https://www.news.cn/politics/leaders/2023-09/18/c_1129869373.htm'
    r = requests.get(url)  # 同步阻塞库

    return r.status_code


@async_timed()
async def main():
    task1 = asyncio.create_task(block_get())
    task2 = asyncio.create_task(block_get())
    task3 = asyncio.create_task(block_get())

    await task1
    await task2
    await task3


if __name__ == '__main__':
    # 因为 requests 是阻塞的，执行了3次，但总耗时大致是3次独立阻塞请求丁综合，没有任何并发优势
    asyncio.run(main())
