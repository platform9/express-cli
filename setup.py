"""Packaging settings."""

import sys
import os
from codecs import open
from subprocess import call

from setuptools import Command, find_packages, setup

from pf9 import __version__

from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# set env_vars for python intpretor that was used for install
py_env = sys.prefix
os.environ["EXPRESS_CLI_PYTHON"] = str(sys.executable) 
os.environ["EXPRESS_CLI_VENV"] = str(py_env) 
os.environ["EXPRESS_CLI_VENV_ACTIVATE"] = "{}/bin/activate".format(py_env)

# The above values should be written to a config file in ~/pf9/bin/
# sym links to the venv/activate and entry points should be created there
# User's PATH should be updated to include ~/pf9/bin/ with entry in ~/.bashrc or ~/.bash_profile


class RunTests(Command):
    """Run all tests."""
    description = 'run tests'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """Run all tests!"""
        errno = call('py.test')
        raise SystemExit(errno)


setup(
    name='express-cli',
    version=__version__,
    description='Platform9 CLI.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/platform9/express-cli',
    author='Jeremy Brooks',
    author_email='jeremy@platform9.com',
    license='Apache 2.0',
    classifiers=[
        'Intended Audience :: System Administrators',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
    ],
    include_package_data=True,
    zip_safe=False,
    keywords='cli',
    packages=find_packages(exclude=['docs', 'tests*']),
    install_requires=['click',
                      'prettytable',
                      'requests',
                      'netifaces',
                      'colorama',
                      'urllib3',
                      'paramiko',
                      'fabric',
                      'invoke',
                      'ansible',
                      'analytics-python'
                      ],
    extras_require={
        'test': ['coverage', 'pytest', 'pytest-cov', 'mock'],
    },
    entry_points={
        'console_scripts': [
            'express=pf9.express:cli',
        ],
    },
    cmdclass={'test': RunTests},
)
