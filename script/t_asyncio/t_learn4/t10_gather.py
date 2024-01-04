import asyncio
from typing import List, Set, Coroutine
import aiohttp
from aiohttp import ClientSession
from t4_async_timed import async_timed


# @async_timed()
async def fetch_status(session: ClientSession, url: str) -> int:
    async with session.get(url) as resp:
        return resp.status


@async_timed()
async def main():
    # 默认 ClientSession 将创建最多100个连接
    async with aiohttp.ClientSession() as session:
        url_list: List[str] = [
            'https://circles.fosun.com/api/v1/circle/common/health/check'
            for i in range(100)
        ]

        coro_list: List[Coroutine] = [fetch_status(session, url) for url in url_list]

        # gather: async_timed -> finished <function main at 0x0000013D4F892CA0> in 0.9007 second(s)
        #       gather 结果是有序的，结果集是协程运行后的的结果，而不是task 或 future
        status_list: List[int] = await asyncio.gather(*coro_list, return_exceptions=True)
        print(f'Asyncio gather size: {len(status_list)}, status_list: {status_list}')

        # wait: async_timed -> finished <function main at 0x00000160671D3C10> in 0.7445 second(s)
        #       wait 结果是无序的, 结果集是task 或 future
        # task_list = [asyncio.create_task(fetch_status(session, url)) for url in url_list]
        # done_list, pending_list = await asyncio.wait(task_list)
        # print(f'Asyncio wait done_list: {done_list}, pending_list: {pending_list}')


if __name__ == '__main__':
    # Fix to raise RuntimeError('Event loop is closed')
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(), debug=True)


