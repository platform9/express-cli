#!/usr/bin/python

# Obtains a PF9-API DU auth token for a specific user/tenant. 
# Tested with python 2.7 and 3.7.0 on OSX and Ubuntu 17.10
# maintainer: tom.christopoulos@platform9.com

import json
import sys

if sys.version_info.major == 2:
    import httplib
    import urlparse
elif sys.version_info.major == 3:
    from http import client as httplib
    from urllib import parse as urlparse


class GetToken:
    def do_request(self, action, host, relative_url, headers, body):
        conn = httplib.HTTPSConnection(host)
        body_json = json.JSONEncoder().encode(body)
        conn.request(action, relative_url, body_json, headers)
        response = conn.getresponse()
        return conn, response
    
    def get_token_v3(self, host, username, password, tenant):
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
        conn, response = self.do_request("POST", host,
                                    "/keystone/v3/auth/tokens?nocatalog",
                                    headers, body)
     
        if response.status not in (200, 201):
            print("{0}: {1}".format(response.status, response.reason))
            exit(1)
     
        token = response.getheader('X-Subject-Token')
        conn.close()
        return token
