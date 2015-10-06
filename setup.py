import sys
import envi

if sys.version_info < (3, 2):
    raise NotImplementedError("Sorry, you need at least Python 3.x to use envi.")

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='envi',
    version=envi.__version__,
    packages=['envi'],
    url='',
    license='',
    author='ayurjev',
    author_email='',
    description='wrapper for bottle',
    install_requires=[
        'bottle>=0.12',
    ]
)
