import subprocess
import time
import os
import json
import requests
import tarfile
import shutil
import urlparse

class Utils:
    def config_to_json(self, config_file):
        config = {}
        try:
            with open(config_file, 'r') as data:
                lines = data.readlines()
            for line in lines:
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
            return config
        except:
            return error 

class Pf9ExpVersion:
    ''' Methods for managing PF9 Versions'''
    def get_local(self, path):
        try:
            with open(path, 'r') as value:
                version = value.readline().strip()
                return version
        except: 
            return error

    def get_latest_json(self):
        r = requests.get('https://api.github.com/repos/platform9/express/releases/latest')
        response = r.json()
        json_return = {
                "version": response["name"],
                "url_tar": response["tarball_url"],
                "url_zip": response["zipball_url"]
                }
        return json.dumps(json_return)

    def get_latest(self):
        r = requests.get('https://api.github.com/repos/platform9/express/releases/latest')
        response = r.json()
        return response["name"]

def do_request(action, du_url, relative_url, headers='', body=''):
    url = du_url + relative_url
    if action == 'get':
        response = requests.get(url, headers=headers)
    elif action == 'post':
        response = requests.post(url, headers=headers, json=body)

    return response


def get_os_token_v3(du_url, username, password, tenant):
    headers = {"Content-Type": "application/json"}
    body = {
        "auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "name": username,
                        "domain": {"id": "default"},
                        "password": password
                    }
                }
            },
            "scope": {
                "project": {
                    "name": tenant,
                    "domain": {"id": "default"}
                }
            }
        }
    }

    response = do_request('post', du_url,
    "/keystone/v3/auth/tokens",
    headers, body)
