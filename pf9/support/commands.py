"""CLI Support Commands """
import sys
import click
import requests
from ..exceptions import CLIException
from ..exceptions import DUCommFailure
from ..modules.express import Get
from ..modules.util import Utils
import ipaddress
@click.group()
def support():
    """Platform9 Support Utilities"""


@support.group()
def bundle():
    """Manage Platform9 Support Bundles"""


@bundle.command('')
@click.option('--host', help='Host for which you want a support bundle generated')
@click.option('--silent', '-s', is_flag=True, help='Run silently, Helpful when utilized in scripts.')
@click.pass_context
def create(ctx, silent, host):
    """Request Creation of a Platform9 Support"""

    if not host:
        except_msg = "No host provided."
        # -- NOT IMPLEMENTED --
        # Need to generate a list of hosts from resmgr/local inventories
        sys.exit(1)
        raise CLIException(except_msg)

    # \/--- From-Here ---\/
    # This all needs to go into a Module
    try:
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
        #except_msg = "Host provided could not be resolved to an IP address"
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
    if not silent:
        click.echo("")


@bundle.command('list')
@click.pass_obj
def list_bundles(obj):
    """List all available Platform9 Support"""
    click.echo("List all support bundles") 
