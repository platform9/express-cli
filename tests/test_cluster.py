"""Tests for express cluster."""

from unittest import TestCase
from click.testing import CliRunner

from pf9.cluster.commands import create as cli_cluster_create
from pf9.cluster.commands import bootstrap as cli_cluster_bootstrap
from pf9.cluster.commands import prepnode as cli_cluster_prepnode
from pf9.cluster.commands import attach_node as cli_cluster_attachnode


class TestClusterHelp(TestCase):
    """Tests express cluster XcommandX --help"""

    #Tests express cluster create --help
    runner = CliRunner()
    result = runner.invoke(cli_cluster_create, ['--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output

    #Tests express cluster bootstrap --help
    runner = CliRunner()
    result = runner.invoke(cli_cluster_bootstrap, ['--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output

    #Tests express cluster prepnode --help
    runner = CliRunner()
    result = runner.invoke(cli_cluster_prepnode, ['--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output

    #Tests express cluster attachnode --help
    runner = CliRunner()
    result = runner.invoke(cli_cluster_attachnode, ['--help'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
