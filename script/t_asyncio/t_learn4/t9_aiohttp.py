"""
并发网络请求库 aiohttp
"""
import asyncio
import aiohttp
from aiohttp import ClientSession
from t4_async_timed import async_timed


@async_timed()
async def fetch_status(session: ClientSession, url: str) -> int:
    async with session.get(url) as resp:
        return resp.status


@async_timed()
async def fetch_status_by_timeout(session: ClientSession, url: str) -> int:
    # ClientTimeout
    #   total:      整个操作的最大秒数，包括建立连接、发送请求和读取响应
    #   connect:    如果超出池连接限制，则建立新连接或等待池中的空闲连接的最大秒数
    #   sock_connect:  为新连接连接到对等点的最大秒数，不是从池中给出的
    #   sock_read:     从对等点读取新数据部分之间允许的最大秒数。
    timeout = aiohttp.ClientTimeout(total=0.1)
    async with session.get(url, timeout=timeout) as resp:
        return resp.status


@async_timed()
async def main():
    # 默认 ClientSession 将创建最多100个连接
    async with aiohttp.ClientSession() as session:
        url: str = 'https://circle.fosun.com/api/v1/circle/common/health/check'

        # async_timed -> finished <function main at 0x00000246D72A2DC0> in 3.5712 second(s)
        # for i in range(100):
        #     status: int = await fetch_status(session, url)
        #     print(f'Coro status for {url} was {status}')

        # 性能经一部提升
        # async_timed -> finished <function main at 0x00000210F8C72DC0> in 0.8881 second(s)
        tasks = [asyncio.create_task(fetch_status(session, url)) for i in range(100)]
        for task in tasks:
            status: int = await task
            print(f'Task status for {url} was {status}')


@async_timed()
async def main_by_timeout():
    session_timeout = aiohttp.ClientTimeout(total=1, connect=0.1)
    async with aiohttp.ClientSession(timeout=session_timeout) as session:
        url: str = 'https://circle.fosun.com/api/v1/circle/common/health/check'
        status: int = await fetch_status_by_timeout(session, url)
        print(f'Status for {url} was {status}')


if __name__ == '__main__':
    # Fix to raise RuntimeError('Event loop is closed')
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # asyncio.run(main())  # Maybe raise RuntimeError('Event loop is closed')

    # 不会 raise RuntimeError('Event loop is closed')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    # loop.run_until_complete(main_by_timeout())
