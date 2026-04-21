from setuptools import find_packages, setup

setup(
    name="saikou-watchdog",
    version="1.0.0",
    description="Production-ready service health monitor with Slack alerts and rotating logs.",
    author="Martin Hatch",
    author_email="martin@saikou.tech",
    url="https://github.com/SuperfastSimon/saikou-watchdog",
    py_modules=["config", "watchdog", "cli"],
    packages=find_packages(),
    install_requires=["requests>=2.31.0"],
    extras_require={"dev": ["pytest>=7.4.0", "pytest-mock>=3.12.0"]},
    entry_points={"console_scripts": ["saikou-watchdog=cli:main"]},
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
