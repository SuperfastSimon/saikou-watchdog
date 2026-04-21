from setuptools import setup, find_packages

setup(
    name="saikou-watchdog",
    version="1.0.0",
    packages=find_packages(),
    install_requires=["requests>=2.31.0"],
    entry_points={
        "console_scripts": [
            "watchdog=watchdog.cli:main",
        ]
    },
)
