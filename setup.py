from setuptools import setup, find_packages

setup(
    name="blockchain-demo",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'websockets>=12.0',
        'pytest>=7.4.3',
        'pytest-asyncio>=0.21.1',
    ],
)