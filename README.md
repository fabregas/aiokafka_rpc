# aiokafka_rpc

RPC over Apache Kafka for Python using asyncio

Example of aiokafka RPC using:

```python
import asyncio

from aiokafka_rpc import AIOKafkaRPC, AIOKafkaRPCClient

class MyRPC(object):
    @asyncio.coroutine
    def test_method(self, val, test=False):
        return [val * 100, test]

    @asyncio.coroutine
    def strlen(self, s):
        return len(s)

@asyncio.coroutine
def test(loop):
    server = AIOKafkaRPC(MyRPC(), loop=loop)
    client = AIOKafkaRPCClient(loop=loop)

    yield from server.run()
    yield from client.run()


    res = yield from client.call.test_method(234)
    assert res, [23400, False]

    res = yield from client.call.test_method(234, test=True)
    assert res, [23400, True]

    res = yield from client.call.strlen('test')
    assert res, 4

    yield from client.close()
    yield from server.close()


loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()
```

