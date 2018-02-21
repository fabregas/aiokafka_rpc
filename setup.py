from setuptools import setup

install_requires = [
    r.strip() for r in open('requirements.txt')
    if r.strip() and not r.strip().startswith('#')
]

setup(
    name="aiokafka_rpc",
    version="1.3.0",
    author='Kostiantyn Andrusenko',
    author_email='kksstt@gmail.com',
    description=("RPC over Apache Kafka for Python using asyncio"),
    license="Apache Software License",
    keywords="aiokafka_rpc",
    url="https://github.com/fabregas/aiokafka_rpc",
    packages=["aiokafka_rpc"],
    install_requires=install_requires,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3"
    ],
)
