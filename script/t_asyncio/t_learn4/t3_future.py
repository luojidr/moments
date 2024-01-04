"""
Future
"""
import asyncio
from asyncio import Future


def test_future():
    f = Future()
    print(f'1 Is my future done? => {f.done()}')  # not Done

    f.set_result(101)
    print(f'2 Is my future done? => {f.done()}')  # Done


def make_request() -> Future:
    future = Future()
    asyncio.create_task(set_future_value(future))
    return future


async def set_future_value(future) -> None:
    await asyncio.sleep(1)
    future.set_result(42)


async def main_future():
    future = make_request()
    print(f'Is the future done? {future.done()}')
    value = await future  # Future 未被 set_result 之前会被一直阻塞
    print(f'Is the future done? {future.done()}')
    print(f'value: {value}')


asyncio.run(main_future())
