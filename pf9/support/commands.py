"""CLI Support Commands """
import os
import sys
import click
import requests
import urllib3
import getpass
import socket
from ..exceptions import DUCommFailure
from ..exceptions import CLIException
from ..modules.express import Get
from ..modules.util import Utils
from fabric import Connection
import ipaddress
import paramiko.ssh_exception


@click.group()
def support():
    """Platform9 Support Utilities"""


@support.group()
def bundle():
    """Manage Platform9 Support Bundles"""


@bundle.command('')
@click.option('--host', help='Host for which you want a support bundle generated')
@click.option('--silent', '-s', is_flag=True, help='Run silently, Helpful when utilized in scripts.')
@click.option('--off-line', '-o', is_flag=True, help='Direct to host request to generate a support bundle.')
@click.pass_context
def create(ctx, silent, host, off_line):
    """Request Creation of a Platform9 Support"""

    if off_line:
        if not host or host in ['localhost', '127.0.0.1']:
            use_localhost = click.prompt("Use localhost? [y/n]", default='y')
            if use_localhost.lower() == 'n':
                click.echo("Quiting...")
                sys.exit(1)
            host = "127.0.0.1"
            fqdn = socket.gethostname()
            click.echo("host_fqdn: " + fqdn)

        click.echo("Directly requesting support bundle generation from \n"
                   "host: {}".format(host))
        ssh_dir = os.path.join(os.path.expanduser("~"), '.ssh/')
        user_name = getpass.getuser()
        ssh_conn = Connection(host=host, user=user_name, port=22)
        local_bundle_exec = 'sudo python /opt/pf9/hostagent/lib/python2.7/site-packages/datagatherer/datagatherer.py'
        try:
            ssh_result = ssh_conn.run(local_bundle_exec, pty=True)
        except paramiko.ssh_exception.NoValidConnectionsError:
            click.echo("Unable to communicate with: " + host)
            sys.exit(1)
        except (paramiko.ssh_exception.SSHException, paramiko.ssh_exception.PasswordRequiredException) as err:
            # Need to loop this whole process up to 3 times.
            click.echo("SSH Credentials for {}".format(host))
            user_name = click.prompt("Username {}".format(user_name), default=user_name)
            use_ssh_key = click.prompt("Use SSH Key Auth? [y/n]", default='y')
            if use_ssh_key.lower() == 'y':
                ssh_key_file = click.prompt("SSH private key file: ", default=ssh_dir)
                ssh_auth = {"look_for_keys": "false", "key_filename": ssh_key_file}
            else:
                password = getpass.unix_getpass()
                ssh_auth = {"look_for_keys": "false", "password": password}
            # Need to loop getting the keyfile against file exist
            ssh_conn = Connection(
                host=host,
                user=user_name,
                port=22,
                connect_kwargs=ssh_auth,
            )
        local_bundle_exec = 'sudo python /opt/pf9/hostagent/lib/python2.7/site-packages/datagatherer/datagatherer.py'
        try:
            ssh_result = ssh_conn.run(local_bundle_exec, pty=True)
        except (paramiko.ssh_exception.SSHException, paramiko.ssh_exception.PasswordRequiredException) as except_err:
            click.echo("FAILED: {}".format(except_err))
            sys.exit(1)
        click.echo("Result: {}".format(ssh_result))
        # TEMP EXIT
        sys.exit(0)

    if not host:
        except_msg = "No host provided."
        # -- NOT IMPLEMENTED --
        # Need to generate a list of hosts from resmgr/local inventories
        #raise CLIException(except_msg)
        click.echo("\n" + except_msg)
        click.echo("\n\n" + click.Context(create).get_help())
        sys.exit(1)

    # \/--- From-Here ---\/
    # This all needs to go into a Module
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        token, project_id = Get(ctx).get_token_project()
    except CLIException as except_err:
        click.echo(except_err)
        sys.exit(1)
    # Building the data set
    _resmgr_endpoint = '{}/resmgr/v1/hosts/'.format(ctx.params['du_url'])
    headers = {'Content-Type': 'application/json', 'X-Auth-Token': token}
    try:
        ipaddress.ip_address(host)
    except ipaddress.AddressValueError:
        pass
        host = Utils.ip_from_dns_name(host)
        # Need to handle hostname lookup against resmgr as well
        # Need to move this into a loop to validate again and fail if resolve doesn't work
        # except_msg = "Host provided could not be resolved to an IP address"
        #    raise CLIException(except_msg)

    try:
        resmgr_get_hosts = requests.get(_resmgr_endpoint,
                                        verify=False,
                                        headers=headers)
        if resmgr_get_hosts.status_code not in (200, 201):
            except_msg = "Failed to obtain host data from Platform9 Management Plane Reservation Manger"
            raise DUCommFailure(except_msg)

        host_values = {}
        for host_data in resmgr_get_hosts.json():
            if 'responding' in host_data['info'] and host_data['info']['responding']:
                if host in host_data['extensions']['ip_address']['data']:
                    host_values['hostname'] = host_data['info']['hostname']
                    host_values['id'] = host_data['id']
                    host_values['ip_addresses'] = host_data['extensions']['ip_address']['data']
    except (DUCommFailure, CLIException) as except_err:
        click.echo(except_err)
        sys.exit(1)

    if len(host_values):
        resmgr_bundle_resp = requests.post("{}{}/support/bundle".
                                           format(_resmgr_endpoint,
                                                  host_values['id']
                                                  ), verify=False, headers=headers)
        if resmgr_bundle_resp.status_code not in (200, 201):
            except_msg = "Failure: Request to the Platform9 Management Plane for support bundle generation failed:" \
                         "host: {}\n" \
                         "hostname: {}\n" \
                         "id: {}\n" \
                         "response status_code: {}".format(
                          host, host_values['hostname'],
                          host_values['id'],
                          resmgr_bundle_resp.status_code)
            raise DUCommFailure(except_msg)
        # /\--- To-Here ---/\

        click.echo("Request to generate a support bundle succeeded:"
                   "    host: {}\n"
                   "    hostname: {}\n"
                   "    id: {}\n"
                   "    response status_code: {}".format(
                    host, host_values['hostname'],
                    host_values['id'], resmgr_bundle_resp.status_code))
        sys.exit(0)
    else:
        click.echo("Unable to find an Active node that matched host: {}".format(host))
        sys.exit(1)

    if not silent:
        click.echo("")


@bundle.command('list')
@click.pass_obj
def list_bundles(obj):
    """List all available Platform9 Support"""
    click.echo("List all support bundles") 
