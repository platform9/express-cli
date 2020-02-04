"""Express Config Module"""
import os
import sys
import shutil
import click
from prettytable import PrettyTable
from ..exceptions import CLIException
from ..exceptions import UserAuthFailure
from ..modules.ostoken import GetToken
from ..modules.ostoken import GetRegionURL
from ..modules.util import Utils
from ..modules.util import GetConfig


@click.group()
def config():
    """Configure CLI for Platform9 management planes."""


def manage_dns_resolvers(ctx, value):
    """Selectively Prompt for DNS Servers"""

    if value:
        if ctx.params['dns_resolver1'] is None:
            ctx.params['dns_resolver1'] = click.prompt('Enter DNS Resolver 1')
        if ctx.params['dns_resolver2'] is None:
            ctx.params['dns_resolver2'] = click.prompt('Enter DNS Resolver 2')
    else:
        ctx.params['dns_resolver1'] = "8.8.8.8"
        ctx.params['dns_resolver2'] = "8.8.4.4"
    return value


@config.command('create')
@click.option('--config_name', '--name', required=True, prompt='Config name')
@click.option('--du_url', '--du', required=True, prompt='Platform9 management URL')
@click.option('--os_username', required=True, prompt='Platform9 user')
@click.option('--os_password', required=True, prompt='Platform9 password', hide_input=True)
@click.option('--os_region', required=True, prompt='Platform9 region')
@click.option('--os_tenant', required=True, prompt='Platform9 tenant', default='service')
@click.option('--proxy_url', default='-')
@click.option('--manage_hostname', default=False)
@click.option('--dns_resolver1', is_eager=True)
@click.option('--dns_resolver2', is_eager=True)
@click.option('--manage_resolver', type=bool, default=False, callback=manage_dns_resolvers)
@click.pass_context
def create(ctx, **kwargs):
    """Create Platform9 management plane config."""
    # creates and activates pf9-express config file

    pf9_exp_conf_dir = ctx.obj['pf9_exp_conf_dir']

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
        except Exception:
            click.echo("Creation of the directory %s failed" % pf9_exp_conf_dir)
        else:
            click.echo("Successfully created the directory %s " % pf9_exp_conf_dir)

    with open(pf9_exp_conf_dir + 'express.conf', 'w') as file:
        for k,v in ctx.params.items():
            file.write(k + '|' + str(v) + '\n')
    click.echo('Successfully wrote Platform9 management plane configuration')


@config.command('list')
@click.pass_obj
def config_list(obj):
    """List Platform9 management plane configs."""
    pf9_exp_conf_dir = obj['pf9_exp_conf_dir']

    if os.path.exists(pf9_exp_conf_dir):
        count = 1
        result = PrettyTable()
        result.field_names = ["#","Active", "Conf", "Management Plane", "Region"]
        files = [f for f in os.listdir(pf9_exp_conf_dir) if os.path.isfile(os.path.join(pf9_exp_conf_dir, f))]

        for f in files:
            active = False
            if f == 'express.conf':
                active = True
            with open(pf9_exp_conf_dir + f, 'r') as config_file:
                _config = Utils().config_to_dict(config_file)
            if active:
                result.add_row([count,'*', _config["name"], _config["du_url"], _config["os_region"]])
            else:
                result.add_row([count,' ', _config["name"], _config["du_url"], _config["os_region"]])
            count = count + 1

        click.echo(result)

    else:
        click.echo('No Platform9 management plane configs exist')


@config.command('activate')
@click.argument('config_name')
@click.pass_obj
def activate(obj, config_name):
    """Activate Platform9 management plane config."""
    
    click.echo("Activating config {}".format(config_name))
    click.echo("    config: {}".format(config_name))
    click.echo("    type: {}".format(type(config_name)))
    exp_conf_path = obj['pf9_exp_conf_dir'] + 'express.conf'
    click.echo("Get current express.conf")
    if os.path.exists(exp_conf_path):
        with open(exp_conf_path, 'r') as exp_conf_read:
            exp_conf= exp_conf_read.readline()
            exp_conf_read.close()
        click.echo("config.activate:\n    exp_conf: {}".format(exp_conf))
        for line in exp_conf:
            click.echo("    line: {}".format(line))
            if 'config_name|' in line:
                line = line.strip()
                name = line.replace('config_name|','')

        filename = name + '.conf'
        shutil.move(exp_conf_path + 'express.conf', exp_conf_path + filename)

    files = [f for f in os.listdir(exp_conf_path) if os.path.isfile(os.path.join(exp_conf_path, f))]

    for f in files:
        if f == (config_name + '.conf'):
            shutil.move(exp_conf_path + f, exp_conf_path + 'express.conf')

    click.echo('Config %s is now active' % config_name)


@config.command('validate')
@click.pass_context
def config_validate(ctx):
    """Validate active Platform9 management plane config."""
    # Validates pf9-express config file and obtains Auth Token
    # Load Active Config into ctx
    GetConfig(ctx).get_active_config()
    #Get Token
    try:
        token = GetToken().get_token_v3(
                ctx.params["du_url"],
                ctx.params["du_username"],
                ctx.params["du_password"],
                ctx.params["du_tenant"] )
        if token is None:
            msg = "Failed to obtain Authentication from: {}".format(ctx.params["du_url"])
            raise CLIException(msg)
        else:
            return token
    except (UserAuthFailure, CLIException) as e:
        click.echo(e, err=True)
        sys.exit(1)
    except Exception as e:
        click.echo("Message: {}\n    type: {}".format(e, type(e)), err=True)
        sys.exit(1)

@config.command('get-token')
@click.pass_context
def get_token(ctx, **kwargs):
    """Validate active Platform9 management plane config."""
    # Validates pf9-express config file and obtains Auth Token
    #Load Active Config into ctx
    GetConfig(ctx).get_active_config()
    #Get Token
    try:
        token = GetToken().get_token_v3(
                ctx.params["du_url"],
                ctx.params["du_username"],
                ctx.params["du_password"],
                ctx.params["du_tenant"] )
        if token is not None:
            click.echo("Management Plane: {}".format(ctx.params["du_url"]))
            click.echo("Username: {}".format(ctx.params["du_username"]))
            click.echo("Region: {}".format(ctx.params["du_region"]))
            click.echo("Token: %s" % token)
        else:
            msg = "Failed to obtain Authentication from: {}".format(ctx.params["du_url"])
            raise CLIException(msg)
    except (UserAuthFailure, CLIException) as e:
        click.echo(e, err=True)
        sys.exit(1)
    except Exception as e:
        click.echo("Message: {}\n    type: {}".format(e, type(e)), err=True)
        sys.exit(1)

@config.command('get-region-url')
@click.pass_context
def test_get_region_url(ctx):
    """test get_region_url."""
    GetConfig(ctx).get_active_config()
    #Get Token
    try:
        region_url = GetRegionURL(
                ctx.params["du_url"],
                ctx.params["du_username"],
                ctx.params["du_password"],
                ctx.params["du_tenant"],
                ctx.params["du_region"]
                ).get_region_url()
        if region_url is None:
            msg = "Failed to obtain region url from: {} \
                    for region: {}".format(ctx.param["du_url"], ctx.param["du_region"])
            raise CLIException(msg)
        print(region_url)

    except (UserAuthFailure, CLIException) as e:
        click.echo(e)
        sys.exit(1)
    except Exception as e:
        click.echo(e)
        sys.exit(1)
