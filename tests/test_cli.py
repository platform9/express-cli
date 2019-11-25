"""Tests for our main skele CLI module."""


import os
import logging
import tempfile
import inspect 
import shutil
import sys
from subprocess import PIPE, Popen as popen

from unittest import TestCase
from click.testing import CliRunner

from pf9 import __version__ as VERSION
from pf9.config.commands import list as cli_config_list
from pf9.config.commands import create as cli_config_create
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


class TestConfigCreateFull(TestCase):
    # ToDo: Need better method for test dir. Can not write to unittest temp dir from click methods
    #       Not currently able to test logic and actions if file or directories need to be created.
    @classmethod
    def setUp(self):
        self.log = logging.getLogger('Running setUp for: '+ inspect.currentframe().f_code.co_name)
        self.temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.temp_dir, 'pf9/pf9-express/'), 0o755)
        self.conf_dir = os.path.join(self.temp_dir, 'pf9/pf9-express/config/')
        os.makedirs(self.conf_dir, 0o755)
        self.obj_test = dict({'pf9_exp_conf_dir': self.conf_dir})
        self.expected_config = '''
                config_name|test
                os_region|region1
                os_username|test.user@platform9.com
                proxy_url|-
                dns_resolver1|1.1.1.1
                dns_resolver2|2.2.2.2
                du_url|test.user@platform9.com
                manage_hostname|TRUE
                manage_resolver|True
                os_password|testpass
                os_tenant|service
                '''

    @classmethod
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_create_cli_options(self):
        runner = CliRunner()
            #result = runner.invoke(cli_config_create, obj=self.obj_test)
        result = runner.invoke(cli_config_create, 
                ['--name=test', 
                    '--du_url=test@platform9.com', 
                    '--os_username=test.user@platform9.com', 
                    '--os_password=testpass', 
                    '--os_region=region1', 
                    '--os_tenant=service', 
                    '--proxy_url=-', 
                    '--manage_hostname=TRUE', 
                    '--manage_resolver=True', 
                    '--dns_resolver1=1.1.1.1', 
                    '--dns_resolver2=2.2.2.2'], 
                obj=self.obj_test)
        assert (result.exit_code == 0)
        assert ('Successfully wrote Platform9 management plane configuration' in result.output)
# !!! Need to compaire elements of both config files
# !!! They are strings so either readline and evaluate each against other file or split('\n', list).sort()
#        with open(os.path.join(self.conf_dir, 'express.conf'), 'r') as read_test_conf:
#            test_config = read_test_conf.readlines()
#        test_config.sort()
#        self.expected_config.strip().sort()
#>       self.expected_config.strip().sort()
#E       AttributeError: 'str' object has no attribute 'sort'
#        assert (test_config == self.expected_config) 

class TestConfigCreateMinimal(TestCase):
    # ToDo: Need better method for test dir. Can not write to unittest temp dir from click methods
    #       Not currently able to test logic and actions if file or directories need to be created.
    @classmethod
    def setUp(self):
        self.log = logging.getLogger('Running setUp for: '+ inspect.currentframe().f_code.co_name)
        self.temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.temp_dir, 'pf9/pf9-express/'), 0o755)
        self.conf_dir = os.path.join(self.temp_dir, 'pf9/pf9-express/config/')
        os.makedirs(self.conf_dir, 0o755)
        self.obj_test = dict({'pf9_exp_conf_dir': self.conf_dir})
        self.expected_config = '''
                config_name|test
                os_region|region1
                os_username|test.user@platform9.com
                proxy_url|-
                dns_resolver1|8.8.8.8
                dns_resolver2|8.8.4.4
                du_url|test.user@platform9.com
                manage_hostname|False
                manage_resolver|False
                os_password|testpass
                os_tenant|service
                '''

    @classmethod
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_create_cli_options(self):
        runner = CliRunner()
            #result = runner.invoke(cli_config_create, obj=self.obj_test)
        result = runner.invoke(cli_config_create, 
                ['--name=test', 
                    '--du_url=test@platform9.com', 
                    '--os_username=test.user@platform9.com', 
                    '--os_password=testpass', 
                    '--os_region=region1', 
                    '--os_tenant=service'], 
                obj=self.obj_test)
        assert (result.exit_code == 0)
        assert ('Successfully wrote Platform9 management plane configuration' in result.output)
# !!! Need to compaire elements of both config files


class TestConfigList(TestCase):
    @classmethod
    def setUp(self):
        self.log = logging.getLogger('Running setUp for: '+ inspect.currentframe().f_code.co_name)
        self.temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.temp_dir, 'pf9/pf9-express/'), 0o755)
        self.conf_dir = os.path.join(self.temp_dir, 'pf9/pf9-express/config/')
        self.obj_test = dict({'pf9_exp_conf_dir': self.conf_dir})
        self.express_config = '''
                config_name|test
                os_region|region1
                os_username|test.user@platform9.com
                proxy_url|-
                dns_resolver1|1.1.1.1
                dns_resolver2|2.2.2.2
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
        assert ('No Platform9 management plane configs exist' in result.output)

    def test_config_list_empty(self):
        os.makedirs(self.conf_dir, 0o755)
        runner = CliRunner()
        result = runner.invoke(cli_config_list, obj=self.obj_test)
        assert result.exit_code == 0
        assert ('No Platform9 management plane configs exist' in result.output or 'Management Plane' in result.output)

    def test_config_list_with_config(self):
        os.makedirs(self.conf_dir, 0o755)
        with open(os.path.join(self.conf_dir, 'express.conf'), 'w+') as write_exp_conf:
            write_exp_conf.write(self.express_config.strip())
        runner = CliRunner()
        result = runner.invoke(cli_config_list, obj=self.obj_test)
        assert result.exit_code == 0
        assert ('test.user@platform9.com' in result.output)
