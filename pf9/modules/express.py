"""
Module for driving Platform9's Express project from python.
Express is a tool for leveraging Ansible to bring hosts \
        under management of a Platform9 management plane.
Express can be found @ https://github.com/platform9/express.git
"""

import os
from ..exceptions import CLIException
from .ostoken import GetRegionURL


class Get:
    """Express.Get(ctx) contains method to "GET" data required to run express"""
    def __init__(self, ctx):
        self.ctx = ctx

    def region_fqdn(self):
        """Calls ostoken.GetRegionURL().get_region_url."""
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
        except CLIException:
            raise

    def active_config(self):
        """Load Active config into ctx"""
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
        """Convert Pipe Seperated Config File to Dict()"""
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
