"""Packaging settings."""


from codecs import open
from subprocess import call

from setuptools import Command, find_packages, setup

from pf9 import __version__


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
    long_description = open('README.md').read(),
    long_description_content_type = 'text/markdown',
    url = 'https://github.com/platform9/express-cli',
    author = 'Jeremy Brooks',
    author_email = 'jeremy@platform9.com',
    license = 'Apache 2.0',
    classifiers = [
        'Intended Audience :: System Administrators',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: OSI Approved :: Apache Software License',
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
    package_data = {
        'pf9':['templates/*',],
    },
    include_package_data=True,
    zip_safe=False,
    keywords = 'cli',
    packages = find_packages(exclude=['docs', 'tests*']),
    install_requires = ['click', 'prettytable', 'requests', 'netifaces', 'colorama'],
    extras_require = {
        'test': ['coverage', 'pytest', 'pytest-cov', 'mock'],
    },
    entry_points = {
        'console_scripts': [
            'express=pf9.express:cli',
        ],
    },
    cmdclass = {'test': RunTests},
)
