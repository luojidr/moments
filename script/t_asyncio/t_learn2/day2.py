import time
import asyncio
import threading


async def do_some_work(x):
    print('Waiting: ', x)
    await asyncio.sleep(x)
    return 'Done after {}s'.format(x)


def async_run1():
    """ 协程中的并发 """
    start = time.time()
    task_list = []
    concurrency = 3

    # 第一步，创建多个协程的列表
    for i in range(concurrency):
        coro = do_some_work(i + 1)
        task = asyncio.ensure_future(coro)
        task_list.append(task)

    # 第二步，将这些协程注册到事件循环中 asyncio.wait() | asyncio.gather()
    # 两者区别： https://iswbm.com/120.html
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(task_list))        # asyncio.wait()
    # loop.run_until_complete(asyncio.gather(*task_list))   # asyncio.gather()

    print("async_run1花费的时间：", time.time() - start)

    # 查看任务结果
    for _task in task_list:
        print('Task ret: {} {} '.format(_task.get_name(), _task.result()))


async def nested_main():
    task_list = []

    # 第一步，创建多个协程的列表
    for i in range(3):
        coro = do_some_work(i + 1)
        task = asyncio.ensure_future(coro)
        task_list.append(task)

    # 【重点】：await 一个task列表（协程）
    # done_list：表示已经完成的任务
    # pending_list：表示未完成的任务
    done_list, pending_list = await asyncio.wait(task_list)
    # results = await asyncio.gather(*task_list)

    # 查看任务结果
    for _task in done_list:
        print('Task ret: {} {} '.format(_task.get_name(), _task.result()))


def async_run2():
    """ 协程中的嵌套(一个协程中await了另外一个协程) """
    loop = asyncio.get_event_loop()
    loop.run_until_complete(nested_main())


def async_run3():
    """ 协程中的状态
        Pending：创建future，还未执行
        Running：事件循环正在调用执行任务
        Done：任务执行完毕
        Cancelled：Task被取消后的状态
    """
    async def hello():
        print("Running in the loop...")
        flag = 0
        while flag < 1000:
            with open("test.txt", "a") as f:
                f.write("------")
            flag += 1
        print("Stop the loop")

    loop = asyncio.get_event_loop()
    task = loop.create_task(hello())

    # Pending：未执行状态
    print(task)
    try:
        t1 = threading.Thread(target=loop.run_until_complete, args=(task, ))
        t1.start()

        # Running：运行中状态
        time.sleep(1)
        print(task)
        t1.join()
    except KeyboardInterrupt as e:
        # 取消任务
        task.cancel()
        # Cancelled：取消任务
        print(task)
    finally:
        print(task)


def async_run4():
    """ wait有控制功能 """
    # 1)【控制运行任务数】：运行第一个任务就返回
    #   FIRST_COMPLETED ：第一个任务完全返回
    #   FIRST_EXCEPTION：产生第一个异常返回
    #   ALL_COMPLETED：所有任务完成返回 （默认选项）

    # 2)【控制时间】：运行一秒后，就返回
    # 3)【默认】：所有任务完成后返回

    pass


if __name__ == '__main__':
    # async_run1()
    # async_run2()
    async_run3()


