from __future__ import absolute_import

import datetime

from kombu import Connection

BROKER_URL = "amqp://admin:admin013431_Prd@127.0.0.1:5672/%2Fcircle"


def publisher():
    with Connection(BROKER_URL) as conn:
        simple_queue = conn.SimpleQueue("kombu_simple_q")
        message = f'helloworld, sent at {datetime.datetime.today()}'
        simple_queue.put(message)
        print(f'Sent: {message}')
        simple_queue.close()


def consumer():
    with Connection(BROKER_URL) as conn:
        simple_queue = conn.SimpleQueue("kombu_simple_q")
        message = simple_queue.get(block=True, timeout=1)
        print("message:", message)
        print(f'Received: {message.payload}')
        message.ack()
        simple_queue.close()




