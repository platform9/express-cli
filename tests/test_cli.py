"""Tests for our main skele CLI module."""


import os
import logging
import tempfile
import inspect 
import shutil
from subprocess import PIPE, Popen as popen

from unittest import TestCase
from click.testing import CliRunner

from pf9 import __version__ as VERSION
from pf9.express import list as cli_config_list

class TestHelp(TestCase):
    def test_returns_usage_information(self):
        output = popen(['express', '--help'], stdout=PIPE).communicate()[0]
        self.assertTrue('Usage:' in output)

class TestVersion(TestCase):
    def test_returns_version_information(self):
        output = popen(['express', '--version'], stdout=PIPE).communicate()[0]
        self.assertEqual(output.strip(), VERSION)

class TestConfigList(TestCase):
    @classmethod
    def setUp(self):
        self.log = logging.getLogger('Running setUp for: '+ inspect.currentframe().f_code.co_name)
        self.temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.temp_dir + 'pf9/pf9-express/'), 0o755)
        self.conf_dir = os.path.join(self.temp_dir, 'config/')
        self.obj_test = dict({'pf9_exp_conf_dir': self.conf_dir})
        self.express_config = '''
config_name|test
os_region|region1
os_username|test.user@platform9.com
proxy_url|-
dns_resolver_1|1.1.1.1
dns_resolver_2|2.2.2.2
du_url|test.user@platform9.com
manage_hostname|TRUE
manage_resolver|True
os_password|testpass
os_tenant|service
'''

    @classmethod
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_list_no_configdir(self):
        runner = CliRunner()
        result = runner.invoke(cli_config_list, obj=self.obj_test)
        assert (result.exit_code == 0)
        assert ('No Platform9 Express configs exist' in result.output)

    def test_config_list_empty(self):
        os.makedirs(self.conf_dir, 0o755)
        runner = CliRunner()
        result = runner.invoke(cli_config_list, obj=self.obj_test)
        assert result.exit_code == 0
        assert ('No Platform9 Express configs exist' in result.output or 'Management Plane' in result.output)

    def test_config_list_with_config(self):
        os.makedirs(self.conf_dir, 0o755)
        with open(os.path.join(self.conf_dir, 'express.conf'), 'w+') as write_exp_conf:
            write_exp_conf.write(self.express_config)
        runner = CliRunner()
        result = runner.invoke(cli_config_list, obj=self.obj_test)
        assert result.exit_code == 0
        assert ('test.user@platform9.com' in result.output)
