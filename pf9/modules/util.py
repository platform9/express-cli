import os
import requests
from ..exceptions import CLIException
import socket


class Utils:
    @staticmethod
    def ip_from_dns_name(fqdn):
        return socket.gethostbyname_ex(fqdn)[2][0]


class Pf9ExpVersion:
    """ Methods for managing PF9 Versions"""
    def get_local(self, path):
        try:
            with open(path, 'r') as value:
                version = value.readline().strip()
            return version
        except Exception:
            msg = "Failed reading {}: ".format(path)
            raise CLIException(msg)

    def get_release_json(self, release='latest'):
        req = requests.get('https://api.github.com/repos/platform9/express/releases/' + release)
        response = req.json()
        json_return = {
            "version": response["name"],
            "url_tar": response["tarball_url"],
            "url_zip": response["zipball_url"]
            }
        return json_return

    def get_release(self, release='latest'):
        req = requests.get('https://api.github.com/repos/platform9/express/releases/' + release)
        response = req.json()
        return response["name"]

    def get_release_list(self):
        rel_list = []
        req = requests.get('https://api.github.com/repos/platform9/express/releases')
        response = req.json()
        for rel in response:
            rel_list.append(rel['tag_name'])
        return rel_list
