import docker as libdocker
import asyncio
import pytest
import uuid
import gc
import logging
import socket
import struct
import sys

log = logging.getLogger('aiokafka-rpc-tests')


def pytest_addoption(parser):
    parser.addoption(
        '--docker-image', action='store',
        default='aiolibs/kafka:2.11_0.10.2.1',
        help='Kafka docker image to use'
    )
    parser.addoption(
        '--no-pull', action='store_true',
        help='Do not pull new docker image before test run'
    )


@pytest.fixture(scope='session')
def unused_port():
    def factory():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]
    return factory


@pytest.fixture(scope='session')
def docker(request):
    return libdocker.Client(version='auto')


def start_container(docker, container_id):
    docker.start(container=container_id)
    resp = docker.inspect_container(container=container_id)
    return resp["NetworkSettings"]["IPAddress"]


def container_logs(docker, container, srv_name):
    c_logs = docker.logs(
        container=container['Id'], stdout=True, stderr=True, follow=False)
    log.info("========== captured {} service log =========".format(srv_name))
    for msg in c_logs.decode().splitlines():
        log.info(msg)
    log.info("============================================")


@pytest.fixture(scope='session')
def session_id():
    return str(uuid.uuid4())


@pytest.yield_fixture(scope='class')
def loop(request):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(None)

    yield loop

    if not loop._closed:
        loop.call_soon(loop.stop)
        loop.run_forever()
        loop.close()
    gc.collect()
    asyncio.set_event_loop(None)


if sys.platform == 'darwin' or sys.platform == 'win32':
    @pytest.fixture(scope='session')
    def docker_ip_address():
        """Returns IP address of the docker daemon service."""
        # docker for mac publishes ports on localhost
        return '127.0.0.1'
else:
    @pytest.fixture(scope='session')
    def docker_ip_address(docker):
        """Returns IP address of the docker daemon service."""
        # Fallback docker daemon bridge name
        ifname = 'docker0'
        try:
            for network in docker.networks():
                _ifname = network['Options'].get(
                    'com.docker.network.bridge.name')
                if _ifname is not None:
                    ifname = _ifname
                    break
        except libdocker.errors.InvalidVersion:
            pass
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        import fcntl
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15].encode('utf-8')))[20:24])


@pytest.yield_fixture(scope='session')
def kafka_server(request, docker, docker_ip_address,
                 unused_port, session_id):
    image = request.config.getoption('--docker-image')
    if not request.config.getoption('--no-pull'):
        docker.pull(image)
    kafka_host = docker_ip_address
    kafka_port = unused_port()
    container = docker.create_container(
        image=image,
        name='aiokafka-rpc-tests',
        ports=[2181, kafka_port],
        environment={
            'ADVERTISED_HOST': kafka_host,
            'ADVERTISED_PORT': kafka_port,
            'NUM_PARTITIONS': 2
        },
        host_config=docker.create_host_config(
            port_bindings={
                2181: (kafka_host, unused_port()),
                kafka_port: (kafka_host, kafka_port),
            }
        ))
    docker.start(container=container['Id'])
    yield kafka_host, kafka_port
    container_logs(docker, container, "kafka server")
    docker.kill(container=container['Id'])
    docker.remove_container(container['Id'])


@pytest.fixture(scope='class')
def setup_test_class(request, loop, kafka_server):
    request.cls.loop = loop
    request.cls.kafka_host, request.cls.kafka_port = kafka_server
    if hasattr(request.cls, 'wait_kafka'):
        request.cls.wait_kafka()
