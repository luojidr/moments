import selectors
import socket
from selectors import SelectorKey
from typing import List, Tuple


selector = selectors.DefaultSelector()

address = ('127.0.0.1', 8080)
server_socket = socket.socket()
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.setblocking(False)  # 设置非阻塞的套接字
server_socket.bind(address)
server_socket.listen()

selector.register(server_socket, selectors.EVENT_READ)

while True:
    # 创建一个将在1秒后超时的选择器
    events: List[Tuple[SelectorKey, int]] = selector.select(timeout=1)

    if len(events) == 0:
        print('No events, waiting a bit more!')

    for event, _ in events:
        event_socket = event.fileobj  # 获取时间的套接字，该套接字存储在fileobj字段中。

        # 如果时间套接字与服务套接字相同，我们就知道这事一次连接尝试
        if event_socket == server_socket:
            connection, address = server_socket.accept()
            connection.setblocking(False)
            print(f'I got a connection: {connection} from address: {address}')

            # 注册与选择器链接的客户端
            selector.register(connection, selectors.EVENT_READ)
        else:
            # 如果时间套接字不是服务器套接字，则从客户端接收数据，并将其回显
            data = event_socket.recv(1024)
            print(f'I got data: {data}')
            event_socket.send(data)







