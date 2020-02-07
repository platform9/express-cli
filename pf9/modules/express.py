"""
Module for driving Platform9's Express project from python.
Express is a tool for leveraging Ansible to bring hosts \
        under management of a Platform9 management plane.
Express can be found @ https://github.com/platform9/express.git
"""

import os
from ..exceptions import CLIException
from ..exceptions import UserAuthFailure
#from .ostoken import GetRegionURL
from .ostoken import GetToken


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

    def request_support_bundle(self,host_id):
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
            return token_project
        except UserAuthFailure:
            raise
        except CLIException as except_err:
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
            return token
        except UserAuthFailure:
            raise
        except CLIException as except_err:
            raise except_err

#   def region_fqdn(self):
#       """Calls ostoken.GetRegionURL().get_region_url.
#               return region_fqdn
#       """

#       try:
#           self.active_config()
#           region_url = GetRegionURL(
#               self.ctx.params["du_url"],
#               self.ctx.params["du_username"],
#               self.ctx.params["du_password"],
#               self.ctx.params["du_tenant"],
#               self.ctx.params["du_region"]).get_region_url()
#           if region_url is None:
#               msg = "Failed to obtain region url from: {} " \
#                     "for region: {}".format(self.ctx.param["du_url"], self.ctx.param["du_region"])
#               raise CLIException(msg)
#           return region_url
#       except CLIException:
#           raise

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
        config_file = os.path.join(self.ctx.obj['pf9_exp_conf_dir'], 'express.conf')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as data:
                    config_file_lines = data.readlines()
            except Exception:
                msg = "Failed reading {}: ".format(config_file)
                raise CLIException(msg)

            config = self.config_to_dict(config_file_lines)
            if config is not None:
                self.ctx.params['du_url'] = config["du_url"]
                self.ctx.params['du_username'] = config["os_username"]
                self.ctx.params['du_password'] = config["os_password"]
                self.ctx.params['du_tenant'] = config["os_tenant"]
                self.ctx.params['du_region'] = config["os_region"]
            return self.ctx
        msg = "No active config. Please define or activate a config."
        raise CLIException(msg)

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
        return config
