import click
import os
from prettytable import PrettyTable
import shutil
import shlex
import subprocess
import tempfile
from ..modules.ostoken import GetToken


inventory_file_template_str = '''
##
## Ansible Inventory
##
[all]
[all:vars]
ansible_user=@@ssh_user@@
ansible_ssh_pass=@@ssh_pass@@
ansible_ssh_private_key_file=~/.ssh/id_rsa

[hypervisors]

################################################################################################
## Kubernetes Groups
################################################################################################
[pmk:children]
k8s_worker

[k8s_worker]
'''

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
    run_command(cmd)

# NOTE: a utils file may be a better location for these helper methods
def build_express_inventory_file(ctx, user, password, ssh_key, ips,
                                 only_local_node=False, node_prep_only=False):
    inv_file_path = None
    if node_prep_only:
        # Create a temp inventory file
        inv_file = tempfile.NamedTemporaryFile(prefix='pf9_', dir=tempfile.gettempdir())
        inv_file_path = inv_file.name

        if only_local_node:
            inv_file.close()
            cur_dir_path = os.path.dirname(os.path.realpath(__file__))
            local_node_template = os.path.join(cur_dir_path, '..', 'templates',
                                               'pmk_localhost_inventory.tpl')
            shutil.copyfile(local_node_template, inv_file_path)
        else:
            # Build the great inventory file
            inv_file.close()
    else:
        # Build inventory file in specific dir hierarchy
        # TODO: to be implemented
        pass

    return inv_file_path

@click.group()
def cluster():
    """Platform9 Managed Kuberenetes Cluster"""

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


@cluster.command('add-node', hidden=True)
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


@cluster.command('create', hidden=True)
@click.argument('cluster')
def create(cluster):
    """Create a defined Kubernetes cluster."""
    # create a defined cluster in qbert and add defined nodes to cluster
    click.echo('WIP')


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