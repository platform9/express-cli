import subprocess
import time
import os
import json
import requests
import tarfile
import shutil
import urlparse


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
