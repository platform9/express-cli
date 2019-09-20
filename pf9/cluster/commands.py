import click
import os
from prettytable import PrettyTable
from ..modules.ostoken import GetToken

@click.group()
def cluster():
    """Platform9 Managed Kuberenetes Cluster"""

@cluster.command('list')
def define(cluster_list):
  click.echo('WIP -- cluster.cluster_list')


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

