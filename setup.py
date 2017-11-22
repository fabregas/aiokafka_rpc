from setuptools import setup
from setuptools import find_packages

setup(
    name="aiokafka_rpc",
    version="1.0",
    author="OPS",
    author_email="ops@yusp.com",
    description=("RPC over Apache Kafka for Python using asyncio - based on fabregas/aiokafka_rpc"),
    license="Apache Software License",
    keywords="aiokafka_rpc",
    url="https://github.com/estol/aiokafka_rpc",
    packages=["aiokafka_rpc"],
    install_requires=[_.strip() for _ in open('requirements.txt') if _.strip() and not _.strip().startswith('#')],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3"
    ],
)