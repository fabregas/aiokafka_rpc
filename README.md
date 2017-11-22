# aiokafka_rpc
[![Build Status](https://travis-ci.org/fabregas/aiokafka_rpc.svg?branch=master)](https://travis-ci.org/fabregas/aiokafka_rpc)
[![codecov](https://codecov.io/gh/fabregas/aiokafka_rpc/branch/master/graph/badge.svg)](https://codecov.io/gh/fabregas/aiokafka_rpc)

### RPC over Apache Kafka for Python using asyncio (>=python3.5.1)

Example of aiokafka RPC using:

```python
import asyncio

from aiokafka_rpc import AIOKafkaRPC, AIOKafkaRPCClient

class MyRPC(object):
    async def test_method(self, val, test=False):
        return [val * 100, test]

    async def strlen(self, s):
        return len(s)


async def test(loop):
    kafka_servers = ["localhost:9092"]
    server = AIOKafkaRPC(MyRPC(), kafka_servers=kafka_servers, loop=loop)
    await server.run()

    client = AIOKafkaRPCClient(kafka_servers=kafka_servers, loop=loop)
    await client.run()

    res = await client.call.test_method(234)
    assert res, [23400, False]

    res = await client.call.test_method(234, test=True)
    assert res, [23400, True]

    res = await client.call.strlen('test')
    assert res, 4

    await client.close()
    await server.close()


loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()
```

## Installation

> pip install aiokafka_rpc
