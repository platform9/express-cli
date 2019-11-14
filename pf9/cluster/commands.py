import click
import os
from prettytable import PrettyTable
import shlex
from string import Template
import subprocess
import sys
import tempfile
from ..modules.ostoken import GetToken
from ..modules.util import GetConfig 
from ..modules.util import Utils
from .cluster_create import CreateCluster
from .cluster_attach import AttachCluster

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

def get_token_project(ctx):
    GetConfig(ctx).GetActiveConfig()

    # Get Token and Tenant ID (app pulling tenant_ID "project_id" into get_token)
    auth_obj = GetToken()
    token, project_id = auth_obj.get_token_project(
                ctx.params["du_url"],
                ctx.params["os_username"],
                ctx.params["os_password"],
                ctx.params["os_tenant"] )

    return token, project_id

def create_cluster(ctx):
    
    # create cluster
    click.echo("[Creating Cluster: {}]".format(ctx.params['cluster_name']))
    cluster_status, cluster_uuid = CreateCluster(ctx).cluster_exists()
        
    if cluster_status == True:
        click.echo("cluster already exists")
    else:
        CreateCluster(ctx).create_cluster()
        cluster_uuid = CreateCluster(ctx).wait_for_cluster()

    return cluster_uuid


def attach_cluster(ctx):
    # Attach to cluster
    cluster_attacher = AttachCluster(ctx)
    cluster_name = ctx.params['cluster_name']

    click.echo("[Attaching to cluster {}]".format(cluster_name))
    status, cluster_uuid = cluster_attacher.cluster_exists(cluster_name)

    if status == False:
        click.echo("Cluster {} doesn't exist. Provide name of an existing cluster".format(
                    ctx.params['cluster_name']))
        # TODO: How should the error be handled?
        sys.exit(1)

    master_ips = ctx.params['master_ip']
    master_nodes = cluster_attacher.get_uuids(master_ips)
    click.echo("[Discovering UUIDs for Cluster Nodes]")
    click.echo("--> Master Nodes")
    for node in master_nodes:
        click.echo("{}".format(node))

    # get uuids for worker nodes
    worker_ips = ctx.params['worker_ip']
    worker_nodes = cluster_attacher.get_uuids(worker_ips)
    click.echo("--> Worker Nodes")
    for node in worker_nodes:
        click.echo("{}".format(node))

    # wait for cluster to by ready
    click.echo("\n[Attaching to Cluster: {}]".format(cluster_name))
    #TODO: Why is this even required??
    cluster_uuid = cluster_attacher.wait_for_cluster(cluster_name)

    # attach master nodes
    cluster_attacher.attach_to_cluster(cluster_uuid, 'master', master_nodes)
    cluster_attacher.wait_for_n_active_masters(cluster_name, len(master_nodes))

    # attach worker nodes
    cluster_attacher.attach_to_cluster(cluster_uuid, 'worker', worker_nodes)


def prep_node(ctx, user, password, ssh_key, ips, node_prep_only):
    only_local_node = False
    if len(ips) == 1 and ips[0] == 'localhost':
        only_local_node = True
        click.echo('Prepping the local node to be added to Platform9 Managed Kubernetes')

    inv_file = build_express_inventory_file(ctx, user, password, ssh_key, ips,
                                            only_local_node, node_prep_only)
    rcode, output = run_express(ctx, inv_file)

    return rcode, output

@click.group()
def cluster():
    """Platform9 Managed Kuberenetes Cluster"""

@cluster.command('bootstrap')
@click.argument('cluster_name')
@click.option('--masterVip', help='IP address for VIP for master nodes', default='')
@click.option('--masterVipIf', help='Interface name for master/worker node', default='')
@click.option('--metallbCidr', help='IP range for MetalLB (<startIP>-<endIp>)', default='')
@click.option('--containersCidr', type=str, required=False, default='10.20.0.0/16', help="CIDR for container overlay")
@click.option('--servicesCidr', type=str, required=False, default='10.21.0.0/16', help="CIDR for services overlay")
@click.option('--externalDnsName', type=str, required=False, default='', help="External DNS name for master VIP")
@click.option('--privileged', type=bool, required=False, default=True, help="Enable privileged mode for Kubernetes API")
@click.option('--appCatalogEnabled', type=bool, required=False, default=False, help="Enable Helm application catalog")
@click.option('--allowWorkloadsOnMaster', type=bool, required=False, default=False, help="Taint master nodes (to enable workloads)")
@click.option("--networkPlugin", type=str, required=False, default='flannel', help="Specify non-default network plugin (default = flannel)")
@click.option('--user', '-u', help='Username for node.')
@click.option('--password', '-p', help='Password for node if different than cluster default.')
@click.option('--ssh-key', '-s', help='SSH key for node if different than cluster default.')
@click.option('--master-ip', '-m', multiple=True, help='IPs of the master nodes.', prompt="IP of the master node", default='localhost') #Confirm this behavior
@click.option('--worker-ip', '-w', multiple=True, help='IPs of the worker nodes.', default='')
@click.pass_context
def bootstrap(ctx, **kwargs):
    """Create a Kubernetes cluster."""

    master_ips = ctx.params['master_ip']
    ctx.params['master_ip'] = ''.join(master_ips).split(' ') if all(len(x)==1 for x in master_ips) else master_ips
    
    worker_ips = ctx.params['worker_ip']
    ctx.params['worker_ip'] = ''.join(worker_ips).split(' ') if all(len(x)==1 for x in worker_ips) else worker_ips

    # Do input validation
    ctx.params['token'], ctx.params['project_id'] = get_token_project(ctx)

    # TODO: Can these be undefined?
    all_ips = ctx.params['master_ip'] + ctx.params['worker_ip']

    if len(all_ips) > 0:
        # Nodes are provided. So prep them.
        adj_ips = ()
        for ip in all_ips:
            if ip == "127.0.0.1" or ip == "localhost" \
                or ip in Utils().get_local_node_addresses():

                adj_ips = adj_ips + ("localhost",)
            else:
                adj_ips = adj_ips + (ip,)
            rcode, output = prep_node(ctx, ctx.params['user'], ctx.params['password'],
                                    ctx.params['ssh_key'], adj_ips,
                                    node_prep_only=True)

    cluster_uuid = create_cluster(ctx)
    click.echo("--> Cluster UUID = {}".format(cluster_uuid))

    # TODO: Probably users should never specify localhost, 127.0.0.1.
    if len(all_ips) > 0:
        # Attach nodes
        attach_cluster(ctx)


@cluster.command('create')
@click.argument('cluster_name')
@click.option('--masterVip', help='IP address for VIP for master nodes', default='')
@click.option('--masterVipIf', help='Interface name for master/worker node', default='')
@click.option('--metallbCidr', help='IP range for MetalLB (<startIP>-<endIp>)', default='')
@click.option('--containersCidr', type=str, required=False, default='10.20.0.0/16', help="CIDR for container overlay")
@click.option('--servicesCidr', type=str, required=False, default='10.21.0.0/16', help="CIDR for services overlay")
@click.option('--externalDnsName', type=str, required=False, default='', help="External DNS name for master VIP")
@click.option('--privileged', type=bool, required=False, default=True, help="Enable privileged mode for Kubernetes API")
@click.option('--appCatalogEnabled', type=bool, required=False, default=False, help="Enable Helm application catalog")
@click.option('--allowWorkloadsOnMaster', type=bool, required=False, default=False, help="Taint master nodes (to enable workloads)")
@click.option("--networkPlugin", type=str, required=False, default='flannel', help="Specify non-default network plugin (default = flannel)")
@click.pass_context
def create(ctx, **kwargs):
    ctx.params['token'], ctx.params['project_id'] = get_token_project(ctx)
    cluster_uuid = create_cluster(ctx)
    click.echo("--> Cluster UUID = {}".format(cluster_uuid))


@cluster.command('attach-node')
@click.argument('cluster_name')
@click.option('--master-ip', '-m', multiple=True, help='IP of the node to be added as masters')
@click.option('--worker-ip', '-w', multiple=True, help='IP of the node to be added as workers')
@click.pass_context
def attach_node(ctx, **kwargs):
    ctx.params['token'], ctx.params['project_id'] = get_token_project(ctx)
    attach_cluster(ctx)

@cluster.command('prep-node')
@click.option('--user', '-u', help='Username for node.')
@click.option('--password', '-p', help='Password for node if different than cluster default.')
@click.option('--ssh-key', '-s', help='SSH key for node if different than cluster default.')
@click.option('--ips', '-i', multiple=True, help='IPs of the host to be prepped.', prompt="IP of the node to be prepped", default=('localhost',))
@click.pass_context
def prepnode(ctx, user, password, ssh_key, ips):

    # Oversmart click does some bs processing if the multiple value option (ips)
    # has just one value provided. Seriously! - Need this work around.
    parse_ips = ''.join(ips).split(' ') if all(len(x)==1 for x in ips) else ips
    adj_ips = ()
    for ip in parse_ips:
        if ip == "127.0.0.1" or ip == "localhost" \
            or ip in Utils().get_local_node_addresses():

            adj_ips = adj_ips + ("localhost",)
        else:
            adj_ips = adj_ips + (ip,)

    rcode, output = prep_node(ctx, user, password, ssh, key,
                              adj_ips, node_prep_only=True)

    #TODO: Report success/failure
