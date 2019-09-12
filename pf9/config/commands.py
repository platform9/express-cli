import click
import os
import shutil
from prettytable import PrettyTable
from ..modules.ostoken import GetToken
from ..modules.util import Utils 

@click.group()
def config():
    """Configure Platform9 Express."""
def manage_dns_resolvers(ctx, param, man_resolvers):
    if man_resolvers:
        if not ctx.params['dns_resolver_1']:
            ctx.params['dns_resolver_1'] = click.prompt('Enter DNS Resolver 1')
        if not ctx.params['dns_resolver_2']:
            ctx.params['dns_resolver_2'] = click.prompt('Enter DNS Resolver 2')
    else:
        ctx.params['dns_resolver_1'] = "8.8.8.8"
        ctx.params['dns_resolver_2'] = "8.8.4.4"
    return man_resolvers

@config.command('create')
@click.option('--config_name', '--name', required=True, prompt='Config name')
@click.option('--du_url', '--du', required=True, prompt='Platform9 management URL')
@click.option('--os_username', required=True, prompt='Platform9 user')
@click.option('--os_password', required=True, prompt='Platform9 password', hide_input=True)
@click.option('--os_region', required=True, prompt='Platform9 region')
@click.option('--os_tenant', required=True, prompt='Platform9 tenant', default='service')
@click.option('--proxy_url', required=True, prompt='Proxy url for internet access', default='-')
@click.option('--manage_hostname', required=True, prompt='Have Platform9 Express manage hostnames', default=False)
@click.option('--dns_resolver_1', prompt='Enter DNS resolver', is_eager=True, default='')
@click.option('--dns_resolver_2', prompt='Enter DNS resolver', is_eager=True, default='')
@click.option('--manage_resolver', required=True, type=bool, prompt='Have Platform9 Express manage DNS resolvers', default=False, callback=manage_dns_resolvers)
@click.pass_context
def create(ctx, **kwargs):
    """Create Platform9 Express config."""
    # creates and activates pf9-express config file

    pf9_exp_conf_dir = ctx.obj['pf9_exp_conf_dir']

    if os.path.exists(pf9_exp_conf_dir + 'express.conf'):
        with open(pf9_exp_conf_dir + 'express.conf', 'r') as current:
            lines = current.readlines()
            current.close()
        for line in lines:
            if 'config_name|' in line:
                line = line.strip()
                name = line.replace('config_name|','')

        filename = name + '.conf'
        shutil.copyfile(pf9_exp_conf_dir + 'express.conf', pf9_exp_conf_dir + filename)

    if not os.path.exists(pf9_exp_conf_dir):
        try:
            os.makedirs(pf9_exp_conf_dir, access_rights)
        except:
            click.echo("Creation of the directory %s failed." % pf9_exp_conf_dir)
        else:
            click.echo("Successfully created the directory %s " % pf9_exp_conf_dir)

    with open(pf9_exp_conf_dir + 'express.conf', 'w') as file:
        for k,v in ctx.params.items():
            file.write(k + '|' + str(v) + '\n')
    click.echo('Successfully wrote Platform9 Express configuration')


@config.command('list')
@click.pass_obj
def list(obj):
    """List Platform9 Express configs."""
    # lists pf9-express config files
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
            with open(pf9_exp_conf_dir + f, 'r') as data:
                for line in data:
                    line = line.strip()
                    if 'config_name|' in line:
                        name = line.replace('config_name|','')
                    if 'du_url' in line:
                        du_url = line.replace('du_url|','')
                    if 'os_region' in line:
                        os_region = line.replace('os_region|','')
                data.close()
                if active:
                    result.add_row([count,'*',name, du_url, os_region])
                else:
                    result.add_row([count,' ',name, du_url, os_region])
            count = count + 1

        print result

    else:
        click.echo('No Platform9 Express configs exist')


@config.command('activate')
@click.argument('config')
@click.pass_obj
def activate(obj, config):
    """Activate Platform9 Express config."""
    # activates pf9-express config file
    click.echo("Activating config %s" % config)
    dir_path = obj['pf9_exp_conf_dir']

    if os.path.exists(dir_path + 'express.conf'):
        with open(dir_path + 'express.conf', 'r') as current:
            lines = current.readlines()
            current.close()
        for line in lines:
            if 'config_name|' in line:
                line = line.strip()
                name = line.replace('config_name|','')

        filename = name + '.conf'
        shutil.move(dir_path + 'express.conf', dir_path + filename)

    files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]

    for f in files:
        if f == (config + '.conf'):
            shutil.move(dir_path + f, dir_path + 'express.conf')

    click.echo('Config %s is now active' % config)


@config.command('validate')
@click.pass_obj
def config_validate(obj):
    """Validate Platform9 Express config."""
    # Validates pf9-express config file and obtains Auth Token
    config_file = os.path.join(obj['pf9_exp_conf_dir'], 'express.conf')
    
    if os.path.exists(config_file):
        config = Utils().config_to_json(config_file)
    else:
        click.echo('No active config. Please define or activate a config.')

    if config is not None:
        token = GetToken().get_token_v3(config["du_url"], config["os_username"], config["os_password"], config["os_tenant"] )
        if token is not None:
            click.echo('Config Validated!')
            click.echo('Token: %s' % token)

