import asyncio
import pytest
import time
from functools import wraps

from aiokafka.client import AIOKafkaClient
from aiokafka.errors import ConnectionError


def run_until_complete(fun):
    if not asyncio.iscoroutinefunction(fun):
        fun = asyncio.coroutine(fun)

    @wraps(fun)
    def wrapper(test, *args, **kw):
        loop = test.loop
        ret = loop.run_until_complete(
            asyncio.wait_for(fun(test, *args, **kw), 15, loop=loop))
        return ret
    return wrapper


@pytest.mark.usefixtures('setup_test_class')
class IntegrationTest:
    loop = None

    kafka_host = None
    kafka_port = None

    @classmethod
    def wait_kafka(cls):
        cls.hosts = ['{}:{}'.format(cls.kafka_host, cls.kafka_port)]

        # Reconnecting until Kafka in docker becomes available
        client = AIOKafkaClient(loop=cls.loop, bootstrap_servers=cls.hosts)
        for i in range(500):
            try:
                cls.loop.run_until_complete(client.bootstrap())
                # Wait for broker to look for others.
                if not client.cluster.brokers():
                    time.sleep(0.1)
                    continue
            except ConnectionError:
                time.sleep(0.1)
            else:
                cls.loop.run_until_complete(client.close())
                return
        assert False, "Kafka server never started"
