import threading

local = threading.local()
print(local.__dict__)


def start(i):
    ident_id = threading.get_ident()
    local.ident_id = i
    print("ident_id:%s, i:%s" % (ident_id, local.ident_id))


if __name__ == "__main__":
    p = []

    for i in range(10):
        t = threading.Thread(target=start, args=(i,))
        t.start()
        p.append(t)

    for pp in p:
        pp.join()

    print(threading.get_ident(), local.__dict__, local.ident_id)
