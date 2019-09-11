import click
import subprocess
import time
import os
import json
import requests
import tarfile
import shutil
import urlparse

from os.path import expanduser
from util import Pf9ExpVersion 

from .config.commands import config
from .cli.commands import version 

@click.group()
@click.version_option(message='%(version)s')
@click.pass_context
def cli(ctx):
    """Express.
    A CLI for Platform9 Express.
    """
    # Set Global Vars into context objs
    if ctx.obj is None:
        ctx.obj= dict()
    ctx.obj['home_dir'] = expanduser("~")
    ctx.obj['pf9_dir'] = os.path.join(ctx.obj['home_dir'], 'pf9/')
    ctx.obj['pf9_exp_dir'] = os.path.join(ctx.obj['pf9_dir'], 'pf9-express/')
    ctx.obj['pf9_exp_conf_dir'] = os.path.join(ctx.obj['pf9_exp_dir'], 'config/')

cli.add_command(version)
cli.add_command(config)


@cli.command('init')
@click.pass_obj
def init(obj):
    """Initialize Platform9 Express."""
    #initialize with current version of pf9-express 

    access_rights = 0o755
    pf9_dir = obj['pf9_dir']
    pf9_exp_dir = obj['pf9_exp_dir']
    target_path = pf9_dir + 'express.tar.gz'

    if not os.path.exists(pf9_exp_dir):
        r = requests.get('https://api.github.com/repos/platform9/express/releases/latest')
        response = r.json()
        url = response['tarball_url']
        version = response['name']

        if not os.path.exists(pf9_dir):
            try:
                os.mkdir(pf9_dir, access_rights)
            except OSError:
                print ("Creation of the directory %s failed" % pf9_dir)
            else:
                print ("Successfully created the directory %s " % pf9_dir)

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(target_path, 'wb') as f:
                f.write(response.raw.read())
        
        tar = tarfile.open(target_path, "r:gz")
        tar.extractall(dir_path)
        tar.close()

        with open(pf9_exp_dir + 'version', 'w') as file:
            file.write(version + '\n')
            file.close()

        for dir in next(os.walk(pf9_exp_dir))[1]:
            if 'platform9-express-' in dir:
                os.rename( pf9_exp_dir + dir, pf9_exp_dir + 'express' )
        
        click.echo('Platform9 Express initialization complete')
    else:
        click.echo('Platform9 Express already initialized')


@cli.command('upgrade')
@click.pass_obj
def upgrade(obj):
    """Upgrade Platform9 Express."""
    # upgrade to latest version of pf9-express 
 
    ver = Pf9ExpVersion()
    click.echo(ver.get_latest_json())

    r = requests.get('https://api.github.com/repos/platform9/express/releases/latest')
    response = r.json()
    url = response['tarball_url']
    version = response['name']
    access_rights = 0o755
    pf9_dir = obj['pf9_dir']
    pf9_exp_dir = obj['pf9_exp_dir']
    target_path = pf9_dir + 'express.tar.gz'

    with open(pf9_exp_dir + 'version', 'r') as v:
        line = v.readline()
        line = line.strip()
        v.close()

    if line != version:
        click.echo("we are here, we are really here")
        if not os.path.exists(pf9_exp_dir):
            try:
                os.mkdir(pf9_exp_dir, access_rights)
            except OSError:
                print ("Creation of the directory %s failed" % pf9_exp_dir)
            else:
                print ("Successfully created the directory %s " % pf9_exp_dir)

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(target_path, 'wb') as f:
                f.write(response.raw.read())
        
        tar = tarfile.open(target_path, "r:gz")
        tar.extractall(pf9_exp_dir)
        tar.close()

        os.rename( pf9_exp_dir + 'express', pf9_exp_dir +'express-bak')

        for dir in next(os.walk(pf9_exp_dir))[1]:
            if 'platform9-express-' in dir:
                os.rename( pf9_exp_dir + dir, pf9_exp_dir + 'express' )
        
        shutil.rmtree(pf9_exp_dir + 'express-bak')

        with open(pf9_exp_dir + 'version', 'w') as file:
            file.write(version + '\n')
            file.close()
        
        click.echo('Platform9 Express upgrade complete')
    
    else:
        click.echo('Platform9 Express is already the latest version')


@cli.group()
def cluster():
    """[ WIP ] Platform9 Managed Kuberenetes Cluster"""

@cluster.command('define')
@click.argument('cluster')
@click.option('--user', '-u', required=True, help='Username for cluster nodes.')
@click.option('--password', '-p', help='Password for cluster nodes.')
@click.option('--ssh-key', '-s', help='SSH key for cluster nodes.')
@click.option('--api-fqdn', '-a', required=True, help='FQDN for the API server e.g. k8s.acme.com.')
@click.option('--container-cidr', '-c', required=True, default='10.1.0.0/16', help='CIDR for k8s containers default is 10.1.0.0/16.')
@click.option('--service-cidr', '-c', required=True, default='10.2.0.0/16', help='CIDR for k8s services default is 10.2.0.0/16.')
@click.option('--priviledged', is_flag=True, help='Allow cluster to run priviledged containers')
def define(cluster):
    """[ WIP ] Define a Kubernetes cluster."""
    # create a pf9-express kuberentes cluster inventory file
    click.echo('WIP')

    home = expanduser("~")
    path = home + '/pf9/pf9-express/'
    dir_path = path + 'clusters/'

    if os.path.exists(path + 'config/express.conf'):
        with open(path + 'config/express.conf') as data:
            for line in data:
                line = line.strip()
                if 'config_name|' in line:
                    name = line.replace('config_name|','')
                if 'du_url' in line:
                    du_url = line.replace('du_url|https://','')
                if 'os_region' in line:
                    os_region = line.replace('os_region|','')
            data.close()

    # get token
    # get nodepool uuid

    du_url = 'a'
    tenantid = 'b'
    url = 'https://pf9-cs-k8s-us/qbert/v3/edeb541c711248088752923d4c68ddff/cloudProviders'
    r = requests.get()
    response = r.json()
    for cp in response:
        if cp['type'] == 'local':
            nodepool = cp['nodePoolUuid']
    
    if not os.path.exists(dir_path):
        try:
            os.mkdir(path, access_rights)
        except OSError:
            print ("Creation of the directory %s failed" % path)
        else:
            print ("Successfully created the directory %s " % path)

    if not os.path.exists(dir_path + cluster ):
        click.echo("WIP - DO STUFF")
        # user
        # password or ssh key
        # pod cidr
        # services cidr
        # privledged
        # api fqdn
    else:
        click.echo('A cluster by the name of %s already exists' % cluster)


@cluster.command('add-node')
@click.argument('cluster')
@click.option('--user', '-u', help='Username for node if different than cluster default.')
@click.option('--password', '-p', help='Password for node if different than cluster default.')
@click.option('--ssh-key', '-s', help='SSH key for node if different than cluster default.')
@click.option('--ip', '-i', required=True, help='SSH key for node if different than cluster default.')
@click.option('--host', '-h', required=True, help='hostname for the node.')
@click.option('--execute', is_flag=True, help='Add node to cluster if cluster is already created')
def add_node(cluster):
    """[ WIP ] Define a node for a Kubernetes cluster."""
    # add node to cluster inventory file, add node to cluster if --execute is included
    click.echo('WIP')



    if os.path.exists(dir_path + cluster ):
        click.echo("WIP - DO STUFF")
        # user
        # password or ssh key
        # ip
        # hostname
    else:
        click.echo('There is no defined cluster by the name of %s' % cluster)

# @cluster.command('add-node')
# @click.argument('cluster')
# @click.argument('node')
# def add_node(cluster, node):
#     """Add a node to a Kubernetes cluster after cluster creation."""
#     # add node to cluster inventory file and run pf9-express for node
#     click.echo('WIP')


@cluster.command('build')
@click.argument('cluster')
def build(cluster):
    """[ WIP ] Create a defined Kubernetes cluster."""
    # create a defined cluster in qbert and add defined nodes to cluster
    click.echo('WIP')


@cluster.command('destroy')
@click.argument('cluster')
def destroy(cluster):
    """[ WIP ] Delete a Kuberenetes cluster."""
    # deauthorize defined nodes in a kuberenetes cluster and delete cluster in qbert
    click.echo('WIP')
