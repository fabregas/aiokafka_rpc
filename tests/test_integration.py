from .utils import IntegrationTest, run_until_complete
from aiokafka_rpc import AIOKafkaRPC, AIOKafkaRPCClient


class TestRPC(object):
    async def valmul(self, val, test=False):
        return [val * 100, test]

    async def strlen(self, s):
        return len(s)

    async def list_to_dict(self, lst):
        return dict(enumerate(lst))


class TestFunctional(IntegrationTest):
    @run_until_complete
    async def test_basic(self):
        kafka_servers = ["{}:{}".format(self.kafka_host, self.kafka_port)]
        server = AIOKafkaRPC(
            TestRPC(), kafka_servers=kafka_servers, loop=self.loop
        )
        client = AIOKafkaRPCClient(kafka_servers=kafka_servers, loop=self.loop)

        await server.run()
        await client.run()

        try:
            res = await client.call.valmul(234)
            assert res, [23400, False]

            res = await client.call.valmul("str")
            assert res, ["str" * 100, False]

            res = await client.call.valmul(234, test=True)
            assert res, [23400, True]

            res = await client.call.strlen('test')
            assert res, 4

            res = await client.call.list_to_dict(["zero", "one", "two"])
            assert res, {0: "zero", 1: "one", 2: "two"}
        finally:
            await client.close()
            await server.close()
