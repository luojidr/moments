"""
使用装饰器测量协程执行时间
"""
import time
import asyncio
import functools
from typing import Callable, Any


def async_timed():
    def wrapper(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapped(*args, **kwargs) -> Any:
            print(f'async_timed -> starting {func} with args {args} {kwargs}')
            start = time.time()

            try:
                return await func(*args, **kwargs)
            finally:
                end = time.time()
                total = end - start
                print(f'async_timed -> finished {func} in {total:.4f} second(s)')

        return wrapped

    return wrapper


@async_timed()
async def delay(delay_seconds: int) -> int:
    print(f'\tsleeping for {delay_seconds} second(s)')
    await asyncio.sleep(delay_seconds)
    print(f'\tfinished sleeping for {delay_seconds} second(s)')
    return delay_seconds


@async_timed()
async def main():
    task1 = asyncio.create_task(delay(2))
    task2 = asyncio.create_task(delay(3))

    await task1
    await task2


if __name__ == '__main__':
    asyncio.run(main())
