import click
from datetime import datetime
import os
from prettytable import PrettyTable
import shlex
from string import Template
import subprocess
import sys
import tempfile
import time
from ..exceptions import CLIException, PrepNodeFailed
from .helpers import validate_ssh_details, get_local_node_addresses, check_vip_needed
from ..modules.ostoken import GetToken
from ..modules.util import GetConfig 
from ..modules.util import Utils
from .cluster_create import CreateCluster
from .cluster_attach import AttachCluster

def print_help_msg(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))

def run_command(command, run_env=os.environ):
    try:
        out = subprocess.check_output(shlex.split(command), env=run_env)
        # Command was successful, return code must be 0 with relevant output
        return 0, out
    except subprocess.CalledProcessError as e:
        click.echo('%s command failed: %s', command, e)
        return e.returncode, e.output

def run_express(ctx, inv_file, ips):
    # Build the pf9-express command to run
    exp_ansible_runner = os.path.join(ctx.obj['pf9_exp_dir'], 'express', 'pf9-express')
    exp_config_file = os.path.join(ctx.obj['pf9_exp_dir'], 'config', 'express.conf')
    log_file = os.path.join("/var/log/pf9",
                            datetime.now().strftime('express_%Y_%m_%d-%H_%m_%S.log'))
    # Invoke PMK only related playbook.
    # Should this be defined directly in the inv file template? It could be a global setting
    # for CLI inventory files.
    ansible_extra_vars = "\"custom_py_interpreter=/opt/pf9/cli/bin/python\""
    cmd = 'sudo {0} -a -b --pmk -v {1} -c {2} -l {3} -e {4} pmk'.format(exp_ansible_runner,
                                                                 inv_file, exp_config_file,
                                                                 log_file, ansible_extra_vars)
    # Current implementation is to have this express invocation dumps logs in 
    # a known location instead of capturing it here. Here we care only about
    # the exit code and fake progress.

    # Progress bar logic: Assume each host takes x time. Number of hosts is n
    # Total estimated time = n * x. We check for command status and refresh the
    # bar even ys with n*x/y.
    time_per_host_secs = 240
    total_nodes = len(ips)
    poll_interval_secs = 5
    with click.progressbar(length=total_nodes * time_per_host_secs, color="orange",
                           label='Preparing nodes') as bar:
        cmd_proc = subprocess.Popen(shlex.split(cmd), env=os.environ, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        elapsed = 0
        while cmd_proc.poll() is None:
            elapsed =  elapsed + poll_interval_secs
            if elapsed < (total_nodes * time_per_host_secs - poll_interval_secs):
                bar.update(poll_interval_secs)

            time.sleep(poll_interval_secs)

        # Success or failure... push the progress to 100%
        bar.update(total_nodes * time_per_host_secs)

    if cmd_proc.returncode:
        msg = "Code: {}, output log: {}".format(cmd_proc.returncode, log_file)
        raise PrepNodeFailed(msg)

    return cmd_proc.returncode, log_file


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
            node_details = 'localhost ansible_python_interpreter=/opt/pf9/cli/bin/python ansible_connection=local ansible_host=localhost\n'
        else:
            # Build the great inventory file
            for ip in ips:
                if ip == 'localhost':
                    node_info = 'localhost ansible_python_interpreter=/opt/pf9/cli/bin/python ansible_connection=local ansible_host=localhost\n'
                else:
                    if password:
                        node_info = "{0} ansible_ssh_common_args='-o StrictHostKeyChecking=no' ansible_user={1} ansible_ssh_pass={2}\n".format(
                                     ip, user, password)
                    else:
                        node_info = "{0} ansible_ssh_common_args='-o StrictHostKeyChecking=no' ansible_user={1} ansible_ssh_private_key_file={2}\n".format(
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
                ctx.params["du_username"],
                ctx.params["du_password"],
                ctx.params["du_tenant"] )

    return token, project_id

def create_cluster(ctx):
    
    # create cluster
    click.echo("Creating Cluster: {}".format(ctx.params['cluster_name']))
    cluster_status, cluster_uuid = CreateCluster(ctx).cluster_exists()

    if cluster_status == True:
        click.echo("Cluster {} already exists".format(ctx.params['cluster_name']))
    else:
        CreateCluster(ctx).create_cluster()
        cluster_uuid = CreateCluster(ctx).wait_for_cluster()

    click.echo("Cluster {} created successfully".format(ctx.params['cluster_name']))

    return cluster_uuid


def attach_cluster(cluster_name, master_ips, worker_ips, ctx):
    # Attach to cluster
    cluster_attacher = AttachCluster(ctx)

    click.echo("Attaching to cluster {}".format(cluster_name))
    status, cluster_uuid = cluster_attacher.cluster_exists(cluster_name)

    if status == False:
        click.secho("Cluster {} doesn't exist. Provide name of an existing cluster".format(
                    ctx.params['cluster_name']), fg="red")
        sys.exit(1)

    if master_ips:
        master_nodes = cluster_attacher.get_uuids(master_ips)
        click.echo("Discovering UUIDs for the cluster's master nodes")
        click.echo("Master nodes:")
        for node in master_nodes:
            click.echo("{}".format(node))

    # get uuids for worker nodes
    if worker_ips:
        worker_nodes = cluster_attacher.get_uuids(worker_ips)
        click.echo("Discovering UUIDs for the cluster's worker nodes")
        click.echo("Worker Nodes:")
        for node in worker_nodes:
            click.echo("{}".format(node))

    #TODO: Why is this even required??
    cluster_uuid = cluster_attacher.wait_for_cluster(cluster_name)

    # attach master nodes
    #TODO: Can this fail?
    #TODO: Likely needs a progress bar?
    if master_ips:
        cluster_attacher.attach_to_cluster(cluster_uuid, 'master', master_nodes)
        cluster_attacher.wait_for_n_active_masters(cluster_name, len(master_nodes))

    # attach worker nodes
    if worker_ips:
        cluster_attacher.attach_to_cluster(cluster_uuid, 'worker', worker_nodes)


def prep_node(ctx, user, password, ssh_key, ips, node_prep_only):
    only_local_node = False
    if len(ips) == 1 and ips[0] == 'localhost':
        only_local_node = True
        click.echo('Prepping the local node to be added to Platform9 Managed Kubernetes')

    inv_file = build_express_inventory_file(ctx, user, password, ssh_key, ips,
                                            only_local_node, node_prep_only)
    rcode, output_file = run_express(ctx, inv_file, ips)

    return rcode, output_file

@click.group()
def cluster():
    """Platform9 Managed Kuberenetes cluster operations"""

@cluster.command('create')
@click.argument('cluster_name')
@click.option('--masterVip', help='IP address for VIP for master nodes', default='')
@click.option('--masterVipIf', help='Interface name on which the VIP should bind to', default='')
@click.option('--metallbIpRange', help='IP range for MetalLB (<startIP>-<endIp>)', default='')
@click.option('--containersCidr', type=str, required=False, default='10.20.0.0/16', help="CIDR for container overlay")
@click.option('--servicesCidr', type=str, required=False, default='10.21.0.0/16', help="CIDR for services overlay")
@click.option('--externalDnsName', type=str, required=False, default='', help="External DNS name for master VIP")
@click.option('--privileged', type=bool, required=False, default=True, help="Enable privileged mode for Kubernetes API")
@click.option('--appCatalogEnabled', type=bool, required=False, default=True, help="Enable Helm application catalog")
@click.option('--allowWorkloadsOnMaster', type=bool, required=False, default=False, help="Taint master nodes (to enable workloads)")
@click.option("--networkPlugin", type=str, required=False, default='flannel', help="Specify non-default network plugin (default = flannel)")
@click.option('--user', '-u', help='SSH username for nodes.')
@click.option('--password', '-p', help='SSH password for nodes.')
@click.option('--ssh-key', '-s', help='SSH key for nodes.')
@click.option('--master-ip', '-m', multiple=True, help='IPs of the master nodes. Specify multiple IPs by repeating this option.', required=True)
@click.option('--worker-ip', '-w', multiple=True, help='IPs of the worker nodes. Specify multiple IPs by repeating this option.', default='')
@click.pass_context
def create(ctx, **kwargs):
    """Create a Kubernetes cluster"""

    master_ips = ctx.params['master_ip']
    ctx.params['master_ip'] = ''.join(master_ips).split(' ') if all(len(x)==1 for x in master_ips) else list(master_ips)

    all_ips = ctx.params['master_ip']

    worker_ips = ctx.params['worker_ip']
    if worker_ips:
        # Worker ips may be undefined
        ctx.params['worker_ip'] = ''.join(worker_ips).split(' ') if all(len(x)==1 for x in worker_ips) else list(worker_ips)
        all_ips = all_ips + ctx.params['worker_ip']

    try:
        check_vip_needed(ctx.params['master_ip'], ctx.params.get('mastervip', None),
                         ctx.params.get('mastervipif', None))

        ctx.params['token'], ctx.params['project_id'] = get_token_project(ctx)

        if len(all_ips) > 0:
            # Nodes are provided. So prep them.
            adj_ips = ()
            for ip in all_ips:
                if ip == "127.0.0.1" or ip == "localhost" or \
                        ip in get_local_node_addresses():
                    # Have to adjust this to localhost to ensure Ansible handles
                    # this as a local connection.
                    adj_ips = adj_ips + ("localhost",)
                else:
                    # check if ssh creds are provided.
                    validate_ssh_details(ctx.params['user'], 
                                         ctx.params['password'],
                                         ctx.params['ssh_key'])
                    adj_ips = adj_ips + (ip,)

            # Will throw in case of failed run
            rcode, out_file = prep_node(ctx, ctx.params['user'], ctx.params['password'],
                                        ctx.params['ssh_key'], adj_ips,
                                        node_prep_only=True)

        cluster_uuid = create_cluster(ctx)
        click.echo("Cluster UUID: {}".format(cluster_uuid))

        if len(all_ips) > 0:
            # To attach nodes, we have to find the node uuid from the DU based on
            # the IP address. This cannot be localhost, 127.0.0.1. We handle it by 
            # getting all the non local IPs and picking the first one.
            # Attach nodes
            master_ips = ()
            worker_ips = ()
            for ip in ctx.params['master_ip']:
                if ip == "127.0.0.1" or ip == "localhost":
                    local_ip = get_local_node_addresses()
                    master_ips = master_ips + (local_ip[0],)
                else:
                    master_ips = master_ips + (ip,)

            for ip in ctx.params['worker_ip']:
                if ip == "127.0.0.1" or ip == "localhost":
                    local_ip = get_local_node_addresses()
                    worker_ips = worker_ips + (local_ip[0],)
                else:
                    worker_ips = worker_ips + (ip,)

            attach_cluster(ctx.params['cluster_name'], master_ips, worker_ips, ctx)
    except CLIException as e:
        click.secho("Failed to create cluster {}. {}".format(
                    ctx.params['cluster_name'], e.msg), fg="red")
        sys.exit(1)

    click.secho("Successfully created cluster {} "\
                "using this node".format(ctx.params['cluster_name']),
                fg="green")


@cluster.command('bootstrap')
@click.argument('cluster_name')
@click.option('--masterVip', help='IP address for VIP for master nodes', default='')
@click.option('--masterVipIf', help='Interface name for master/worker node', default='')
@click.option('--metallbIpRange', help='IP range for MetalLB (<startIP>-<endIp>)', default='')
@click.option('--containersCidr', type=str, required=False, default='10.20.0.0/16', help="CIDR for container overlay")
@click.option('--servicesCidr', type=str, required=False, default='10.21.0.0/16', help="CIDR for services overlay")
@click.option('--externalDnsName', type=str, required=False, default='', help="External DNS name for master VIP")
@click.option('--privileged', type=bool, required=False, default=True, help="Enable privileged mode for Kubernetes API")
@click.option('--appCatalogEnabled', type=bool, required=False, default=True, help="Enable Helm application catalog")
@click.option('--allowWorkloadsOnMaster', type=bool, required=False, default=True, help="Taint master nodes (to enable workloads)")
@click.option("--networkPlugin", type=str, required=False, default='flannel', help="Specify non-default network plugin (default = flannel)")
@click.pass_context
def bootstrap(ctx, **kwargs):
    """
    Bootstrap a single node Kubernetes cluster with your current host as the Kubernetes node.
    """
    prompt_msg = "Proceed with creating a Kubernetes cluster with the current node as the Kubernetes master [y/n]?"
    localnode_confirm = click.prompt(prompt_msg, default='y')

    if localnode_confirm.lower() == 'n':
        click.secho("Quitting...", fg="red")
        sys.exit(1)

    try:
        ctx.params['token'], ctx.params['project_id'] = get_token_project(ctx)

        # This will throw when the prep node fails
        rcode, output = prep_node(ctx, None, None,
                                None, ('localhost',),
                                node_prep_only=True)

        cluster_uuid = create_cluster(ctx)
        click.echo("Cluster UUID: {}".format(cluster_uuid))

        local_ip = get_local_node_addresses()
        # To attach nodes, we have to find the node uuid from the DU based on
        # the IP address. This cannot be localhost, 127.0.0.1. We handle it by 
        # getting all the non local IPs and picking the first one
        # Attach nodes
        attach_cluster(ctx.params['cluster_name'], (local_ip[0],), None, ctx)
    except CLIException as e:
        click.secho("Encountered an error while bootstrapping the local node to a Kubernetes"\
                    " cluster. {}".format(e.msg), fg="red")
        sys.exit(1)

    click.secho("Successfully created cluster {} "\
                "using this node".format(ctx.params['cluster_name']),
                fg="green")


@cluster.command('attach-node')
@click.argument('cluster_name')
@click.option('--master-ip', '-m', multiple=True, help='IP of the node to be added as masters, Specify multiple IPs by repeating this option.')
@click.option('--worker-ip', '-w', multiple=True, help='IP of the node to be added as workers. Specify multiple IPs by repeating this option.')
@click.pass_context
def attach_node(ctx, **kwargs):
    """
    Attach provided nodes the specified cluster
    """
    if not ctx.params['master_ip'] and not ctx.params['worker_ip']:
        msg = "No nodes were specified to be attached to the cluster {}."
        click.secho(msg.format(ctx.params['cluster_name']), fg="red")
        sys.exit(1)

    ctx.params['token'], ctx.params['project_id'] = get_token_project(ctx)
    master_ips = ()
    worker_ips = ()
    for ip in ctx.params['master_ip']:
        if ip == "127.0.0.1" or ip == "localhost":
            local_ip = get_local_node_addresses()
            master_ips = master_ips + (local_ip[0],)
        else:
            master_ips = master_ips + (ip,)

    for ip in ctx.params['worker_ip']:
        if ip == "127.0.0.1" or ip == "localhost":
            local_ip = get_local_node_addresses()
            worker_ips = worker_ips + (local_ip[0],)
        else:
            worker_ips = worker_ips + (ip,)

    # There may be 0 masters, workers specified. The attach_cluster method
    # handles this situation
    try:
        attach_cluster(ctx.params['cluster_name'], master_ips, worker_ips, ctx)
    except CLIException as e:
        click.secho("Encountered an error while attaching nodes to a Kubernetes"\
                    " cluster {}. {}".format(ctx.params['cluster_name'], e.msg), fg="red")
        sys.exit(1)

    click.secho("Successfully attached nodes to a Kubernetes cluster {} "\
                "using this node".format(ctx.params['cluster_name']),
                fg="green")


@cluster.command('prep-node')
@click.option('--user', '-u', help='SSH username for nodes.')
@click.option('--password', '-p', help='SSH password for nodes.')
@click.option('--ssh-key', '-s', help='SSH key for nodes.')
@click.option('--ips', '-i', multiple=True, help='IPs of the host to be prepped. Specify multiple IPs by repeating this option.')
@click.pass_context
def prepnode(ctx, user, password, ssh_key, ips):
    """ 
    Prepare a node to be ready to be added to a Kubernetes cluster
    """
    if not ips:
        prompt_msg = "No IPs provided. Proceed with preparing the current node to be added to a Kubernetes cluster [y/n]?"

        localnode_confirm = click.prompt(prompt_msg, default = 'y')
        if localnode_confirm.lower() == 'n':
            sys.exit(1)
        else:
            ips = ("localhost",)

    # Click does some processing if the multiple value option (ips)
    # has just one value provided. Hence, need this work around.
    parse_ips = ''.join(ips).split(' ') if all(len(x)==1 for x in ips) else list(ips)
    adj_ips = ()
    try:
        for ip in parse_ips:
            if ip == "127.0.0.1" or ip == "localhost" \
                or ip in get_local_node_addresses():
                adj_ips = adj_ips + ("localhost",)
            else:
                # check if ssh creds are provided.
                try:
                    validate_ssh_details(user, password, ssh_key)
                except CLIException as e:
                    click.secho(e.msg, fg="red")
                    print_help_msg(prepnode)
                    sys.exit(1)

                adj_ips = adj_ips + (ip,)

        rcode, output_file = prep_node(ctx, user, password, ssh_key,
                                    adj_ips, node_prep_only=True)

    except CLIException as e:
        click.secho("Encountered an error while preparing the provided nodes as " \
                    "Kubernetes nodes. {}".format(e.msg), fg="red")
        sys.exit(1)

    click.secho("Preparing the provided nodes to be added to Kubernetes cluster was successful",
                fg="green")

