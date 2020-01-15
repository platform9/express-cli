"""Tests for our main skele CLI module."""


import os
import logging
import inspect 
import shutil
import sys
from subprocess import PIPE, Popen as popen

from unittest import TestCase
from click.testing import CliRunner

from pf9 import __version__ as VERSION
from pf9.express import cli
from pf9.express import version as cli_version

try:
    # python 3.4+ should use builtin unittest.mock not mock package
    from unittest.mock import patch
except ImportError:
    from mock import patch


class TestHelp(TestCase):
    def test_returns_usage_information(self):
        output = popen(['express', '--help'], stdout=PIPE).communicate()[0]
        self.assertTrue('Usage:' in str(output))

class TestExpCliVersion(TestCase):
    def test_returns_version_information(self):
        output = popen(['express', '--version'], stdout=PIPE).communicate()[0]
        self.assertEqual(output.decode("utf-8").strip(), VERSION)
# WIP
class TestPf9ExpVersion(TestCase):
    @classmethod
    def setUp(self):
        self.log = logging.getLogger('Running setUp for: '+ inspect.currentframe().f_code.co_name)
        self.version_id = 'v1.0.1'
        self.runner = CliRunner()

    def test_cli_version(self):
        with self.runner.isolated_filesystem():
            tmp_dir = os.getcwd()
            pf9_exp_dir = os.path.join(tmp_dir, 'pf9/pf9-express/')
            os.makedirs(pf9_exp_dir, 0o755)
            obj_test = dict({'pf9_exp_dir': pf9_exp_dir})
            
            # Test when version file doesn't exist
            result_1 = self.runner.invoke(cli_version, obj=obj_test) 
            assert ('version information not available' in result_1.output)


            with open(os.path.join(pf9_exp_dir, 'version'), 'w+') as write_ver:
                # Test when version file exist no data
                result_2 = self.runner.invoke(cli_version, obj=obj_test) 
                assert ('version information not available' in result_2.output)
                
                # Test when version file exist
                write_ver.write(self.version_id)
            result_3 = self.runner.invoke(cli_version, obj=obj_test) 
            assert (self.version_id in result_3.output)

