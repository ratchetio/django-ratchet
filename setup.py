import os.path
from setuptools import Command, find_packages, setup

HERE = os.path.abspath(os.path.dirname(__file__))

README_PATH = os.path.join(HERE, 'README.md')
try:
    README = open(README_PATH).read()
except IOError:
    README = ''

setup(
    name='django_ratchet',
    version='0.1',
    description='ratchet plugin for django',
    long_description=README,
    author='brianr',
    author_email='brian@ratchet.io',
    url='',
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        ],
    install_requires=[
        'django>=1.4',
        'requests',
        ],
    packages=find_packages(),
    zip_safe=False,
    )







