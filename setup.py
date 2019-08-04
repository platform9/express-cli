"""Packaging settings."""


from codecs import open
from os.path import abspath, dirname, join
from subprocess import call

from setuptools import Command, find_packages, setup

from pf9 import __version__


this_dir = abspath(dirname(__file__))
with open(join(this_dir, 'README.md'), encoding='utf-8') as file:
    long_description = file.read()


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
        errno = call(['py.test', '--cov=pf9', '--cov-report=term-missing'])
        raise SystemExit(errno)


setup(
    name = 'express-cli',
    version = __version__,
    description = 'Express CLI.',
    long_description = long_description,
    url = 'https://github.com/platform9/express-cli',
    author = 'Jeremy Brooks',
    author_email = 'jeremy@platform9.com',
    license = 'Apache 2.0',
    classifiers = [
        'Intended Audience :: Platform9 Express Users',
        'Topic :: Utilities',
        'License :: Apache 2.0',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    keywords = 'cli',
    packages = find_packages(exclude=['docs', 'tests*']),
    install_requires = ['Click', 'docker'],
    extras_require = {
        'test': ['coverage', 'pytest', 'pytest-cov'],
    },
    entry_points = {
        'console_scripts': [
            'express=pf9.express:cli',
        ],
    },
    cmdclass = {'test': RunTests},
)
