import time


# 生成器的嵌套:调用方, 委托生成器, 子生成器


def avarage_gen():
    # 子生成器
    total = 0
    count = 0
    average = 0

    while True:
        new_num = yield average  # yield 与 send 对应

        count += 1
        total += new_num
        average = total / count


# 子生成器
def average_gen2():
    total = 0
    count = 0
    average = 0
    while True:
        new_num = yield average
        if new_num is None:
            break
        count += 1
        total += new_num
        average = total/count

    # 每一次return，都意味着当前协程结束。
    return total, count, average


def proxy_gen():
    # 委托生成器: 在调用方与子生成器之间建立一个双向通道
    while True:
        yield from avarage_gen()


# 委托生成器
def proxy_gen2():
    while True:
        # 只有子生成器要结束（return）了，yield from左边的变量才会被赋值，后面的代码才会执行。
        total, count, average = yield from average_gen2()
        print("计算完毕！！\n总共传入 {} 个数值， 总和：{}，平均数：{}".format(count, total, average))


def main():
    # 调用方
    calc_average = proxy_gen()
    next(calc_average)            # 启动生成器 或 calc_average.send(None)
    print(calc_average.send(10))  # 打印：10.0
    print(calc_average.send(20))  # 打印：15.0
    print(calc_average.send(30))  # 打印：20.0


# 调用方
def main2():
    calc_average = proxy_gen2()
    next(calc_average)            # 预激协程
    print(calc_average.send(10))  # 打印：10.0
    time.sleep(3)
    print(calc_average.send(20))  # 打印：15.0
    print(calc_average.send(30))  # 打印：20.0
    calc_average.send(None)      # 结束协程
    # 如果此处再调用calc_average.send(10)，由于上一协程已经结束，将重开一协程


if __name__ == '__main__':
    # main()
    main2()

