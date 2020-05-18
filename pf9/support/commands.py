"""CLI Support Commands """
import os
import sys
import click
import requests
import urllib3
import getpass
import shlex
import subprocess
import tarfile
import shutil
from fabric import Connection, Config
import ipaddress
import paramiko.ssh_exception
import socket
import invoke.exceptions

from pf9.exceptions import DUCommFailure, CLIException, UserAuthFailure
from pf9.modules.express import Get
from pf9.modules.util import Utils, Logger, Pf9ExpVersion

logger = Logger(os.path.join(os.path.expanduser("~"), 'pf9/log/pf9ctl.log')).get_logger(__name__)


@click.group()
def support():
    """Platform9 Support Utilities"""


@support.command('get-token')
@click.option('--silent', '-s', is_flag=True, help='Return only the token. Helpful when utilized in scripts.')
@click.pass_context
def get_token(ctx, silent):
    """Returns an Auth Token for the active config from the Platform9 Management Plane"""
    logger.info(msg=click.get_current_context().info_name)
    try:
        # Load Active Config into ctx
        Get(ctx).active_config()
        # Get Token
        token = Get(ctx).get_token()
        if token is not None:
            if silent:
                logger.info(msg="Silent Get Token Success")
                click.echo(token)
                sys.exit(0)

            logger.info(msg="Get Token Success")
            click.echo("Management Plane: {}".format(ctx.params["du_url"]))
            click.echo("Username: {}".format(ctx.params["du_username"]))
            click.echo("Region: {}".format(ctx.params["du_region"]))
            click.echo("Token: %s" % token)
        else:
            msg = "Failed to obtain Authentication from: {}".format(ctx.params["du_url"])
            raise CLIException(msg)

    except (UserAuthFailure, CLIException) as except_err:
        logger.exception(except_err)
        click.echo("Failed to obtain Authentication from: {}".format(ctx.params["du_url"]))
        sys.exit(1)
    except Exception as except_err:
        logger.exception("GENERICALLY CAUGHT EXCEPTION! {}".format(except_err))
        click.echo("Failed to obtain Authentication from: {}".format(ctx.params["du_url"]))
        sys.exit(1)


@support.command('get-region-fqdn')
@click.pass_context
def test_get_region_url(ctx):
    """Returns the FQDN of the public service api endpoint
    on the Platform9 Management Plane for the region specified in the current active config
    """
    logger.info(msg=click.get_current_context().info_name)
    try:
        region_url = Get(ctx).region_fqdn()
        if region_url is None:
            msg = "Failed to obtain region url from: {} \
                    for region: {}".format(ctx.param["du_url"], ctx.param["du_region"])
            raise CLIException(msg)
        logger.info(msg="Get Region FQDN Success")
        click.echo(region_url)
    except (UserAuthFailure, CLIException) as except_msg:
        logger.info(msg="Get Region FQDN Failed! {}".format(except_msg))
        click.echo("Get Region FQDN Failed!")
        sys.exit(1)
    except Exception as except_msg:
        logger.info(msg="GENERICALLY CAUGHT EXCEPTION! {}".format(except_msg))
        click.echo("Get Region FQDN Failed!")
        sys.exit(1)


@support.command('init')
@click.pass_obj
def init(obj):
    """Initialize Platform9 Express."""
    logger.info(msg=click.get_current_context().info_name)

    access_rights = 0o755
    pf9_dir = obj['pf9_dir']
    pf9_exp_dir = obj['pf9_exp_dir']
    target_path = pf9_dir + 'express.tar.gz'

    if not os.path.exists(pf9_exp_dir):
        get_exp_ver = Pf9ExpVersion()
        latest_express_ver_json = get_exp_ver.get_release_json()
        current_express_ver = latest_express_ver_json['version']
        url = latest_express_ver_json['url_tar']

        if not os.path.exists(pf9_dir):
            try:
                os.mkdir(pf9_dir, access_rights)
            except OSError:
                print("Creation of the directory %s failed" % pf9_dir)
            else:
                print("Successfully created the directory %s " % pf9_dir)

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(target_path, 'wb') as raw_tar:
                raw_tar.write(response.raw.read())

        tar = tarfile.open(target_path, "r:gz")
        tar.extractall(pf9_exp_dir)
        tar.close()

        with open(pf9_exp_dir + 'version', 'w') as file:
            file.write(current_express_ver + '\n')
            file.close()

        for sub_dir in next(os.walk(pf9_exp_dir))[1]:
            if 'platform9-express-' in sub_dir:
                os.rename(pf9_exp_dir + sub_dir, pf9_exp_dir + 'express')

        click.echo('Platform9 Express initialization complete')
    else:
        click.echo('Platform9 Express already initialized')


@support.command('upgrade')
@click.pass_obj
def upgrade(obj):
    """Upgrade Platform9 Express."""
    logger.info(msg=click.get_current_context().info_name)

    ver = Pf9ExpVersion()
    click.echo(ver.get_release_json())
    # TODO: upgrade fails if there is no version file.
    r = requests.get('https://api.github.com/repos/platform9/express/releases/latest')
    response = r.json()
    url = response['tarball_url']
    new_version = response['tag_name']
    access_rights = 0o755
    pf9_dir = obj['pf9_dir']
    pf9_exp_dir = obj['pf9_exp_dir']
    target_path = pf9_dir + 'express.tar.gz'

    with open(pf9_exp_dir + 'version', 'r') as v:
        current_version = v.readline()
        current_version = current_version.strip()
        v.close()

    if current_version != new_version:
        click.echo("A newer version of Platform9 Express is avialable")
        if not os.path.exists(pf9_exp_dir):
            try:
                os.mkdir(pf9_exp_dir, access_rights)
            except OSError:
                print("Creation of the directory %s failed" % pf9_exp_dir)
            else:
                print("Successfully created the directory %s " % pf9_exp_dir)

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(target_path, 'wb') as f:
                f.write(response.raw.read())

        os.rename(pf9_exp_dir + 'express', pf9_exp_dir + 'express-bak')

        tar = tarfile.open(target_path, "r:gz")
        tar.extractall(pf9_exp_dir)
        tar.close()

        for sub_dir in next(os.walk(pf9_exp_dir))[1]:
            if 'platform9-express-' in sub_dir:
                os.rename(pf9_exp_dir + sub_dir, pf9_exp_dir + 'express')

        shutil.rmtree(pf9_exp_dir + 'express-bak')

        with open(pf9_exp_dir + 'version', 'w') as file:
            file.write(new_version + '\n')
            file.close()

        click.echo('Platform9 Express upgrade complete')

    else:
        click.echo('Platform9 Express is already the latest version')


@support.group()
def bundle():
    """Manage Platform9 Support Bundles"""


@bundle.command('')
@click.option('--host', help='Host for which you want a support bundle generated')
@click.option('--silent', '-s', is_flag=True, hidden=True, help='Run silently, Helpful when utilized in scripts.')
@click.option('--mgmt-plane', '-m', is_flag=True, hidden=True, help='Direct to host request to generate a support bundle.')
@click.option('--offline', '-o', is_flag=True, hidden=True, help='Direct to host request to generate a support bundle.')
@click.pass_context
def create(ctx, silent, host, offline, mgmt_plane):
    """Request Creation of a Platform9 Support"""
    if offline and mgmt_plane:
        click.echo("--mgmt-plane and --offline are not mutually exclusive.\n"
                   "Only one may be set")
        click.echo("\n\n" + click.Context(create).get_help())

    if not mgmt_plane or offline:
        offline = True

    use_localhost = False
    bundle_exec = 'python /opt/pf9/hostagent/lib/python2.7/site-packages/datagatherer/datagatherer.py'
    if not host or host in ['localhost', '127.0.0.1']:
        use_localhost = click.prompt("Use localhost? [y/n]", default='y')
        if use_localhost.lower() == 'y':
            host = socket.getfqdn()
        else:
            if not host:
                click.echo("A host is required when not using localhost")
                sys.exit(1)
            else:
                use_localhost = False

    if offline:
        if use_localhost:
            try:
                click.echo("Generating support bundle on localhost")
                subprocess.check_output(shlex.split("sudo " + bundle_exec))
                check_bundle_out = subprocess.check_output(shlex.split("sudo ls -sh /tmp/pf9-support.tgz"))
                if check_bundle_out:
                    click.echo("Generation of support bundle complete on:\n"
                               "Host: localhost")
                    click.echo(check_bundle_out)
                    exit(0)
                else:
                    click.echo("Support Bundle Creation Failed:")
                    exit(1)
            except subprocess.CalledProcessError as except_err:
                click.echo("Support Bundle Creation Failed:")
                exit(1)

        click.echo("Requesting support bundle generation directly from host: {}".format(host))
        ssh_dir = os.path.join(os.path.expanduser("~"), '.ssh/id_rsa')
        user_name = getpass.getuser()
        ssh_conn = Connection(host=host,
                              user=user_name,
                              port=22)
        attempt = 0
        while attempt < 4:
            attempt = attempt + 1
            try:
                ssh_result_generate = ssh_conn.sudo(bundle_exec, hide='stderr')
                ssh_result_bundle = ssh_conn.sudo('ls -sh /tmp/pf9-support.tgz', hide='stderr')
                if ssh_result_generate.exited and ssh_result_bundle.exited:
                    ssh_conn.close()
                click.echo("\n\n")
                click.echo("Generation of support bundle complete on:\n Host: " + host)
                click.echo(ssh_result_bundle.stdout.strip())
                # I don't like this exit point
                # needs to return to bottom
                sys.exit(0)
            except paramiko.ssh_exception.NoValidConnectionsError:
                click.echo("Unable to communicate with: " + host)
                sys.exit(1)
            except (paramiko.ssh_exception.SSHException,
                    paramiko.ssh_exception.PasswordRequiredException,
                    invoke.exceptions.AuthFailure) as err:
                click.echo("\nAttempt [{}/3]".format(attempt))
                click.echo("SSH Credentials for {}".format(host))
                user_name = click.prompt("Username {}".format(user_name), default=user_name)
                use_ssh_key = click.prompt("Use SSH Key Auth? [y/n]", default='y')
                if use_ssh_key.lower() == 'y':
                    ssh_key_file = click.prompt("SSH private key file: ", default=ssh_dir)
                    ssh_auth = {"look_for_keys": "false", "key_filename": ssh_key_file}
                else:
                    password = getpass.unix_getpass()
                    ssh_auth = {"look_for_keys": "false", "password": password}
                click.echo("Sudo ", nl=False)
                sudo_pass = getpass.unix_getpass()
                config = Config(overrides={'sudo': {'password': sudo_pass}})
                ssh_conn = Connection(host=host,
                                      user=user_name,
                                      port=22,
                                      connect_kwargs=ssh_auth,
                                      config=config)


        sys.exit(0)

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

    if not host:
        except_msg = "No host provided."
        # -- NOT IMPLEMENTED --
        # Need to generate a list of hosts from resmgr/local inventories
        #raise CLIException(except_msg)
        click.echo("\n" + except_msg)
        click.echo("\n\n" + click.Context(create).get_help())
        sys.exit(1)

    if not silent:
        click.echo("")


@bundle.command('list')
@click.pass_obj
def list_bundles(obj):
    """List all available Platform9 Support"""
    click.echo("Not Implemented")
