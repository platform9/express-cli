"""Tests for config CLI module."""


import os
import logging
import tempfile
import inspect
import shutil

from unittest import TestCase
from click.testing import CliRunner

from pf9.config.commands import config_list as cli_config_list
from pf9.config.commands import create as cli_config_create


class TestConfigCreateFull(TestCase):
    """ Test Config Create"""
    # ToDo: Need better method for test dir. Can not write to unittest temp dir from click methods
    #       Not currently able to test logic and actions if file or directories need to be created.
    @classmethod
    def setUp(cls):
        """Setup mock env"""
        cls.log = logging.getLogger('Running setUp for: '+ inspect.currentframe().f_code.co_name)
        cls.temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(cls.temp_dir, 'pf9/'), 0o755)
        cls.conf_dir = os.path.join(cls.temp_dir, 'pf9/db/')
        os.makedirs(cls.conf_dir, 0o755)
        cls.obj_test = dict({'pf9_db_dir': cls.conf_dir,
                             'exp_config_file': os.path.join(cls.conf_dir, 'express.conf')})
        cls.expected_config = '''os_region|region1
                os_username|test.user@platform9.com
                proxy_url|-
                du_url|test.platform9.com
                os_password|testpass
                os_tenant|service
                '''

    @classmethod
    def tearDown(cls):
        """teardown mock env"""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_config_create_cli_options(self):
        """Test Config create from"""
        runner = CliRunner()
            #result = runner.invoke(cli_config_create, obj=self.obj_test)
        result = runner.invoke(cli_config_create,
                               ['--du_url=test.platform9.com',
                                '--os_username=test.user@platform9.com',
                                '--os_password=testpass',
                                '--os_region=region1',
                                '--os_tenant=service'],
                               obj=self.obj_test)
        assert result.exit_code == 0
        assert 'Successfully wrote Platform9 management plane configuration' in result.output
# !!! Need to compaire elements of both config files
#        with open(os.path.join(self.conf_dir, 'express.conf'), 'r') as read_test_conf:
#            test_config = read_test_conf.readlines()
#        test_config.sort()
#        self.expected_config.strip().sort()
#>       self.expected_config.strip().sort()
#E       AttributeError: 'str' object has no attribute 'sort'
#        assert (test_config == self.expected_config)

class TestConfigCreateMinimal(TestCase):
    """Test express config create"""
    # ToDo: Need better method for test dir. Can not write to unittest temp dir from click methods
    #       Not currently able to test logic and actions if file or directories need to be created.
    @classmethod
    def setUp(cls):
        """Setup mock env"""
        cls.log = logging.getLogger('Running setUp for: '+ inspect.currentframe().f_code.co_name)
        cls.temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(cls.temp_dir, 'pf9/'), 0o755)
        cls.conf_dir = os.path.join(cls.temp_dir, 'pf9/db/')
        os.makedirs(cls.conf_dir, 0o755)
        cls.obj_test = dict({'pf9_db_dir': cls.conf_dir,
                             'exp_config_file': os.path.join(cls.conf_dir, 'express.conf')})
        cls.expected_config = '''os_region|region1
                os_username|test.user@platform9.com
                proxy_url|-
                du_url|test.platform9.com
                os_password|testpass
                os_tenant|service
                '''

    @classmethod
    def tearDown(cls):
        """teardown mock env"""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_config_create_cli_options(self):
        """Test creating a config with args"""
        runner = CliRunner()
        result = runner.invoke(cli_config_create,
                               ['--du_url=test.platform9.com',
                                '--os_username=test.user@platform9.com',
                                '--os_password=testpass',
                                '--os_region=region1',
                                '--os_tenant=service'],
                               obj=self.obj_test)
        assert result.exit_code == 0
        assert 'Successfully wrote Platform9 management plane configuration' in result.output
# !!! Need to compaire elements of both config files


class TestConfigList(TestCase):
    """Test express config list functions"""
    @classmethod
    def setUp(cls):
        """Setup mock env"""
        cls.log = logging.getLogger('Running setUp for: '+ inspect.currentframe().f_code.co_name)
        cls.temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(cls.temp_dir, 'pf9/'), 0o755)
        cls.conf_dir = os.path.join(cls.temp_dir, 'pf9/db/')
        cls.obj_test = dict({'pf9_db_dir': cls.conf_dir,
                             'exp_config_file': os.path.join(cls.conf_dir, 'express.conf')})
        cls.express_config = '''
                os_region|region1
                os_username|test.user@platform9.com
                proxy_url|-
                du_url|https://test.platform9.com
                os_password|testpass
                os_tenant|service
                '''

    @classmethod
    def tearDown(cls):
        """teardown mock env"""
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_config_list_no_configdir(self):
        """Test when no configdir exist"""
        runner = CliRunner()
        result = runner.invoke(cli_config_list, obj=self.obj_test)
        assert result.exit_code == 0
        assert 'No Platform9 management plane configs exist' in result.output

    def test_config_list_empty(self):
        """Test when configdir exist but empty"""
        os.makedirs(self.conf_dir, 0o755)
        runner = CliRunner()
        result = runner.invoke(cli_config_list, obj=self.obj_test)
        assert result.exit_code == 0
        assert ('No Platform9 management plane configs exist' in result.output
                or 'Management Plane' in result.output)

    def test_config_list_with_config(self):
        """Test when configdir and config exist"""
        os.makedirs(self.conf_dir, 0o755)
        with open(os.path.join(self.conf_dir, 'express.conf'), 'w+') as write_exp_conf:
            write_exp_conf.write(self.express_config.strip())
        runner = CliRunner()
        result = runner.invoke(cli_config_list, obj=self.obj_test)
        assert result.exit_code == 0
        assert 'test.platform9.com' in result.output
