#!/bin/sh

cd $1
rm -R build dist *.egg-info
python setup.py sdist bdist_wheel
# python -m twine upload -s -i "DataJoint Dev" dist/*
python -m twine upload dist/*
# rm -R build dist *.egg-info