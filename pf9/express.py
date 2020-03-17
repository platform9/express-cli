"""Express Config Module"""
import os
import sys
import click

from pf9.cli.commands import version
from pf9.cluster.commands import cluster
from pf9.config.commands import config
from pf9.modules.util import Logger
from pf9.support.commands import support

# Initialize logger
logger = Logger(os.path.join(os.path.expanduser("~"), 'pf9/log/pf9ctl.log')).get_logger(__name__)
logger.info(msg=__name__ + "Initialized")


@click.group()
@click.version_option(message='%(version)s')
@click.pass_context
def cli(ctx):
    """Express-CLI
    A CLI for Platform9 Express."""
    # Set Global Vars into context objs
    if ctx.obj is None:
        ctx.obj = dict()
    ctx.obj['pf9_venv'] = sys.prefix
    ctx.obj['venv_activate'] = "{}/bin/activate".format(ctx.obj['pf9_venv'])
    ctx.obj['venv_python'] = sys.executable
    ctx.obj['home_dir'] = os.path.expanduser("~")
    ctx.obj['pf9_cli_src_dir'] = os.path.dirname(os.path.realpath(__file__))
    ctx.obj['pf9_dir'] = os.path.join(ctx.obj['home_dir'], 'pf9/')
    ctx.obj['pf9_log_dir'] = os.path.join(ctx.obj['pf9_dir'], 'log/')
    ctx.obj['pf9_log'] = os.path.join(ctx.obj['pf9_log_dir'], 'pf9ctl.log')
    ctx.obj['pf9_db_dir'] = os.path.join(ctx.obj['pf9_dir'], 'db/')
    ctx.obj['pf9_exp_dir'] = os.path.join(ctx.obj['pf9_cli_src_dir'], 'express/')
    ctx.obj['exp_config_file'] = os.path.join(ctx.obj['pf9_db_dir'], 'express.conf')
    ctx.obj['pf9_exec_ansible-playbook'] = os.path.join(ctx.obj['pf9_venv'], 'bin', 'ansible-playbook')
    ctx.obj['pf9_ansible_cfg'] = os.path.join(ctx.obj['pf9_exp_dir'], 'ansible.cfg')
    ctx.obj['pf9_k8_playbook'] = os.path.join(ctx.obj['pf9_exp_dir'], 'pf9-k8s-express.yml')

# Add top-level commands to cli.
# Any commands defined here or added will be toplevel


cli.add_command(version)
cli.add_command(config)
cli.add_command(support)
cli.add_command(cluster)
