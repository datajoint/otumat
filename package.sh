#!/bin/sh

# package for PyPi
cd $1
rm -R build dist *.egg-info
python setup.py sdist bdist_wheel
# python -m twine upload dist/*
