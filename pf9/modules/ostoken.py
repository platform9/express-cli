#!/usr/bin/python

# Obtains a PF9-API DU auth token for a specific user/tenant. 
# Tested with python 2.7 and 3.7.0 on OSX and Ubuntu 17.10
# maintainer: tom.christopoulos@platform9.com

from ..exceptions import UserAuthFailure
import click
import json
import requests
import sys


class GetToken:

    def os_auth(self, host, username, password, tenant):
        keystone_endpoint = '%s/keystone/v3/auth/tokens?nocatalog' % host
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
        r = requests.post(keystone_endpoint, headers=headers,
                          json=body)

        if r.status_code not in (200, 201):
            click.echo("{0}: {1}".format(r.status_code, r.text))
            msg = "Failed to authenticate with {}".format(host)
            raise UserAuthFailure(msg)

        response = {
                "headers": r.headers,
                "json": r.json()
                }
        return response 

    def get_token_v3(self, host, username, password, tenant):
        os_auth_req = self.os_auth(host, username, password, tenant)
        token = os_auth_req['headers']['X-Subject-Token']
        return token

    def get_project_id(self, host, username, password, tenant):
        os_auth_req = self.os_auth(host, username, password, tenant)
        project_id = os_auth_req['json']['token']['project']['id']
        return project_id

    def get_token_project(self, host, username, password, tenant):
        os_auth_req = self.os_auth(host, username, password, tenant)
        token = os_auth_req['headers']['X-Subject-Token']
        project_id = os_auth_req['json']['token']['project']['id']
        return token, project_id


