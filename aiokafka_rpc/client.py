import uuid
import msgpack
import random
import asyncio
import logging
# from kafka.common import TopicPartition
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka_rpc.utils import get_msgpack_hooks


class RPCError(Exception):
    pass


class CallObj(object):
    def __init__(self, wrapper):
        self._wrapper = wrapper

    def __getattr__(self, attr):
        return self._wrapper(attr)


class AIOKafkaRPCClient(object):
    log = logging.getLogger(__name__)

    def __init__(self, kafka_servers='localhost:9092',
                 in_topic='aiokafkarpc_in',
                 out_topic='aiokafkarpc_out', out_partitions=(0,),
                 translation_table=[], *, loop):
        self.call = CallObj(self._call_wrapper)

        self._topic_in = in_topic
        self._loop = loop
        self._waiters = {}
        self._out_topic = out_topic
        self._out_partitions = out_partitions

        default, ext_hook = get_msgpack_hooks(translation_table)
        self.__consumer = AIOKafkaConsumer(
            self._out_topic,
            loop=loop, bootstrap_servers=kafka_servers,
            group_id=None,
            key_deserializer=lambda x: x.decode("utf-8"),
            value_deserializer=lambda x: msgpack.unpackb(
                x, ext_hook=ext_hook, encoding="utf-8"))

        self.__producer = AIOKafkaProducer(
            bootstrap_servers=kafka_servers, loop=loop,
            key_serializer=lambda x: x.encode("utf-8"),
            value_serializer=lambda x: msgpack.packb(x, default=default))

    @asyncio.coroutine
    def run(self):
        yield from self.__producer.start()
        yield from self.__consumer.start()
        # FIXME manual partition assignment does not work correctly in aiokafka
        # self.__consumer.assign(
        # [TopicPartition(self._out_topic, p) for p in self._out_partitions])
        #
        # ensure that topic partitions exists
        for tp in self.__consumer.assignment():
            yield from self.__consumer.position(tp)
        self._consume_task = self._loop.create_task(self.__consume_routine())

    @asyncio.coroutine
    def close(self, timeout=10):
        yield from self.__producer.stop()
        if self._waiters:
            yield from asyncio.wait(
                self._waiters.values(), loop=self._loop, timeout=timeout)

        self._consume_task.cancel()
        try:
            yield from self._consume_task
        except asyncio.CancelledError:
            pass
        yield from self.__consumer.stop()

        for fut in self._waiters.values():
            fut.set_exception(asyncio.TimeoutError())

    def _call_wrapper(self, method):
        @asyncio.coroutine
        def rpc_call(*args, **kw_args):
            call_id = uuid.uuid4().hex
            ptid = random.choice(self._out_partitions)
            request = (method, args, kw_args, ptid)
            fut = asyncio.Future(loop=self._loop)
            fut.add_done_callback(lambda fut: self._waiters.pop(call_id))
            self._waiters[call_id] = fut
            try:
                yield from self.__producer.send(
                    self._topic_in, request, key=call_id)
            except Exception as err:
                self.log.error("send RPC request failed: %s", err)
                self._waiters[call_id].set_exception(err)
            return (yield from self._waiters[call_id])

        return rpc_call

    @asyncio.coroutine
    def __consume_routine(self):
        while True:
            message = yield from self.__consumer.getone()
            call_id = message.key
            response = message.value
            self.call = CallObj(self._call_wrapper)

            fut = self._waiters.get(call_id)
            if fut is None:
                continue
            if "error" in response:
                self.log.debug(response.get("stacktrace"))
                fut.set_exception(RPCError(response["error"]))
            else:
                fut.set_result(response["result"])
