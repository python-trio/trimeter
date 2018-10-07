from setuptools import setup, find_packages

exec(open("trimeter/_version.py", encoding="utf-8").read())

LONG_DESC = open("README.rst", encoding="utf-8").read()

setup(
    name="trimeter",
    version=__version__,
    description="A simple but powerful job scheduler for Trio programs",
    url="https://github.com/python-trio/trimeter",
    long_description=LONG_DESC,
    author="Nathaniel J. Smith",
    author_email="njs@pobox.com",
    license="MIT -or- Apache License 2.0",
    packages=find_packages(),
    install_requires=[
        "trio >= 0.9.0",  # For channels
        "outcome",
        "async_generator",
        "attrs",
    ],
    keywords=[
        "async", "scheduler", "trio",
    ],
    python_requires=">=3.5",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "License :: OSI Approved :: Apache Software License",
        "Framework :: Trio",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Intended Audience :: Developers",
    ],
)
