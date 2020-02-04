"""Tests for our main skele CLI module."""


import os
import logging
import inspect
from subprocess import PIPE, Popen as popen

from unittest import TestCase
from click.testing import CliRunner

from pf9 import __version__
from pf9.express import cli
from pf9.express import version as cli_version


class TestHelp(TestCase):
    """Test express --help call"""
    def test_returns_usage_information(self):
        """Test express --help via direct subproccess call"""
        output = popen(['express', '--help'], stdout=PIPE).communicate()[0]
        self.assertTrue('Usage:' in str(output))

class TestExpCliVersion(TestCase):
    """Test express --version call"""
    def test_returns_version_information(self):
        """Test express --version call"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        assert str(__version__) in result.output
# WIP
class TestPf9ExpVersion(TestCase):
    """Test express-cli version functions"""
    @classmethod
    def setUp(cls):
        """Setup Test express-cli version """
        cls.log = logging.getLogger('Running setUp for: '+ inspect.currentframe().f_code.co_name)
        cls.version_id = 'v1.0.1'
        cls.runner = CliRunner()

    def test_cli_version(self):
        """Test express-cli version functions"""
        with self.runner.isolated_filesystem():
            tmp_dir = os.getcwd()
            pf9_exp_dir = os.path.join(tmp_dir, 'pf9/pf9-express/')
            os.makedirs(pf9_exp_dir, 0o755)
            obj_test = dict({'pf9_exp_dir': pf9_exp_dir})

            # Test when version file doesn't exist
            result_1 = self.runner.invoke(cli_version, obj=obj_test)
            assert 'version information not available' in result_1.output


            with open(os.path.join(pf9_exp_dir, 'version'), 'w+') as write_ver:
                # Test when version file exist no data
                result_2 = self.runner.invoke(cli_version, obj=obj_test)
                assert 'version information not available' in result_2.output

                # Test when version file exist
                write_ver.write(self.version_id)
            result_3 = self.runner.invoke(cli_version, obj=obj_test)
            assert self.version_id in result_3.output
