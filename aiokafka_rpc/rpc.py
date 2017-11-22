import io
import traceback
import functools
import msgpack
import asyncio
import logging
from kafka.common import KafkaError
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka_rpc.client import get_msgpack_hooks


class AIOKafkaRPC(object):
    log = logging.getLogger(__name__)

    def __init__(self, rpc_obj, kafka_servers='localhost:9092',
                 in_topic='aiokafkarpc_in', out_topic='aiokafkarpc_out',
                 translation_table=[], *, loop):
        self._tasks = {}
        self._loop = loop
        self._topic_out = out_topic
        self._rpc_obj = rpc_obj
        self._res_queue = asyncio.Queue(loop=loop)

        default, ext_hook = get_msgpack_hooks(translation_table)
        self.__consumer = AIOKafkaConsumer(
            in_topic, loop=loop, bootstrap_servers=kafka_servers,
            group_id=in_topic + '-group',
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
        self._consume_task = self._loop.create_task(self.__consume_routine())
        self._produce_task = self._loop.create_task(self.__produce_routine())

    @asyncio.coroutine
    def close(self, timeout=10):
        self._consume_task.cancel()
        try:
            yield from self._consume_task
        except asyncio.CancelledError:
            pass

        if self._tasks:
            yield from asyncio.wait(
                self._tasks.values(), loop=self._loop, timeout=timeout)

        self._res_queue.put_nowait((None, None, None))
        yield from self._produce_task

        yield from self.__producer.stop()
        yield from self.__consumer.stop()

    def __send_result(self, call_id, ptid, result=None, err=None):
        if err is not None:
            out = io.StringIO()
            traceback.print_exc(file=out)
            ret = {"error": repr(err), "stacktrace": out.getvalue()}
        else:
            ret = {"result": result}
        self._res_queue.put_nowait((call_id, ptid, ret))

    def __on_done_task(self, call_id, ptid, task):
        self._tasks.pop(call_id)
        try:
            result = task.result()
            self.__send_result(call_id, ptid, result)
        except Exception as err:
            self.__send_result(call_id, ptid, err=err)

    @asyncio.coroutine
    def __produce_routine(self):
        while True:
            call_id, ptid, res = yield from self._res_queue.get()
            if call_id is None:
                break
            try:
                yield from self.__producer.send(
                    self._topic_out, res, key=call_id, partition=ptid)
            except KafkaError as err:
                self.log.error("send RPC response failed: %s", err)
            except Exception as err:
                self.__send_result(call_id, err=err)

    @asyncio.coroutine
    def __consume_routine(self):
        while True:
            message = yield from self.__consumer.getone()
            call_id = message.key
            method_name, args, kw_args, ptid = message.value
            try:
                method = getattr(self._rpc_obj, method_name)
                if not asyncio.iscoroutinefunction(method):
                    raise RuntimeError(
                        "'{}' should be a coroutine".format(method_name))
                task = self._loop.create_task(method(*args, **kw_args))
                task.add_done_callback(
                    functools.partial(self.__on_done_task, call_id, ptid))
                self._tasks[call_id] = task
            except Exception as err:
                self.__send_result(call_id, ptid, err=err)
