"""Express Config Module"""
import os
import sys
import shutil
import click
from prettytable import PrettyTable
from ..exceptions import CLIException
from ..exceptions import UserAuthFailure
from ..modules.ostoken import GetToken
from ..modules.express import Get
from ..modules.util import Logger

# Initialize logger
logger = Logger(os.path.join(os.path.expanduser("~"), 'pf9/log/pf9ctl.log')).get_logger(__name__)


@click.group()
@click.pass_context
def config(ctx):
    """Configure CLI for Platform9 management planes."""


@config.command('create')
@click.option('--config_name', '--name', required=True, prompt='Config name')
@click.option('--du_url', '--du', required=True, prompt='Platform9 management URL')
@click.option('--os_username', required=True, prompt='Platform9 user')
@click.option('--os_password', required=True, prompt='Platform9 password', hide_input=True)
@click.option('--os_region', required=True, prompt='Platform9 region')
@click.option('--os_tenant', required=True, prompt='Platform9 tenant', default='service')
@click.pass_context
def create(ctx, config_name, du_url, os_username, os_password, os_region, os_tenant):
    """Create Platform9 management plane config."""
    # creates and activates pf9-express config file
    logger.info(msg=click.get_current_context().info_name)

    pf9_exp_conf_dir = ctx.obj['pf9_db_dir']

    # Backup existing config if one exist
    if os.path.exists(pf9_exp_conf_dir + 'express.conf'):
        with open(pf9_exp_conf_dir + 'express.conf', 'r') as current:
            lines = current.readlines()
            current.close()
        for line in lines:
            if 'config_name|' in line:
                line = line.strip()
                name = line.replace('config_name|', '')

        filename = name + '.conf'
        shutil.copyfile(pf9_exp_conf_dir + 'express.conf', pf9_exp_conf_dir + filename)

    if not os.path.exists(pf9_exp_conf_dir):
        try:
            access_rights = 0o700
            os.makedirs(pf9_exp_conf_dir, access_rights)
        except Exception as except_err:
            logger.exception(except_err)
            click.echo("Creation of the directory %s failed" % pf9_exp_conf_dir)
        else:
            click.echo("Successfully created the directory %s " % pf9_exp_conf_dir)

    with open(pf9_exp_conf_dir + 'express.conf', 'w') as file:
        for k,v in ctx.params.items():
            file.write(k + '|' + str(v) + '\n')
            if k == 'config_name':
                config_name = v
    logger.info('Successfully wrote config: {}'.format(config_name))
    click.echo('Successfully wrote Platform9 management plane configuration')


@config.command('list')
@click.pass_obj
def config_list(obj):
    """List Platform9 management plane configs."""
    logger.info(msg=click.get_current_context().info_name)
    pf9_exp_conf_dir = obj['pf9_db_dir']

    if os.path.exists(pf9_exp_conf_dir):
        count = 1
        result = PrettyTable()
        result.field_names = ["#", "Active", "Conf", "Management Plane", "Region"]
        files = [f for f in os.listdir(pf9_exp_conf_dir) if os.path.isfile(os.path.join(pf9_exp_conf_dir, f))]

        for f in files:
            active = False
            if f == 'express.conf':
                active = True
            with open(pf9_exp_conf_dir + f, 'r') as config_file:
                _config = Get.config_to_dict(config_file)
            if active:
                result.add_row([count, '*', _config["name"], _config["du_url"], _config["os_region"]])
            else:
                result.add_row([count, ' ', _config["name"], _config["du_url"], _config["os_region"]])
            count = count + 1
        click.echo(result)
        logger.info("config list returned successfully")
    else:
        logger.info('No Platform9 management plane configs exist')
        click.echo('No Platform9 management plane configs exist')


@config.command('activate')
@click.argument('config_name')
@click.pass_obj
def activate(obj, config_name):
    """Activate Platform9 management plane config."""
    # activates pf9-express config file
    logger.info(msg=click.get_current_context().info_name)
    logger.info(msg="Activating config %s" % config_name)
    click.echo("Activating config %s" % config_name)
    exp_conf_dir = obj['pf9_db_dir']
    exp_conf_file = obj['pf9_db_dir'] + 'express.conf'

    if os.path.exists(exp_conf_file):
        with open(exp_conf_file, 'r') as current:
            lines = current.readlines()
            current.close()
        for line in lines:
            if 'config_name|' in line:
                line = line.strip()
                name = line.replace('config_name|', '')

        filename = name + '.conf'
        shutil.move(exp_conf_file, exp_conf_dir + filename)

    files = [f for f in os.listdir(exp_conf_dir) if os.path.isfile(os.path.join(exp_conf_dir, f))]

    for f in files:
        if f == (config_name + '.conf'):
            shutil.move(exp_conf_dir + f, exp_conf_file)

    logger.info(msg='Config %s is now active' % config_name)
    click.echo('Config %s is now active' % config_name)


@config.command('validate')
@click.pass_context
def config_validate(ctx):
    """Validates the active config against the Platform9 Management Plane.

    \b
    Success:
        stdout: silent
        rc:     0
    \b
    Failure:
        stdout: Error message
        rc:     1
    """
    logger.info(msg=click.get_current_context().info_name)
    try:
        # Load Active Config into ctx
        Get(ctx).active_config()
        # Get Token
        token = GetToken().get_token_v3(
                ctx.params["du_url"],
                ctx.params["du_username"],
                ctx.params["du_password"],
                ctx.params["du_tenant"])
        if token is None:
            click.echo("Validation of config:[{}] Failed to: {}".format(ctx.params['config_name'], ctx.params["du_url"]))
            msg = "Failed to obtain Authentication from: {}".format(ctx.params["du_url"])
            raise CLIException(msg)
        else:
            logger.info(msg="Config {} Validation Successful".format(ctx.params['config_name']))
            return token
    except (UserAuthFailure, CLIException) as except_msg:
        logger.exception("Config: {} Validation Failed. Exception: {}".format(ctx.params['config_name'], except_msg))
        click.echo("Validation of config:[{}] Failed to: {}".format(ctx.params['config_name'], ctx.params["du_url"]))
        sys.exit(1)
    except Exception as except_msg:
        logger.exception("GENERICALLY CAUGHT EXCEPTION!!! "
                         "Validation of config:{} Failed to: {}: {}".format(
                          ctx.params['config_name'], ctx.params['du_url'], except_msg))
        click.echo("Validation of config:[{}] Failed to: {}".format(ctx.params['config_name'], ctx.params["du_url"]))
        sys.exit(1)
