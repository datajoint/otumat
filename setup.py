import setuptools
from os import path

pkg_name = "raphael_python_metadata"

with open("README.md", "r") as fh:
    long_description = fh.read()

with open(path.join(path.abspath(path.dirname(__file__)), pkg_name, '__init__.py')) as f:
    exec(f.read())

setuptools.setup(
    name=pkg_name,
    version=__version__,
    author="Raphael Guzman",
    author_email="raphael.h.guzman@gmail.com",
    description="Signed certificate metadata for verifying contents of pip modules.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/guzman-raphael/datajoint-python-metadata",
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
            "privkey_path.sig = {}:write_arg_cert".format(pkg_name),
            "pubkey_path.pub = {}:write_arg_pub".format(pkg_name),
        ],
    },
    install_requires=['cryptography'],
)
