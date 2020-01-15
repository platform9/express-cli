"""Tests for express cluster."""

from unittest import TestCase
from click.testing import CliRunner

from pf9.cluster.commands import create as cli_cluster_create
from pf9.cluster.commands import bootstrap as cli_cluster_bootstrap
from pf9.cluster.commands import prepnode as cli_cluster_prepnode
from pf9.cluster.commands import attach_node as cli_cluster_attachnode

try:
    # python 3.4+ should use builtin unittest.mock not mock package
    from unittest.mock import patch
except ImportError:
    from mock import patch


class TestClusterHelp(TestCase):
    """Tests express cluster XcommandX --help"""
    def test_cli_cluster_create_help(self):
        runner = CliRunner()
        result = runner.invoke(cli_cluster_create, 
                ['--help'])
        assert (result.exit_code == 0)
        assert ('Usage:' in result.output)

    def test_cli_cluster_bootstrap_help(self):
        runner = CliRunner()
        result = runner.invoke(cli_cluster_bootstrap, 
                ['--help'])
        assert (result.exit_code == 0)
        assert ('Usage:' in result.output)

    def test_cli_cluster_prepnode_help(self):
        runner = CliRunner()
        result = runner.invoke(cli_cluster_prepnode, 
                ['--help'])
        assert (result.exit_code == 0)
        assert ('Usage:' in result.output)

    def test_cli_cluster_attachnode_help(self):
        runner = CliRunner()
        result = runner.invoke(cli_cluster_attachnode, 
                ['--help'])
        assert (result.exit_code == 0)
        assert ('Usage:' in result.output)


