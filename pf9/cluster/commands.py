"""Express Cluster Commands"""
import sys
import os
from datetime import datetime
import time
import shlex
import subprocess
import click
from pf9.exceptions import CLIException
from pf9.modules.express import PrepExpressRun
from pf9.modules.util import Logger
from pf9.cluster.exceptions import PrepNodeFailed, ClusterNotAvailable, ClusterAttachFailed, ClusterCreateFailed
from pf9.cluster.helpers import validate_ssh_details, get_local_node_addresses, check_vip_needed, print_help_msg
from pf9.cluster.cluster_create import CreateCluster
from pf9.cluster.cluster_attach import AttachCluster

logger = Logger(os.path.join(os.path.expanduser("~"), 'pf9/log/pf9ctl.log')).get_logger(__name__)


def prep_node(ctx, user, password, ssh_key, ips, node_prep_only):
    # TODO: Filter all nodes against regmgr. If they have role[pf9_kube] and role_status: ok. Remove from inventory
    if len(ips) == 1 and ips[0] == 'localhost':
        logger.info('Preparing the local node to be added to Platform9 Managed Kubernetes')
        click.echo('Preparing the local node to be added to Platform9 Managed Kubernetes')
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    inv_file_template = os.path.join(cur_dir_path,
                                     'templates',
                                     'pmk_inventory.tpl')
    cmd = PrepExpressRun(ctx, user, password, ssh_key, ips, node_prep_only, inv_file_template
                         ).build_ansible_command()
    log_file = os.path.join(ctx.obj['pf9_log_dir'],
                            datetime.now().strftime('node_provision_%Y_%m_%d-%H_%M_%S.log'))
    os.environ['ANSIBLE_CONFIG'] = ctx.obj['pf9_ansible_cfg']
    # Progress bar logic: estimate total time, while cmd_proc running, poll at interval, refreshing progbar
    # TODO: if both masters and workers, Add to est_total_time to allot for masters role, before workers.
    time_per_host_secs = 200
    poll_interval_secs = 5
    est_total_time = time_per_host_secs
    with click.progressbar(length=est_total_time, color="orange",
                           label='Preparing nodes') as progbar:
        elapsed = 0
        with open(log_file, 'w') as log_file_write:
            cmd_proc = subprocess.Popen(shlex.split(cmd), env=os.environ, stdout=log_file_write,
                                        stderr=subprocess.STDOUT, encoding='utf-8')
            while cmd_proc.poll() is None:
                elapsed = elapsed + poll_interval_secs
                if elapsed < (est_total_time - poll_interval_secs):
                    progbar.update(poll_interval_secs)
                time.sleep(poll_interval_secs)
        # Success or failure... push the progress to 100%
        progbar.update(est_total_time)

        if cmd_proc.returncode:
            msg = "Code: {}, output log: {}".format(cmd_proc.returncode, log_file)
            raise PrepNodeFailed(msg)

        return cmd_proc.returncode, log_file


def create_cluster(ctx):
    # create cluster
    logger.info("Creating Cluster: {}".format(ctx.params['cluster_name']))
    click.echo("Creating Cluster: {}".format(ctx.params['cluster_name']))
    cluster_status, cluster_uuid = CreateCluster(ctx).cluster_exists()

    if cluster_status:
        logger.info("Cluster {} already exists".format(ctx.params['cluster_name']))
        click.echo("Cluster {} already exists".format(ctx.params['cluster_name']))
    else:
        CreateCluster(ctx).create_cluster()
        cluster_uuid = CreateCluster(ctx).wait_for_cluster()

    logger.info("Cluster {} created successfully".format(ctx.params['cluster_name']))
    click.echo("Cluster {} created successfully".format(ctx.params['cluster_name']))

    return cluster_uuid


def attach_cluster(cluster_name, master_ips, worker_ips, ctx):
    # Attach to cluster
    cluster_attacher = AttachCluster(ctx)

    logger.info("Attaching to cluster {}".format(cluster_name))
    click.echo("Attaching to cluster {}".format(cluster_name))
    status, cluster_uuid = CreateCluster(ctx).cluster_exists()
    if not status:
        click.secho("Cluster {} doesn't exist. Provide name of an existing cluster".format(
                    ctx.params['cluster_name']), fg="red")
        sys.exit(1)

    if master_ips:
        master_nodes = cluster_attacher.get_uuids(master_ips)
        logger.info("Discovering UUIDs for the cluster's master nodes")
        click.echo("Discovering UUIDs for the cluster's master nodes")
        logger.info("Master nodes:")
        click.echo("Master nodes:")
        for node in master_nodes:
            logger.info("{}".format(node))
            click.echo("{}".format(node))

    # get uuids for worker nodes
    if worker_ips:
        worker_nodes = cluster_attacher.get_uuids(worker_ips)
        click.echo("Discovering UUIDs for the cluster's worker nodes")
        logger.info("Discovering UUIDs for the cluster's worker nodes")
        click.echo("Worker Nodes:")
        logger.info("Worker Nodes:")
        for node in worker_nodes:
            logger.info("{}".format(node))
            click.echo("{}".format(node))

    #TODO: Why is this even required??
    cluster_uuid = CreateCluster(ctx).wait_for_cluster()

    # attach master nodes
    #TODO: Likely needs a progress bar?
    if master_ips:
        try:
            cluster_attacher.attach_to_cluster(cluster_uuid, 'master', master_nodes)
            cluster_attacher.wait_for_n_active_masters(len(master_nodes))
        except (ClusterAttachFailed, ClusterNotAvailable) as except_err:
            logger.exception(except_err)
            click.echo("Failed attaching master node(s) to cluster: {}".format(except_err))
    # attach worker nodes
    if worker_ips:
        try:
            cluster_attacher.attach_to_cluster(cluster_uuid, 'worker', worker_nodes)
        except (ClusterAttachFailed, ClusterNotAvailable) as except_err:
            logger.exception(except_err)
            click.echo("Failed attaching worker node(s) to cluster: {}".format(except_err))


@click.group()
def cluster():
    """Platform9 Managed Kubernetes cluster operations. Read more at http://pf9.io/cli_clhelp."""


@cluster.command('create')
@click.argument('cluster_name')
@click.option('--master-ip', '-m', multiple=True, required=True,
              help='IPs of the master nodes. Specify multiple IPs by repeating this option.')
@click.option('--worker-ip', '-w', multiple=True, default='',
              help='IPs of the worker nodes. Specify multiple IPs by repeating this option.')
@click.option('--user', '-u', help='SSH username for nodes.')
@click.option('--password', '-p', help='SSH password for nodes.')
@click.option('--ssh-key', '-s', help='SSH key for nodes.')
@click.option('--masterVip', default='',
              help='IP address for VIP for master nodes. Read more at http://pf9.io/pmk_vip.')
@click.option('--masterVipIf', default='',
              help='Interface name on which the VIP should bind to. Read more at http://pf9.io/pmk_vip.')
@click.option('--metallbIpRange', default='',
              help='IP range for MetalLB (<startIP>-<endIp>). Read more at http://pf9.io/pmk_metallb.')
@click.option('--containersCidr', type=str, required=False, default='10.20.0.0/16',
              help="CIDR for container overlay")
@click.option('--servicesCidr', type=str, required=False, default='10.21.0.0/16',
              help="CIDR for services overlay")
@click.option('--externalDnsName', type=str, required=False, default='',
              help="External DNS name for master VIP")
@click.option('--privileged', type=bool, required=False, default=True,
              help="Enable privileged mode for Kubernetes API")
@click.option('--appCatalogEnabled', type=bool, required=False, default=True,
              help="Enable Helm application catalog")
@click.option('--allowWorkloadsOnMaster', type=bool, required=False, default=False,
              help="Taint master nodes (to enable workloads)")
@click.option("--networkPlugin", type=str, required=False, default='flannel',
              help="Specify network plugin (Possible values: flannel or calico, Default: flannel)")
@click.pass_context
def create(ctx, **kwargs):
    """Create a Kubernetes cluster. Read more at http://pf9.io/cli_clcreate."""
    logger.info(msg=click.get_current_context().info_name)

    master_ips = ctx.params['master_ip']
    ctx.params['master_ip'] = ''.join(master_ips).split(' ') if all(len(x) == 1
                                                                    for x in master_ips
                                                                    ) else list(master_ips)

    all_ips = ctx.params['master_ip']

    worker_ips = ctx.params['worker_ip']
    if worker_ips:
        # Worker ips may be undefined
        ctx.params['worker_ip'] = ''.join(worker_ips).split(' ') if all(len(x) == 1
                                                                        for x in worker_ips
                                                                        ) else list(worker_ips)
        all_ips = all_ips + ctx.params['worker_ip']

    try:
        check_vip_needed(ctx.params['master_ip'], ctx.params.get('mastervip', None),
                         ctx.params.get('mastervipif', None))

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
            prep_node(ctx, ctx.params['user'], ctx.params['password'],
                      ctx.params['ssh_key'], adj_ips, node_prep_only=True)

        cluster_uuid = create_cluster(ctx)
        logger.info("Cluster UUID: {}".format(cluster_uuid))
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
        logger.exception("Cluster Create Failed")
        click.secho("Failed to create cluster {}. {}".format(
                    ctx.params['cluster_name'], e.msg), fg="red")
        sys.exit(1)

    click.secho("Successfully created cluster {} "\
                "using this node".format(ctx.params['cluster_name']),
                fg="green")


@cluster.command('bootstrap')
@click.argument('cluster_name')
@click.option('--masterVip', default='',
              help='IP address for VIP for master nodes. Read more at http://pf9.io/pmk_vip.')
@click.option('--masterVipIf', default='',
              help='Interface name for master/worker node. Read more at http://pf9.io/pmk_vip.')
@click.option('--metallbIpRange', default='',
              help='IP range for MetalLB (<startIP>-<endIp>). Read more at http://pf9.io/pmk_metallb.')
@click.option('--containersCidr', type=str, required=False, default='10.20.0.0/16',
              help="CIDR for container overlay")
@click.option('--servicesCidr', type=str, required=False, default='10.21.0.0/16',
              help="CIDR for services overlay")
@click.option('--externalDnsName', type=str, required=False, default='',
              help="External DNS name for master VIP")
@click.option('--privileged', type=bool, required=False, default=True,
              help="Enable privileged mode for Kubernetes API")
@click.option('--appCatalogEnabled', type=bool, required=False, default=True,
              help="Enable Helm application catalog")
@click.option('--allowWorkloadsOnMaster', type=bool, required=False, default=True,
              help="Taint master nodes (to enable workloads)")
@click.option("--networkPlugin", type=str, required=False, default='flannel',
              help="Specify network plugin (Possible values: flannel or calico, Default: flannel)")
@click.pass_context
def bootstrap(ctx, **kwargs):
    """
    Bootstrap a single node Kubernetes cluster with your current host as the Kubernetes node.
    Read more at http://pf9.io/cli_clbootstrap.
    """
    logger.info(msg=click.get_current_context().info_name)
    prompt_msg = "Proceed with creating a Kubernetes cluster with the current node as the Kubernetes master [y/n]?"
    localnode_confirm = click.prompt(prompt_msg, default='y')

    if localnode_confirm.lower() == 'n':
        click.secho("Quitting...", fg="red")
        sys.exit(1)

    try:

        # This will throw when the prep node fails
        prep_node(ctx, None, None, None, ('localhost',), node_prep_only=True)

        cluster_uuid = create_cluster(ctx)
        logger.info("Cluster UUID: {}".format(cluster_uuid))
        click.echo("Cluster UUID: {}".format(cluster_uuid))

        local_ip = get_local_node_addresses()
        # To attach nodes, we have to find the node uuid from the DU based on
        # the IP address. This cannot be localhost, 127.0.0.1. We handle it by 
        # getting all the non local IPs and picking the first one
        # Attach nodes
        attach_cluster(ctx.params['cluster_name'], (local_ip[0],), None, ctx)
    except CLIException as e:
        logger.exception("Bootstrap Failed")
        click.secho("Encountered an error while bootstrapping the local node to a Kubernetes"\
                    " cluster. {}".format(e.msg), fg="red")
        sys.exit(1)

    click.secho("Successfully created cluster {} "\
                "using this node".format(ctx.params['cluster_name']),
                fg="green")


@cluster.command('attach-node')
@click.argument('cluster_name')
@click.option('--master-ip', '-m', multiple=True,
              help='IP of the node to be added as masters, Specify multiple IPs by repeating this option.')
@click.option('--worker-ip', '-w', multiple=True,
              help='IP of the node to be added as workers. Specify multiple IPs by repeating this option.')
@click.pass_context
def attach_node(ctx, **kwargs):
    """
    Attach provided nodes the specified cluster. Read more at http://pf9.io/cli_clattach.
    """
    logger.info(msg=click.get_current_context().info_name)
    if not ctx.params['master_ip'] and not ctx.params['worker_ip']:
        msg = "No nodes were specified to be attached to the cluster {}."
        click.secho(msg.format(ctx.params['cluster_name']), fg="red")
        sys.exit(1)

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
        logger.exception("Cluster Attach Failed")
        click.secho("Encountered an error while attaching nodes to a Kubernetes"\
                    " cluster {}. {}".format(ctx.params['cluster_name'], e.msg), fg="red")
        sys.exit(1)

    click.secho("Successfully attached nodes to a Kubernetes cluster {} "\
                "using this node".format(ctx.params['cluster_name']),
                fg="green")


@cluster.command('prep-node')
@click.option('--user', '-u',
              help='SSH username for nodes.')
@click.option('--password', '-p',
              help='SSH password for nodes.')
@click.option('--ssh-key', '-s',
              help='SSH key for nodes.')
@click.option('--ips', '-i', multiple=True,
              help='IPs of the host to be prepared. Specify multiple IPs by repeating this option.')
@click.pass_context
def prepnode(ctx, user, password, ssh_key, ips):
    """ 
    Prepare a node to be ready to be added to a Kubernetes cluster. Read more at http://pf9.io/cli_clprep.
    """
    logger.info(msg=click.get_current_context().info_name)
    if not ips:
        prompt_msg = "No IPs provided. " \
                     "Proceed with preparing the current node to be added to a Kubernetes cluster [y/n]?"
        localnode_confirm = click.prompt(prompt_msg, default='y')
        if localnode_confirm.lower() == 'n':
            sys.exit(1)
        else:
            ips = ("localhost",)

    # Click does some processing if the multiple value option (ips)
    # has just one value provided. Hence, need this work around.
    parse_ips = ''.join(ips).split(' ') if all(len(x) == 1 for x in ips) else list(ips)
    adj_ips = ()
    try:
        for ip in parse_ips:
            if ip == "127.0.0.1" or ip == "localhost" or ip in get_local_node_addresses():
                adj_ips = adj_ips + ("localhost",)
            else:
                # check if ssh creds are provided.
                try:
                    validate_ssh_details(user, password, ssh_key)
                except CLIException as e:
                    logger.exception("SSH Validation Failed")
                    click.secho(e.msg, fg="red")
                    print_help_msg(prepnode)
                    sys.exit(1)

                adj_ips = adj_ips + (ip,)

        prep_node(ctx, user, password, ssh_key, adj_ips, node_prep_only=True)

    except CLIException as e:
        logger.exception("Encountered an error while preparing the provided nodes as Kubernetes nodes.")
        click.secho("Encountered an error while preparing the provided nodes as "
                    "Kubernetes nodes. {}".format(e.msg), fg="red")
        sys.exit(1)

    click.secho("Preparing the provided nodes to be added to Kubernetes cluster was successful",
                fg="green")
