"""
Module for driving Platform9's Express project from python.
Express is a tool for leveraging Ansible to bring hosts \
        under management of a Platform9 management plane.
Express can be found @ https://github.com/platform9/express.git
"""

import os
import tempfile
from string import Template
from pf9.exceptions import CLIException
from pf9.exceptions import UserAuthFailure
from pf9.modules.ostoken import GetRegionURL, GetToken
from pf9.modules.util import Utils, Logger

logger = Logger(os.path.join(os.path.expanduser("~"), 'pf9/log/pf9ctl.log')).get_logger(__name__)


class ResMgr:
    """express.ResMgr(ctx) contains methods to interact with Platform9 Reservation Manager"""
    def __init__(self, region_url, token):
        self.region_url = region_url
        self.token = token

    def get_hosts(self):
        """express.ResMgr().get_resmgr_hosts
        Calls Platform9 Reservation Manager using active config
        retrieves all hosts associated with the region. (Responding, Not Responding, Not Authorized)
                return resmgr_hosts_json
        """
        return_msg = ("--- Not Implemented ---"
                      "Move just  call from support bundle here")
        print(return_msg)
        return return_msg
        # resmgr_bundle_resp = requests.post("{}{}/support/bundle".
        #                                   format(_resmgr_endpoint,
        #                                          host_values['id']
        #                                          ), verify=False, headers=headers)

    def request_support_bundle(self, host_id):
        """express.ResMgr().request_support_bundle(host_id)"""
        return_msg = ("--- Not Implemented ---"
                      "Move call from support bundle create"
                      "takes in ")
        print(return_msg)
        return return_msg


class Get:
    """Express.Get(ctx) contains method to "GET" data required to run express"""
    def __init__(self, ctx):
        self.ctx = ctx


    def get_token_project(self):
        """Calls ostoken.GetToken().get_token_project() using active config
                return token, project_id
        """
        try:
            self.active_config()
            token_project = GetToken().get_token_project(
                self.ctx.params["du_url"],
                self.ctx.params["du_username"],
                self.ctx.params["du_password"],
                self.ctx.params["du_tenant"])
            if not token_project:
                except_err = "Failed to obtain an Authentication Token from: {}".format(self.ctx.params["du_url"])
                raise CLIException(except_err)
            # Add token and project_id to ctx and return token_project
            self.ctx.params['token'], self.ctx.params['project_id'] = token_project
            return token_project
        except UserAuthFailure as except_msg:
            logger.exception(except_msg)
            raise
        except CLIException as except_err:
            logger.exception(except_err)
            raise except_err

    def get_token_project_user_id(self):
        """Calls ostoken.GetToken().get_token_project() using active config
                return token, project_id
        """
        try:
            self.active_config()
            token_project_user_id = GetToken().get_token_project_user_id(
                self.ctx.params["du_url"],
                self.ctx.params["du_username"],
                self.ctx.params["du_password"],
                self.ctx.params["du_tenant"])
            if not token_project_user_id:
                except_err = "Failed to obtain an Authentication Token from: {}".format(self.ctx.params["du_url"])
                raise CLIException(except_err)
            # Add token and project_id to ctx and return token_project
            self.ctx.params['token'], self.ctx.params['project_id'], self.ctx.params['user_id'] = token_project_user_id
            return token_project_user_id
        except UserAuthFailure as except_msg:
            logger.exception(except_msg)
            raise
        except CLIException as except_err:
            logger.exception(except_err)
            raise except_err

    def get_token(self):
        """Calls ostoken.GetToken.get_token_v3 using active config
                return token
        """
        try:
            self.active_config()
            token = GetToken().get_token_v3(
                self.ctx.params["du_url"],
                self.ctx.params["du_username"],
                self.ctx.params["du_password"],
                self.ctx.params["du_tenant"])
            if not token:
                except_err = "Failed to obtain an Authentication Token from: {}".format(self.ctx.params["du_url"])
                raise CLIException(except_err)
            # Add token to ctx and return token
            self.ctx.params['token'] = token
            return token
        except UserAuthFailure as except_err:
            logger.exception(except_err)
            raise
        except CLIException as except_err:
            logger.exception(except_err)
            raise except_err

    def region_fqdn(self):
        """Calls ostoken.GetRegionURL().get_region_url.
                return region_fqdn
        """

        try:
            self.active_config()
            region_url = GetRegionURL(
                self.ctx.params["du_url"],
                self.ctx.params["du_username"],
                self.ctx.params["du_password"],
                self.ctx.params["du_tenant"],
                self.ctx.params["du_region"]).get_region_url()
            if region_url is None:
                msg = "Failed to obtain region url from: {} " \
                      "for region: {}".format(self.ctx.param["du_url"], self.ctx.param["du_region"])
                raise CLIException(msg)
            return region_url
        except CLIException as except_err:
            logger.exception(except_err)
            raise

    def active_config(self):
        """Load Active config into ctx
            return
                   ctx.params['du_url']
                   ctx.params['du_username']
                   ctx.params['du_password']
                   ctx.params['du_tenant']
                   ctx.params['du_region']
            return does not need to be captured if context is available
        """
        config_file = os.path.join(self.ctx.obj['pf9_db_dir'], 'express.conf')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as data:
                    config_file_lines = data.readlines()
            except Exception as except_err:
                except_msg = "Failed reading {}: ".format(config_file)
                logger.exception(except_err, except_msg)
                raise CLIException(except_msg)
            try:
                config = self.config_to_dict(config_file_lines)
                if config is not None:
                    if "name" in config:
                        self.ctx.params['config_name'] = config["name"]
                    else:
                        self.ctx.params['config_name'] = (config["os_username"].
                                                          split('@', 1)[0]) + '-' + config["du_url"]
                    self.ctx.params['du_url'] = config["du_url"]
                    self.ctx.params['du_username'] = config["os_username"]
                    self.ctx.params['du_password'] = config["os_password"]
                    self.ctx.params['du_tenant'] = config["os_tenant"]
                    self.ctx.params['du_region'] = config["os_region"]
                    # This is needed if we want them to be loaded as python bool
                    if config.get("dev_key") == 'True':
                        self.ctx.params['dev_key'] = True
                    else:
                        self.ctx.params['dev_key'] = False
                    if config.get("disable_analytics") == 'True':
                        self.ctx.params['disable_analytics'] = True
                    else:
                        self.ctx.params['disable_analytics'] = False

                return self.ctx
            except Exception as except_err:
                except_msg = "Failed parsing active config {}: ".format(config_file)
                logger.exception(except_err, except_msg)
                raise CLIException(except_msg)
        except_msg = "No active config. Please define or activate a config."
        logger.exception(except_msg)
        raise CLIException(except_msg)

    @staticmethod
    def config_to_dict(config_file):
        """Convert Pipe separated config to Dict()
                return config
        """
        config = {}
        for line in config_file:
            if 'config_name|' in line:
                line = line.strip()
                config.update({'name': line.replace('config_name|', '')})
            if 'du_url' in line:
                line = line.strip()
                config.update({'du_url': line.replace('du_url|', '')})
            if 'os_tenant' in line:
                line = line.strip()
                config.update({'os_tenant': line.replace('os_tenant|', '')})
            if 'os_username' in line:
                line = line.strip()
                config.update({'os_username': line.replace('os_username|', '')})
            if 'os_region' in line:
                line = line.strip()
                config.update({'os_region': line.replace('os_region|', '')})
            if 'os_password' in line:
                line = line.strip()
                config.update({'os_password': line.replace('os_password|', '')})
            if 'proxy_url' in line:
                line = line.strip()
                config.update({'proxy_url': line.replace('proxy_url|', '')})
            if 'dns_resolver1' in line:
                line = line.strip()
                config.update({'dns_resolver1': line.replace('dns_resolver1|', '')})
            if 'dns_resolver_2' in line:
                line = line.strip()
                config.update({'dns_resolver_2': line.replace('dns_resolver_2|', '')})
            if 'manage_hostname' in line:
                line = line.strip()
                config.update({'manage_hostname': line.replace('manage_hostname|', '')})
            if 'manage_resolver' in line:
                line = line.strip()
                config.update({'manage_resolver': line.replace('manage_resolver|', '')})
            if 'dev_key' in line:
                line = line.strip()
                config.update({'dev_key': line.replace('dev_key|', '')})
            if 'disable_analytics' in line:
                line = line.strip()
                config.update({'disable_analytics': line.replace('disable_analytics|', '')})
        return config


class PrepExpressRun:
    """ prepnode.PrepNode(ctx, user, password, ssh_key, ips, node_prep_only) """

    def __init__(self, ctx, user, password, ssh_key, ips, node_prep_only, inv_file_template):
        self.ctx = ctx
        self.user = user
        self.password = password
        self.ssh_key = ssh_key
        self.ips = ips
        self.node_prep_only = node_prep_only
        self.inv_file_template = inv_file_template
        if self.ctx.params['floating_ip']:
            floating_ips=ctx.params['floating_ip']
            ctx.params['floating_ip'] = ''.join(floating_ips).split(' ') if all(len(x) == 1
                                                                                for x in floating_ips
                                                                                ) else list(floating_ips)
            if len(self.ctx.params['floating_ip']) == len(self.ips):
                self.ips = self.ctx.params['floating_ip']
                logger.info("Configuring node(s) via Floating IP(s): {}".format(self.ips))
            else:
                except_msg = "Number of floating IPs does not match nodes provided"
                raise CLIException(except_msg)

    def build_ansible_command(self, verbose=False):
        """Build the bash command that will be sent to pf9-express"""
        # Invoke PMK only related playbook.
        # TODO: rework to allow for PMO/PMK or deauth. In this function or another
        _inv_file = self.build_express_inventory_file()
        try:
            Get(self.ctx).get_token_project()
            du_fqdn = Get(self.ctx).region_fqdn()
            if du_fqdn is None:
                msg = "Failed to obtain region url from: {} \
                        for region: {}".format(self.ctx.param["du_url"], self.ctx.param["du_region"])
                raise CLIException(msg)
        except (UserAuthFailure, CLIException) as except_err:
            logger.exception(except_err)
            raise

        extra_args = '-e "skip_prereq=1 autoreg={} du_fqdn={} ctrl_ip={} du_username={} du_password={} ' \
                     'du_region={} du_tenant={} du_token={}"'.format(
                      "'on'",
                      du_fqdn,
                      Utils.ip_from_dns_name(du_fqdn),
                      self.ctx.params['du_username'],
                      self.ctx.params['du_password'],
                      self.ctx.params['du_region'],
                      self.ctx.params['du_tenant'],
                      self.ctx.params['token'])

        ansible_cmd = self.ctx.obj['pf9_exec_ansible-playbook']
        if verbose:
            ansible_cmd = ansible_cmd + ' -vvvv'
        cmd = '{} -i {} -l pmk {} {}' \
              .format(ansible_cmd,
                      _inv_file,
                      extra_args,
                      self.ctx.obj['pf9_k8_playbook'])
        return cmd

    def build_express_inventory_file(self):
        inv_file_path = None
        node_details = ''
        # Read in inventory template file
        with open(self.inv_file_template) as f:
            inv_tpl_contents = f.read()
        if self.node_prep_only:
            # Create a temp inventory file
            tmp_dir = tempfile.mkdtemp(prefix='pf9_')
            inv_file_path = os.path.join(tmp_dir, 'exp-inventory')
            if len(self.ips) == 1 and self.ips[0] == 'localhost':
                node_details = 'localhost ansible_python_interpreter={} ' \
                               'ansible_connection=local ansible_host=localhost\n'.format(
                                self.ctx.obj['venv_python'])
            else:
                # Build the great inventory file
                for ip in self.ips:
                    if ip == 'localhost':
                        node_info = 'localhost ansible_python_interpreter={} ' \
                                    'ansible_connection=local ansible_host=localhost\n'.format(
                                     self.ctx.obj['venv_python'])
                    else:
                        # TODO: MOVE PASSWORD TO EXTRAVARS!!!
                        if self.password:
                            node_info = "{0} ansible_ssh_common_args='-o StrictHostKeyChecking=no' " \
                                        "ansible_user={1} " \
                                        "ansible_ssh_pass={2}\n".format(
                                         ip, self.user, self.password)
                        else:
                            node_info = "{0} ansible_ssh_common_args='-o StrictHostKeyChecking=no' " \
                                        "ansible_user={1} " \
                                        "ansible_ssh_private_key_file={2}\n".format(
                                         ip, self.user, self.ssh_key)
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
