import click
import os
from prettytable import PrettyTable
from ..modules.ostoken import GetToken
from ..modules.util import Utils
from .cluster_create import CreateCluster

@click.group()
def cluster():
    """Platform9 Managed Kuberenetes Cluster"""

@cluster.command('create')
@click.option('--cluster_name', help='cluster name', prompt='Cluster Name')
@click.option('--masterVip', help='IP address for VIP for master nodes', prompt='Master VIP')
@click.option('--masterVipIf', help='Interface name for master/worker node', prompt='Master VIP Interface name')
@click.option('--metallbCidr', help='IP range for MetalLB (<startIP>-<endIp>)', prompt='MetalLB IP Range')
@click.option('--containersCidr', type=str, required=False, default='10.20.0.0/16', help="CIDR for container overlay")
@click.option('--servicesCidr', type=str, required=False, default='10.21.0.0/16', help="CIDR for services overlay")
@click.option('--externalDnsName', type=str, required=False, default='', help="External DNS name for master VIP")
@click.option('--privileged', type=bool, required=False, default=True, help="Enable privileged mode for Kubernetes API")
@click.option('--appCatalogEnabled', type=bool, required=False, default=True, help="Enable Helm application catalog")
@click.option('--allowWorkloadsOnMaster', type=bool, required=False, default=False, help="Taint master nodes (to enable workloads)")
@click.option("--networkPlugin", type=str, required=False, default='flannel', help="Specify non-default network plugin (default = flannel)")
@click.pass_context
def create(ctx, **kwargs):
    """Create a Kubernetes cluster."""
    # MOVE TO MODULE!!!
    # Get Variables from Config
    config_file = os.path.join(ctx.obj['pf9_exp_conf_dir'], 'express.conf')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as data:
                config_file_lines = data.readlines()
        except:
            click.echo('Failed reading %s: '% config_file)
        config = Utils().config_to_dict(config_file_lines)
        if config is not None:
            ctx.params['du_url'] = config["du_url"]
            ctx.params['du_username'] = config["os_username"]
            ctx.params['du_password'] = config["os_password"]
            ctx.params['du_tenant'] = config["os_tenant"]
    else:
        click.echo('No active config. Please define or activate a config.')

    # Get Token and Tenant ID (app pulling tenant_ID "project_id" into get_token)
    ctx.params['project_id'] = GetToken().get_project_id(
                config["du_url"],
                config["os_username"],
                config["os_password"],
                config["os_tenant"] )
    ctx.params['token'] = GetToken().get_token_v3(
                config["du_url"],
                config["os_username"],
                config["os_password"],
                config["os_tenant"] )
       
    # create cluster
    click.echo("[Creating Cluster: {}]".format(ctx.params['cluster_name']))
    cluster_status, cluster_uuid = CreateCluster(ctx).cluster_exists()
        
    if cluster_status == True:
        click.echo("cluster already exists")
    else:
        CreateCluster(ctx).create_cluster()
        cluster_uuid = CreateCluster(ctx).wait_for_cluster()
        click.echo("--> UUID = {}".format(cluster_uuid))



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

#@cluster.command('destroy')
#@click.argument('cluster')
#def destroy(cluster):
#    """Delete a Kuberenetes cluster."""
#    # deauthorize defined nodes in a kuberenetes cluster and delete cluster in qbert
#    click.echo('WIP')

