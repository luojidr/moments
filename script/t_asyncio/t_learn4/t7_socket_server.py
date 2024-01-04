"""
使用 Socket 模拟网络 IO ,学习和进一步深入理解 asyncio 异步并发
"""
import socket
import socketserver
import asyncio


def run_server_block_socket():
    address = ('127.0.0.1', 8080)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind(address)
    server_socket.listen()

    connections = []

    try:
        while True:
            print(f'socketserver is listening now......')
            connection, client_address = server_socket.accept()
            print(f'I got a connection: {connection} from address: {client_address}')
            connections.append(connection)

            for conn in connections:
                buffer = b''

                while buffer[-2:] != b'\r\n':
                    data = conn.recv(2)

                    if not data:
                        break

                    print(f'T got data: {data}')
                    buffer += data

                print(f'All the data is: {buffer}')
                conn.send(buffer)
    finally:
        server_socket.close()
        pass


def run_server_not_block_socket():
    address = ('127.0.0.1', 8080)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind(address)
    server_socket.listen()
    server_socket.setblocking(False)  # 设置非阻塞的套接字

    connections = []

    try:
        while True:
            print(f'socketserver is listening now......')

            try:
                connection, client_address = server_socket.accept()
                connection.setblocking(False)
                print(f'I got a connection: {connection} from address: {client_address}')
                connections.append(connection)
            except BlockingIOError:
                pass

            for conn in connections:
                try:
                    buffer = b''

                    while buffer[-2:] != b'\r\n':
                        data = conn.recv(2)

                        if not data:
                            break

                        print(f'T got data: {data}')
                        buffer += data

                    print(f'All the data is: {buffer}')
                    conn.send(buffer)
                except BlockingIOError:
                    pass
    finally:
        server_socket.close()
        pass


if __name__ == '__main__':
    # run_server_block_socket()
    run_server_not_block_socket()
