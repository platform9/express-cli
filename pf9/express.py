import click
import subprocess
import time
import os
import json
import docker


@click.group()
@click.version_option(message='%(version)s')
def cli():
    """Express.
    A CLI for Platform9 Express.
    """

@cli.command('init')
def init():
    """Initialize Platform9 Express."""
   # checks for Docker install, pulls Express image, provides sample express inventory file 
    click.echo('WIP')
    client = docker.from_env()
    # image = client.images.pull('pf9dockerhub/pf9express:latest')
    retcode = subprocess.call(['docker', 'image', 'pull', img_str])

@cli.command('prep')
@click.option('--config', '-c', default='~/pf9/express.conf', help='Platoform9 Express conf file location.')
@click.option('--inventory', '-i', default='~/pf9/hosts', help='Inventory file location.')
@click.option('--target', '-t', default='all', help='Platform9 Express target host/group.')
def run(config, inventory, target):
    """Run Platform9 Express Host Pre-requisites."""
    # client = docker.from_env()
    homedir = os.environ['HOME']

    if '~' in config or inventory:
        config = config.replace('~', homedir)
        inventory = inventory.replace('~', homedir)

    conf_map = config + ':/pf9/express.conf'
    inv_map = inventory + ':/pf9/hosts'

    click.echo('Using inventory file located at %s with target %s' % (inventory, target))
    subprocess.call(['docker', 'run', '-e', 'ANSIBLE_HOST_KEY_CHECKING=False', '-v', conf_map, '-v', inv_map, 'pf9dockerhub/pf9express', '-b', '-c', '/pf9/express.conf', '-v', '/pf9/hosts', target])
    click.echo('Platform9 Express Run Complete')

@cli.command('authorize')
@click.argument('inventory')
@click.argument('target')
def run(inventory, target):
    """Run Platform9 Express Host Pre-requisites and Authorize."""
    client = docker.from_env()
    click.echo('Using inventory file located at %s with target %s' % (inventory, target))
    command = '-b -v ' + inventory + ' -a ' + target

    click.echo('Platform9 Express Run Complete')

@cli.command('deauthorize')
@click.argument('inventory')
@click.argument('target')
def run(inventory, target):
    """Run Platform9 Express Host to Deauthorize Hosts."""
    client = docker.from_env()
    click.echo('Using inventory file located at %s with target %s' % (inventory, target))
    command = '-b -v ' + inventory + ' -d ' + target

    click.echo('Platform9 Express Run Complete')

@cli.command('upgrade')
@click.option('--version', '-v', default='0', help='Platform9 Express version.')
@click.option('--debug', is_flag=True)
def pmo_cloud_list(version, debug):
    """Upgrade Platform9 Express."""
    client = docker.from_env()
    if version == '0':
        click.echo('Upgrading Platform9 Express to latest version')
        # image = client.images.pull('pf9dockerhub/pf9express:latest')
        retcode = subprocess.call(['docker', 'image', 'pull', 'pf9dockerhub/pf9express:latest'])

    else:
        img_str = 'pf9dockerhub/pf9express:' + version
        click.echo('Upgrading Platform9 Express to version %s' % img_str)
        try:
            image = client.images.pull(img_str)
            # retcode = subprocess.call(['docker', 'image', 'pull', img_str])
        except Exception as e:
            click.echo('An error has occured attempting to upgrade to version %s' % version)
            if debug:
                click.echo(str(e))

    # click.echo('WIP')