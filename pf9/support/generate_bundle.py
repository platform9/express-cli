import os
import sys
import click
import getpass
import shlex
import subprocess
import requests
import json
from fabric import Connection, Config
import paramiko.ssh_exception
import socket
import invoke.exceptions
import time
from progress.bar import Bar
from pf9.exceptions import DUCommFailure, CLIException, UserAuthFailure
from pf9.modules.express import Get
from pf9.modules.util import Utils, Logger, Pf9ExpVersion


logger = Logger(os.path.join(os.path.expanduser("~"), 'pf9/log/pf9ctl.log')).get_logger(__name__)

class Log_Bundle:

    def __init__(self,error_msg="none"):
        self.error_msg = error_msg
#       self.host = "127.0.0.1"

    def get_uuid_from_resmgr(self,du_url,host_ip,headers):

    #Based on the host_ip this function would pull the host UUID from resmgr.

        try:
            api_endpoint = "resmgr/v1/hosts"
            pf9_response = requests.get("{}/{}".format(du_url,api_endpoint),
                                        headers=headers)
            if pf9_response.status_code != 200:
                return None

            # parse resmgr response
            json_response = json.loads(pf9_response.text)
        except Exception as except_err:
            logger.exception(except_err)
            return None

        # sequentially search resmgr response for the ip of the host, if the ip is found return host uuid
        for host in json_response:
            try:
                for iface_name, iface_ip in host['extensions']['interfaces']['data']['iface_ip'].items():
                    if iface_ip == host_ip:
                        logger.info("Node host_id: {}".format(host['id']))
                        return host['id']
            except Exception as e:
                logger.exception(e)
        return None

    def check_host_status(self,ctx,ips):
        """ Check the status of the host in Resource manager , obtaing the UUID and verify the role and responding status """
        Get(ctx).active_config()
        du_url = ctx.params['du_url']
        token = ctx.params['token']
        host_uuid = {}
        headers = {'Content-Type': 'application/json', 'X-Auth-Token': token}

        for host in ips:
            #If the host provided is local host
            # get ip of the localhost and get the hostname

            if host in ['127.0.0.1','localhost']:
                hostname=socket.gethostname()
                ip=socket.gethostbyname(hostname)
            # get host uuid from resmgr using the ip of the localhost
                host_uuid[ip]=self.get_uuid_from_resmgr(du_url,ip,headers)

                if host_uuid[ip]:
                # if a valid uuid is found , hostagent is configured and we can pull the support bundle from the host
                    resmgr_endpoint = '{}/resmgr/v1/hosts/{}'.format(ctx.params['du_url'],host_uuid[ip])

                    resmgr_get_hosts = requests.get(resmgr_endpoint,verify=False,headers=headers)
                    data = resmgr_get_hosts.json()
                    roles = (data["roles"])
                    responding = (data["info"]["responding"])

                    if responding and roles[0] == "pf9-kube":
                        pass
                    else:
                        click.secho("PF9 Installation failed for the host: {}\n".format(host))
                        time.sleep(2)
                        self.create_log_bundle(ctx,host)
                else:
                # if a valid uuid not found in resmgr from the host , hostganet is not installled and support bunndle cant be generated
                # uploading pf9ctl logs in this case
                    answer = click.prompt ("pf9ctl Prep-Node failed. Do you want to share pf9ctl logs with Platform9 (y/n)", default='y')
                    if answer == "y" or answer == "yes":
                        self.upload_pf9cli_logs (du_url,host)
                    else:
                        click.secho("pf9ctl Prep-Node failed. Contact Platform9 Support at <support@platform9.com>")



            # host provided in not localhost, get host uuid from resmgr using the ip
            else:
                host_uuid[host]=self.get_uuid_from_resmgr(du_url,host,headers)
                if host_uuid[host]:
                    resmgr_endpoint = '{}/resmgr/v1/hosts/{}'.format(ctx.params['du_url'],host_uuid[host])

                    resmgr_get_hosts = requests.get(resmgr_endpoint,verify=False,headers=headers)
                    data = resmgr_get_hosts.json()
                    roles = (data["roles"])

                    responding = (data["info"]["responding"])

                    if responding and roles[0] == "pf9-kube":
                        pass
                    else:
                        self.create_log_bundle(ctx,host)
                else:
                # if a valid uuid not found in resmgr from the host , hostganet is not installled and support bunndle cant be generated
                # uploading pf9ctl logs in this case
                    click.secho ("pf9ctl Prep-Node failed for node: {} \npf9ctl logs will be shared with Platform9 now\n".format(host), fg="red")
                    self.upload_pf9cli_logs (du_url,host)


        return None

    def upload_pf9cli_logs (self,du_url,host):
    #function for uploading pf9cli logs in case support bundle cant be generated
        log_path = str(self.error_msg)
        filename = log_path.split(":")[2].lstrip()
        #host = socket.getfqdn()    ## Made changes as we are now getting host information in parameter: host
        du_url = du_url.replace("https://","")
#        filename = path.replace("Code: 4, output log: ","")
        S3_location = "http://uploads.platform9.com.s3-us-west-1.amazonaws.com/"+str(du_url)+"/"+str(host)+"/"
        try:

            click.secho("Uploading the pf9cli log file {}\n".format(filename),fg="green")
            with Bar('Uploading', max=100) as bar:
                for i in range(100):
                    cmd = subprocess.run(["curl", "-T", filename, S3_location])
                    # self.create_os_information(S3_location)
                    bar.next()
            #time.sleep(2)
            click.secho("\nUploaded the pf9cli log files at {}".format(S3_location),
                        fg="green")
        except Exception as e:
           click.secho(e)
           click.secho("File uploading failed with error")

        return None

    def create_log_bundle(self,ctx,host='none'):

        #This function is used to generate the log bundle based on the host ip.

        Get(ctx).active_config()
        du_url = ctx.params['du_url']
        ips = ctx.params['ips']
        upload_logs =  True
        use_localhost = False
        click.secho("Generating support bundle for the host {}".format(host), fg='green')
        datagatherer_py3 = '/opt/pf9/hostagent/lib/python3.6/site-packages/datagatherer/datagatherer.py'
        datagatherer_py2 = '/opt/pf9/hostagent/lib/python2.7/site-packages/datagatherer/datagatherer.py'
        if os.path.isfile(datagatherer_py3):
            bundle_exec = 'python {}'.format(datagatherer_py3)
        elif os.path.isfile(datagatherer_py2):
            bundle_exec = 'python {}'.format(datagatherer_py2)
        else:
            # Just attempt the py3 path (and fail if it doesn't exist)
            bundle_exec = 'python {}'.format(datagatherer_py3)
        if not host or host in ['localhost', '127.0.0.1']:

                host = socket.getfqdn()
                try:
#                   Generating support bundle on localhost
                    subprocess.check_output(shlex.split("sudo " + bundle_exec))
                    check_bundle_out = subprocess.check_output(shlex.split("sudo ls -sh /tmp/pf9-support.tgz"))
                    if check_bundle_out:
                        click.echo("Generation of support bundle complete on Host:".format(host))
                        click.echo(check_bundle_out)
                        #upload_logs=click.prompt("Do you want to send the logs files to Platform9: ?(y,n)", default='y')
                        #if upload_logs.lower() == 'y' or upload_logs.lower() == 'yes':
                        click.secho("Sending the Support Bundle to Platform9",fg='green')
                        time.sleep(2)
                        self.upload_logs(du_url)
                        #else:
                        #click.secho("Logs not uploaded", fg='red')
                        # exit(0)
                    #else:
                    #    click.echo("Support Bundle Creation Failed,Sending pf9ctl logs to Platform9")
                        # upload only pf9ctl logs
                except subprocess.CalledProcessError as except_err:
                    click.echo("Support Bundle Creation Failed:")
                    # upload only pf9ctl logs

        else:
        # Generating support Bundle for remote Host
            click.secho("Generating support bundle for the host "+host+" via passwordless SSH")
            ssh_dir = os.path.join(os.path.expanduser("~"), '.ssh/id_rsa')
            user_name = getpass.getuser()
            ssh_conn = Connection(host=host,
                                      user=user_name,
                                      port=22)
            attempt = 0
            while attempt < 3:
                attempt = attempt + 1
                try:
                    ssh_result_generate = ssh_conn.sudo(bundle_exec, hide='stderr')
                    ssh_result_bundle = ssh_conn.sudo('ls -sh /tmp/pf9-support.tgz', hide='stderr')
                    if ssh_result_generate.exited and ssh_result_bundle.exited:
                        ssh_conn.close()
                    click.echo("\n\n")
                    click.echo("Generation of support bundle completed on Host: " + host +"\n")
                    click.echo(ssh_result_bundle.stdout.strip())
                    click.secho("Sending the Support Bundle to Platform9",fg='green')
                    time.sleep(2)
                    self.remote_host_upload(du_url, ssh_conn, host)
                    break


                except paramiko.ssh_exception.NoValidConnectionsError:
                        click.echo("Unable to communicate with: " + host)
                        sys.exit(1)
                #If passwordless ssh is not configured to a host , ask for username and password to generate the bundle
                except (paramiko.ssh_exception.SSHException,paramiko.ssh_exception.PasswordRequiredException,invoke.exceptions.AuthFailure) as err:
                        click.secho("Password less SSH for the"+host+" didn't work.\nNeed credentials for the host")
                        click.echo("\nAttempt [{}/3]".format(attempt))
                        click.echo("SSH Credentials for {}".format(host))
                        user_name = click.prompt("Username {}".format(user_name), default=user_name)
                        #use_ssh_key = click.prompt("Use SSH Key Auth? [y/n]", default='y')
                        #if use_ssh_key.lower() == 'y':
                        #   ssh_key_file = click.prompt("SSH private key file: ", default=ssh_dir)
                        #   ssh_auth = {"look_for_keys": "false", "key_filename": ssh_key_file}

                        password = getpass.unix_getpass()
                        ssh_auth = {"look_for_keys": "false", "password": password}
                        #click.echo("Sudo ", nl=False)
                        #sudo_pass = getpass.unix_getpass()
                        #config = Config(overrides={'sudo': {'password': sudo_pass}})
                        config = {'password': password}
                        ssh_conn = Connection(host=host,
                                              user=user_name,
                                              port=22,
                                              connect_kwargs=config)
        return None



    def upload_logs(self,du_url):
    # function to upload the logs from the localhost to S3
        host = socket.getfqdn()
        du_url = du_url.replace("https://","")
        filename = "/tmp/pf9-support.tgz"
#        filename = path.replace("Code: 4, output log: ","")
        S3_location = "http://uploads.platform9.com.s3-us-west-1.amazonaws.com/"+str(du_url)+"/"+str(host)+"/"
        try:
#            f = open(filename)
#            print ("\n")
            click.secho("Uploading the log file & system information {} to {}\n".format(filename,S3_location),fg="green")
            with Bar('Uploading', max=100) as bar:
                for i in range(100):
                    cmd = subprocess.run(["curl", "-T", filename, S3_location])
                    # self.create_os_information(S3_location)
                    bar.next()
            #time.sleep(2)
            click.secho("\nUploaded the files at {}\n".format(S3_location),
                        fg="green")
        except Exception as e:
           click.secho(e)
           click.secho("File uploading failed with error\n")

        return None



    def remote_host_upload(self,du_url,ssh_conn,host):
    # function to upload the logs from remote host to S3
        S3_location = "http://uploads.platform9.com.s3-us-west-1.amazonaws.com/"+str(du_url)+"/"+str(host)+"/"
        du_url = du_url.replace("https://","")
        filename = "/tmp/pf9-support.tgz"
        try:
            click.secho("Uploading the log file & system information {} to {}\n".format(filename,S3_location),fg="green")
           # with Bar('Uploading', max=100) as bar:
           #     for i in range(100):
            ssh_conn.sudo("curl -s -T /tmp/pf9-support.tgz http://uploads.platform9.com.s3-us-west-1.amazonaws.com/"+du_url+"/"+host+"/")
           #          bar.next()
            click.secho("\n Uploaded the files to S3\n")

        except Exception as e:
            click.secho(e)
            click.secho("File uploading failed with error\n")
        return None
