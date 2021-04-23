import setuptools
from os import path

pkg_name = "otumat"

with open("README.md", "r") as fh:
    long_description = fh.read()

with open(path.join(path.abspath(path.dirname(__file__)), pkg_name, 'version.py')) as f:
    exec(f.read())

setuptools.setup(
    name=pkg_name,
    version=__version__,
    author="Raphael Guzman",
    author_email="raphael.h.guzman@gmail.com",
    description="A suite of maintainer tools and utilities for pip packages.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/datajoint/otumat",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "distutils.setup_keywords": [
            "privkey_path = {}:assert_string".format(pkg_name),
            "pubkey_path = {}:assert_string".format(pkg_name),
        ],
        "egg_info.writers": [
            ".sig = {}:write_arg".format(pkg_name),
            ".pub = {}:write_arg".format(pkg_name),
        ],
    },
    install_requires=['cryptography'],
)
