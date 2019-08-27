import click
import subprocess
import time
import os
import json
import requests
import tarfile
import shutil
import urlparse

import util

from os.path import expanduser
from prettytable import PrettyTable


@click.group()
@click.version_option(message='%(version)s')
def cli():
    """Express.
    A CLI for Platform9 Express.
    """


@cli.command('init')
def init():
    """Initialize Platform9 Express."""
    #initialize with current version of pf9-express 


    home = expanduser("~")
    access_rights = 0o755
    path = home + '/pf9/'
    dir_path = path + 'pf9-express/'
    target_path = path + 'express.tar.gz'

    if not os.path.exists(dir_path):
        r = requests.get('https://api.github.com/repos/platform9/express/releases/latest')
        response = r.json()
        url = response['tarball_url']
        version = response['name']

        if not os.path.exists(path):
            try:
                os.mkdir(path, access_rights)
            except OSError:
                print ("Creation of the directory %s failed" % path)
            else:
                print ("Successfully created the directory %s " % path)

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(target_path, 'wb') as f:
                f.write(response.raw.read())
        
        tar = tarfile.open(target_path, "r:gz")
        tar.extractall(dir_path)
        tar.close()

        with open(dir_path + 'version', 'w') as file:
            file.write(version + '\n')
            file.close()

        for dir in next(os.walk(dir_path))[1]:
            if 'platform9-express-' in dir:
                os.rename( dir_path + dir, dir_path + 'express' )
        
        click.echo('Platform9 Express initialization complete')
    else:
        click.echo('Platform9 Express already initialized')


@cli.command('version')
def version():
    """Show Platform9 Express version."""
    # print current version of pf9-express 

    home = expanduser("~")
    path = home + '/pf9/'
    dir_path = path + 'pf9-express/'

    with open(dir_path + 'version', 'r') as v:
        line = v.readline()
        line = line.strip()
        v.close()
    
    click.echo('Platform9 Express: %s' % line)


@cli.command('upgrade')
def upgrade():
    """Upgrade Platform9 Express."""
    # upgrade to latest version of pf9-express 
 
    r = requests.get('https://api.github.com/repos/platform9/express/releases/latest')
    response = r.json()
    url = response['tarball_url']
    version = response['name']
    home = expanduser("~")
    access_rights = 0o755
    path = home + '/pf9/'
    dir_path = path + 'pf9-express/'
    target_path = path + 'express.tar.gz'

    with open(dir_path + 'version', 'r') as v:
        line = v.readline()
        line = line.strip()
        v.close()

    if line != version:
        click.echo("we are here, we are really here")
        if not os.path.exists(path):
            try:
                os.mkdir(path, access_rights)
            except OSError:
                print ("Creation of the directory %s failed" % path)
            else:
                print ("Successfully created the directory %s " % path)

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(target_path, 'wb') as f:
                f.write(response.raw.read())
        
        tar = tarfile.open(target_path, "r:gz")
        tar.extractall(dir_path)
        tar.close()

        os.rename( dir_path + 'express', dir_path +'express-bak')

        for dir in next(os.walk(dir_path))[1]:
            if 'platform9-express-' in dir:
                os.rename( dir_path + dir, dir_path + 'express' )
        
        shutil.rmtree(dir_path + 'express-bak')

        with open(dir_path + 'version', 'w') as file:
            file.write(version + '\n')
            file.close()
        
        click.echo('Platform9 Express upgrade complete')
    
    else:
        click.echo('Platform9 Express is already the latest version')


@cli.group()
def config():
    """Configure Platform9 Express."""


@config.command('create')
def create():
    """Create Platform9 Express config."""
    # creates and activates pf9-express config file 

    home = expanduser("~")
    access_rights = 0o755
    path = home + '/pf9/'
    dir_path = path + 'pf9-express/config/'
    
    if os.path.exists(dir_path + 'express.conf'):
        with open(dir_path + 'express.conf', 'r') as current:
            lines = current.readlines()
            current.close()
        for line in lines:
            if 'config_name|' in line:
                line = line.strip()
                name = line.replace('config_name|','')
        
        filename = name + '.conf'
        shutil.copyfile(dir_path + 'express.conf', dir_path + filename)

    prompts = {}
    prompts['config_name'] = click.prompt('Config name', type=str)
    prompts['du_url'] = click.prompt('Platform9 management URL', type=str)
    prompts['os_username'] = click.prompt('Platform9 user', type=str)
    prompts['os_password'] = click.prompt('Platform9 password', hide_input=True, type=str)
    prompts['os_region'] = click.prompt('Platform9 region', type=str)
    prompts['os_tenant'] = click.prompt('Platform9 tenant', default='service', type=str)
    prompts['proxy_url'] = click.prompt('Proxy url for internet access', default='-', type=str)
    prompts['manage_hostname'] = click.prompt('Have Platform9 Express manage hostnames', default=False, type=str)
    prompts['manage_resolver'] = click.prompt('Have Platform9 Express manage DNS resolvers', default=False, type=bool)

    if prompts['manage_resolver']:
        prompts['dns_resolver1'] = click.prompt('Platform9 management URL:', type=str)
        prompts['dns_resolver2'] = click.prompt('Platform9 management URL:', type=str)
    else:
        prompts['dns_resolver1'] = '8.8.8.8'
        prompts['dns_resolver2'] = '8.8.4.4'

    if not os.path.exists(dir_path):
        try:
            os.mkdir(dir_path, access_rights)
        except OSError:
            click.echo("Creation of the directory %s failed" % dir_path)
        else:
            click.echo("Successfully created the directory %s " % dir_path)
    
    with open(dir_path + 'express.conf', 'w') as file:
        for k,v in prompts.items():
            file.write(k + '|' + str(v) + '\n')
    file.close()
    click.echo('Successfully wrote Platform9 Express configuration')


@config.command('list')
def list():
    """List Platform9 Express configs."""
    # lists pf9-express config files 
    home = expanduser("~")
    path = home + '/pf9/'
    dir_path = path + 'pf9-express/config/'

    count = 1
    result = PrettyTable()
    result.field_names = ["#","Active", "Conf", "Management Plane", "Region"]
    files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]

    for f in files:
        active = False
        if f == 'express.conf':
            active = True
        with open(dir_path + f, 'r') as data:
            for line in data:
                line = line.strip()
                if 'config_name|' in line:
                    name = line.replace('config_name|','')
                if 'du_url' in line:
                    du_url = line.replace('du_url|https://','')
                if 'os_region' in line:
                    os_region = line.replace('os_region|','')
            data.close()
            if active:
                result.add_row([count,'*',name, du_url, os_region])
            else:
                result.add_row([count,' ',name, du_url, os_region])
        count = count + 1
    
    print result


@config.command('activate')
@click.argument('config')
def activate(config):
    """Activate Platform9 Express config."""
    # activates pf9-express config file 
    click.echo("Activating config %s" % config)
    home = expanduser("~")
    path = home + '/pf9/'
    dir_path = path + 'pf9-express/config/'

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


@cli.group()
def cluster():
    """Platform9 Managed Kuberenetes Cluster"""

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
    """Define a Kubernetes cluster."""
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
    """Define a node for a Kubernetes cluster."""
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


@cluster.command('create')
@click.argument('cluster')
def create(cluster):
    """Create a defined Kubernetes cluster."""
    # create a defined cluster in qbert and add defined nodes to cluster
    click.echo('WIP')


@cluster.command('destroy')
@click.argument('cluster')
def destroy(cluster):
    """Delete a Kuberenetes cluster."""
    # deauthorize defined nodes in a kuberenetes cluster and delete cluster in qbert
    click.echo('WIP')