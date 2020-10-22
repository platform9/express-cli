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
from pf9.exceptions import DUCommFailure, CLIException, UserAuthFailure
from pf9.modules.express import Get
from pf9.modules.util import Utils, Logger, Pf9ExpVersion

class Log_Bundle:

    def __init__(self,error_msg="none"):
        self.error_msg = error_msg

    def get_uuid_from_resmgr(self, du_url, host_ip, headers):
        #Based on the host_ip this function would pull the host UUID from resmgr.
        try:
            api_endpoint = "resmgr/v1/hosts"
            pf9_response = requests.get("{}/{}".format(du_url, api_endpoint),
                                        headers=headers)
            if pf9_response.status_code != 200:
                return None
            # parse resmgr response
            json_response = json.loads(pf9_response.text)
             # sequentially search resmgr response for the ip of the host, if the ip is found return host uuid
            for host in json_response:
                try:
                    for iface_name, iface_ip in host['extensions']['interfaces']['data']['iface_ip'].items():
                        if iface_ip == host_ip:
                            return host['id']
                except Exception:
                    # For future logging
                    # Currently this try/except block is to ensure that we itterate through entire list of host
                    pass

        except Exception:
            return None
            
        return None

    def check_host_status(self, ctx, ips, user, password):
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
                host_uuid[ip]=self.get_uuid_from_resmgr(du_url, ip, headers)

                if host_uuid[ip]:
                # if a valid uuid is found , hostagent is configured and we can pull the support bundle from the host
                    resmgr_endpoint = '{}/resmgr/v1/hosts/{}'.format(ctx.params['du_url'],host_uuid[ip])
                    resmgr_get_hosts = requests.get(resmgr_endpoint, headers=headers)
                    data = resmgr_get_hosts.json()
                    roles = (data["roles"])
                    if len(roles) >= 1 :
                        if roles[0] == "pf9-kube" and data["info"]["responding"] == "true":  # Responding key will only be there is pf9-kube is installed else there will not be any responding key in response
                            pass
                        else:
                            self.create_log_bundle(ctx, user, password, host)
                    else:
                        self.create_log_bundle(ctx, user, password, host)
                else:
                    self.upload_pf9cli_logs (du_url, host)

            # host provided in not localhost, get host uuid from resmgr using the ip
            else:
                host_uuid[host]=self.get_uuid_from_resmgr(du_url, host, headers)
                if host_uuid[host]:
                    resmgr_endpoint = '{}/resmgr/v1/hosts/{}'.format(ctx.params['du_url'],host_uuid[host])
                    resmgr_get_hosts = requests.get(resmgr_endpoint, headers=headers)
                    data = resmgr_get_hosts.json()
                    roles = (data["roles"])
                    if len(roles) >= 1:
                        if roles[0] == "pf9-kube" and data["info"]["responding"] == "true": # Responding key will only be there is pf9-kube is installed else there will not be any responding key in response
                            pass
                        else:
                            self.create_log_bundle(ctx, user, password, host)
                    else:
                        self.create_log_bundle(ctx, user, password, host)
                else:
                # if a valid uuid not found in resmgr from the host , hostagent is not installed and support bundle cannot be generated
                # uploading pf9ctl logs in this case
                    self.upload_pf9cli_logs (du_url, host)

        return None

    def upload_pf9cli_logs (self, du_url, host):
        #function for uploading pf9cli logs in case support bundle cant be generated
        log_path = str(self.error_msg)
        filename = log_path.split(":")[2].lstrip()
        cli_logs="/root/pf9/log/pf9ctl.log"
        du_url = du_url.replace("https://","")
        header = 'x-amz-acl:bucket-owner-full-control'
        S3_location = "https://s3-us-west-2.amazonaws.com/loguploads.platform9.com/"+str(du_url)+"/"+str(host)+"/"
        cmd = subprocess.run(["curl", "-T", filename, "-H", header, S3_location])
        cmd = subprocess.run(["curl", "-T", cli_logs, "-H", header, S3_location])
        return None

    def create_log_bundle(self, ctx, user, password, host='none'):
        #This function is used to generate the log bundle based on the host ip.
        Get(ctx).active_config()
        du_url = ctx.params['du_url']
        upload_logs =  True
        use_localhost = False
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
                ###Generating support bundle on localhost
                subprocess.check_output(shlex.split("sudo " + bundle_exec))
                check_bundle_out = subprocess.check_output(shlex.split("sudo ls -sh /tmp/pf9-support.tgz"))
                if check_bundle_out:
                    time.sleep(2)
                    self.upload_logs(du_url)
                    self.upload_pf9cli_logs(du_url, host)

        else:
            # Generating support Bundle for remote Host
            ssh_dir = os.path.join(os.path.expanduser("~"), '.ssh/id_rsa')
            user_name = getpass.getuser()
            ssh_conn = Connection(host=host,
                                      user=user_name,
                                      port=22)
            try:
                ssh_result_generate = ssh_conn.sudo(bundle_exec, hide='stderr')
                ssh_result_bundle = ssh_conn.sudo('ls -sh /tmp/pf9-support.tgz > /dev/null 2>&1', hide='stderr')
                if ssh_result_generate.exited and ssh_result_bundle.exited:
                    ssh_conn.close()
                time.sleep(2)
                self.remote_host_upload(du_url, ssh_conn, host)
                self.upload_pf9cli_logs(du_url, host)

            except paramiko.ssh_exception.NoValidConnectionsError:
                    self.upload_pf9cli_logs(du_url, host)
                    sys.exit(1)
                #If passwordless ssh is not configured to a host , use the username and password provided in the prep node command to generate the log bundle
            except (paramiko.ssh_exception.SSHException,paramiko.ssh_exception.PasswordRequiredException,invoke.exceptions.AuthFailure) as err:
                    user_name = user
                    password = password
                    ssh_auth = {"look_for_keys": "false", "password": password}
                    config = {'password': password}
                    try:
                        ssh_conn = Connection(host=host,
                                              user=user_name,
                                              port=22,
                                              connect_kwargs=config)
                        ssh_result_generate = ssh_conn.sudo(bundle_exec, hide='stderr')
                        ssh_result_bundle = ssh_conn.sudo('ls -sh /tmp/pf9-support.tgz > /dev/null 2>&1', hide='stderr')
                        if ssh_result_generate.exited and ssh_result_bundle.exited:
                           ssh_conn.close()
                        time.sleep(2)
                        self.remote_host_upload(du_url, ssh_conn, host)
                        self.upload_pf9cli_logs(du_url, host)
                    except (paramiko.ssh_exception.SSHException,paramiko.ssh_exception.PasswordRequiredException,invoke.exceptions.AuthFailure) as err:
                        self.upload_pf9cli_logs(du_url, host)

        return None


    def upload_logs(self, du_url):
        #function to upload the logs from the localhost to S3
        host = socket.getfqdn()
        du_url = du_url.replace("https://","")
        filename = "/tmp/pf9-support.tgz"
        header = 'x-amz-acl:bucket-owner-full-control'
        S3_location = "https://s3-us-west-2.amazonaws.com/loguploads.platform9.com/"+str(du_url)+"/"+str(host)+"/"
        cmd = subprocess.run(["curl", "-T", filename, "-H", header, S3_location])
        return None


    def remote_host_upload(self, du_url, ssh_conn, host):
        # function to upload the logs from remote host to S3
        du_url = du_url.replace("https://","")
        S3_location = "https://s3-us-west-2.amazonaws.com/loguploads.platform9.com/"+str(du_url)+"/"+str(host)+"/"
        ssh_conn.sudo("curl -s -T /tmp/pf9-support.tgz -H 'x-amz-acl:bucket-owner-full-control' https://s3-us-west-2.amazonaws.com/loguploads.platform9.com/"+du_url+"/"+host+"/")
        return None
        
