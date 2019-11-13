import click
import os
from prettytable import PrettyTable
import shlex
from string import Template
import subprocess
import tempfile
from ..modules.ostoken import GetToken
from ..modules.util import GetConfig 
from ..modules.util import Utils
from .cluster_utils import ClusterUtils
from .cluster_attach import ClusterAttach

def run_command(command, run_env=os.environ):
    try:
        out = subprocess.check_output(shlex.split(command), env=run_env)
        # Command was successful, return code must be 0 with relevant output
        return 0, out
    except subprocess.CalledProcessError as e:
        click.echo('%s command failed: %s', command, e)
        return e.returncode, e.output

def run_express(ctx, inv_file):
    # Build the pf9-express command to run
    exp_ansible_runner = os.path.join(ctx.obj['pf9_exp_dir'], 'express', 'pf9-express')
    exp_config_file = os.path.join(ctx.obj['pf9_exp_dir'], 'config', 'express.conf')
    # TODO: Make this run only PMK tasks
    cmd = 'sudo {0} -a -b -v {1} -c {2} pmk'.format(exp_ansible_runner, inv_file,
                                                    exp_config_file)
    return run_command(cmd)

# NOTE: a utils file may be a better location for these helper methods
def build_express_inventory_file(ctx, user, password, ssh_key, ips,
                                 only_local_node=False, node_prep_only=False):
    inv_file_path = None
    inv_tpl_contents = None
    node_details = ''
    # Read in inventory template file
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    inv_file_template = os.path.join(cur_dir_path, '..', 'templates',
                                     'pmk_inventory.tpl')

    with open(inv_file_template) as f:
        inv_tpl_contents = f.read()

    if node_prep_only:
        # Create a temp inventory file
        tmp_dir = tempfile.mkdtemp(prefix='pf9_')
        inv_file_path = os.path.join(tmp_dir, 'exp-inventory')

        if only_local_node:
            node_details = 'localhost ansible_connection=local ansible_host=localhost\n'
        else:
            # Build the great inventory file
            for ip in ips:
                if ip == 'localhost':
                    node_info = 'localhost ansible_connection=local ansible_host=localhost\n'
                else:
                    if password:
                        node_info = '{0} ansible_user={1} ansible_ssh_pass={2}\n'.format(
                                     ip, user, password)
                    else:
                        node_info = '{0} ansible_user={1} ansible_ssh_private_key_file={2}\n'.format(
                                     ip, user, ssh_key)
                node_details = "".join((node_details, node_info))

        inv_template = Template(inv_tpl_contents)
        file_data = inv_template.safe_substitute(node_details=node_details)
        with open(inv_file_path, 'w') as inv_file:
            inv_file.write(file_data)
        
    else:
        # Build inventory file in specific dir hierarchy
        # TODO: to be implemented
        pass

    return inv_file_path

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
    #Load Active Config into ctx 
    GetConfig(ctx).GetActiveConfig()
    #Get Token
    ctx.params['project_id'] = GetToken().get_project_id(
                ctx.params["du_url"],
                ctx.params["du_username"],
                ctx.params["du_password"],
                ctx.params["du_tenant"] )
    # Tenant ID
    ctx.params['token'] = GetToken().get_token_v3(
                ctx.params["du_url"],
                ctx.params["du_username"],
                ctx.params["du_password"],
                ctx.params["du_tenant"] )
       
    # create cluster
    click.echo("[Creating Cluster: {}]".format(ctx.params['cluster_name']))
    cluster_status, cluster_uuid = ClusterUtils(ctx).cluster_exists()
        
    if cluster_status == True:
        click.echo("cluster already exists")
    else:
        ClusterUtils(ctx).create_cluster()
        cluster_uuid = ClusterUtils(ctx).wait_for_cluster()
        click.echo("--> UUID = {}".format(cluster_uuid))


@cluster.command('attach')
@click.option('--cluster_name', help='cluster name', prompt='Cluster Name')
@click.option('--master_nodes', type=str, required=False, help='comma-delimited list of ip addresses', prompt='IP addresses of Master nodes')
@click.option('--worker_nodes', type=str, required=False, help='comma-delimited list of ip addresses', prompt='IP addresses of Worker nodes')
@click.pass_context

def attach(ctx, **kwargs):
    """Add Nodes to an existing Kubernetes cluster."""
    if ctx.params['master_nodes'] is None and ctx.params['work_nodes'] is None:
        click.echo("Either master_nodes or worker_nodes must be provided")
        sys.exit(1)

    # Load Active Config into ctx 
    GetConfig(ctx).GetActiveConfig()
    # Tenant ID
    ctx.params['project_id'] = GetToken().get_project_id(
                ctx.params["du_url"],
                ctx.params["du_username"],
                ctx.params["du_password"],
                ctx.params["du_tenant"] )
    # Get Token
    ctx.params['token'] = GetToken().get_token_v3(
                ctx.params["du_url"],
                ctx.params["du_username"],
                ctx.params["du_password"],
                ctx.params["du_tenant"] )

    try:
        cluster_uuid = ClusterUtils(ctx).wait_for_cluster()
    except:
        click.echo("Cluster %s does not exist or is not available for node attachment" % cluster_uuid)
        sys.exit(1) 
        
    click.echo("Discovering UUIDs for Cluster Nodes")
    # get uuids for master nodes
    if ctx.params['master_nodes'] is not None:
        master_node_uuids = ClusterUtils(ctx).get_uuids(ctx.params['master_nodes'].split(','))
        click.echo("--> Master Nodes")
        for node in master_node_uuids:
            click.echo("{}".format(node))

    # get uuids for worker nodes
    if ctx.params['master_nodes'] is not None:
        worker_node_uuids = ClusterUtils(ctx).get_uuids(ctx.params['worker_nodes'].split(','))
        click.echo("--> Worker Nodes")
        for node in worker_node_uuids:
            click.echo("{}".format(node))

    click.echo("[Attaching nodes to Cluster: {}]".format(ctx.params['cluster_name']))

    # attach master nodes
    ClusterAttach(ctx).attach_to_cluster(cluster_uuid, 'master', master_node_uuids)
    ClusterUtils(ctx).wait_for_n_active_masters(len(ctx.params['master_nodes'].split(',')))

    # attach worker nodes
    ClusterAttach(ctx).attach_to_cluster(cluster_uuid, 'worker', worker_node_uuids)




@cluster.command('list', hidden=True)
def define(cluster_list):
  click.echo('WIP -- cluster.cluster_list')


@cluster.command('define', hidden=True)
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


# @cluster.command('add-node')
# @click.argument('cluster')
# @click.argument('node')
# def add_node(cluster, node):
#     """Add a node to a Kubernetes cluster after cluster creation."""
#     # add node to cluster inventory file and run pf9-express for node
#     click.echo('WIP')


@cluster.command('destroy', hidden=True)
@click.argument('cluster')
def destroy(cluster):
    """Delete a Kuberenetes cluster."""
    # deauthorize defined nodes in a kuberenetes cluster and delete cluster in qbert
    click.echo('WIP')

@cluster.command('prep-node')
@click.option('--user', '-u', help='Username for node.')
@click.option('--password', '-p', help='Password for node if different than cluster default.')
@click.option('--ssh-key', '-s', help='SSH key for node if different than cluster default.')
@click.option('--ips', '-i', multiple=True, help='IPs of the host to be prepped.', default='localhost')
@click.pass_context
def prepnode(ctx, user, password, ssh_key, ips):
    only_local_node = False
    if len(ips) == 1 and ips[0] == 'localhost':
        only_local_node = True
        click.echo('Prepping the local node to be added to Platform9 Managed Kubernetes')

    inv_file = build_express_inventory_file(ctx, user, password, ssh_key, ips,
                                            only_local_node, node_prep_only=True)
    rcode, output = run_express(ctx, inv_file)

    #TODO: Report success/failure
    click.echo('WIP')
