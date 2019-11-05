#!/usr/bin/python

# Obtains a PF9-API DU auth token for a specific user/tenant. 
# Tested with python 2.7 and 3.7.0 on OSX and Ubuntu 17.10
# maintainer: tom.christopoulos@platform9.com

import json
import requests
import sys


class GetToken:

    def get_token_v3(self, host, username, password, tenant):
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
            print("{0}: {1}".format(r.status_code, r.text))
            sys.exit(1)
     
        token = r.headers['X-Subject-Token']
        return token
