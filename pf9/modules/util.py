import netifaces
import json
import re
import requests
import os
import click

class GetConfig(object):
    def __init__(self, ctx):
        self.ctx = ctx

    def GetActiveConfig(self):
        # Load Active config into ctx 
        config_file = os.path.join(self.ctx.obj['pf9_exp_conf_dir'], 'express.conf')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as data:
                    config_file_lines = data.readlines()
            except:
                click.echo('Failed reading %s: '% config_file)
            config = Utils().config_to_dict(config_file_lines)
            if config is not None:
                self.ctx.params['du_url'] = config["du_url"]
                self.ctx.params['du_username'] = config["os_username"]
                self.ctx.params['du_password'] = config["os_password"]
                self.ctx.params['du_tenant'] = config["os_tenant"]
            return self.ctx
        else:
            click.echo('No active config. Please define or activate a config.')


class Utils:
    def config_to_dict(self, config_file):
        config = {}
        for line in config_file:
            if 'config_name|' in line:
                line = line.strip()
                config.update( {'name' : line.replace('config_name|','')} )
            if 'du_url' in line:
                line = line.strip()
                config.update( {'du_url' : line.replace('du_url|','')} )
            if 'os_tenant' in line:
                line = line.strip()
                config.update( {'os_tenant' : line.replace('os_tenant|','')} )
            if 'os_username' in line:
                line = line.strip()
                config.update( {'os_username' : line.replace('os_username|','')} )
            if 'os_region' in line:
                line = line.strip()
                config.update( {'os_region' : line.replace('os_region|','')} )
            if 'os_password' in line:
                line = line.strip()
                config.update( {'os_password' : line.replace('os_password|','')} )
            if 'proxy_url' in line:
                line = line.strip()
                config.update( {'proxy_url' : line.replace('proxy_url|','')} )
            if 'dns_resolver1' in line:
                line = line.strip()
                config.update( {'dns_resolver1' : line.replace('dns_resolver1|','')} )
            if 'dns_resolver_2' in line:
                line = line.strip()
                config.update( {'dns_resolver_2' : line.replace('dns_resolver_2|','')} )
            if 'manage_hostname' in line:
                line = line.strip()
                config.update( {'manage_hostname' : line.replace('manage_hostname|','')} )
            if 'manage_resolver' in line:
                line = line.strip()
                config.update( {'manage_resolver' : line.replace('manage_resolver|','')} )
        return config


class Pf9ExpVersion:
    ''' Methods for managing PF9 Versions'''
    def get_local(self, path):
        try:
            with open(path, 'r') as value:
                version = value.readline().strip()
                return version
        except:
            return error

    def get_release_json(self, release='latest'):
        r = requests.get('https://api.github.com/repos/platform9/express/releases/' + release)
        response = r.json()
        json_return = {
                "version": response["name"],
                "url_tar": response["tarball_url"],
                "url_zip": response["zipball_url"]
                }
        return json_return
    
    def get_release(self, release ='latest'):
        r = requests.get('https://api.github.com/repos/platform9/express/releases/' + release)
        response = r.json()
        return response["name"]
    
    def get_release_list(self):
        rel_list = []
        r = requests.get('https://api.github.com/repos/platform9/express/releases')
        response = r.json()
        for rel in response:
            rel_list.append(rel['tag_name']) 
        return rel_list 

