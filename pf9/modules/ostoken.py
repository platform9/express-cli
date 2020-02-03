#!/usr/bin/python
"""
Classes for Authenticating and Interogating Platform9 Management Plane
Tested with python 2.7 and 3.7.0 on OSX and Ubuntu 16.04 and 18.04
Maintainer: tom.christopoulos@platform9.com
"""

import re
import requests
import urllib3
from ..exceptions import UserAuthFailure
from ..exceptions import DUCommFailure
from ..exceptions import CLIException
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GetToken:
    """Authenticates to Platform9 Management Plane and Returns Authentication Token and ProjectID"""
    def os_auth(self, host, username, password, tenant):
        """POST Authentication to PF9 Management Plane and return raw Headers and JSON body"""
        get_token_try = 0
        while get_token_try < 2:
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
            try:
                raw_response = requests.post(keystone_endpoint, headers=headers, json=body)
                if raw_response.status_code not in (200, 201):
                    msg = "Failed to authenticate with {}".format(host)
                    raise UserAuthFailure(msg)

                response = {
                    "headers": raw_response.headers,
                    "json": raw_response.json()}
                return response
            except (UserAuthFailure, requests.exceptions.MissingSchema) as err:
                get_token_try = get_token_try + 1
                if not host.startswith('http'):
                    host = "https://{}".format(host)
                elif host.startswith('http://'):
                    host = host.replace('http', 'https')
                else:
                    raise UserAuthFailure(str(err))

    def get_token_v3(self, host, username, password, tenant):
        """Calls os_auth and returns only the Auth Token"""
        os_auth_req = self.os_auth(host, username, password, tenant)
        token = os_auth_req['headers']['X-Subject-Token']
        return token

    def get_project_id(self, host, username, password, tenant):
        """Calls os_auth and only returns OpenStack Project_ID"""
        os_auth_req = self.os_auth(host, username, password, tenant)
        project_id = os_auth_req['json']['token']['project']['id']
        return project_id

    def get_token_project(self, host, username, password, tenant):
        """Call os_auth and returns OpenStack Project_ID and Authentication Token"""
        os_auth_req = self.os_auth(host, username, password, tenant)
        token = os_auth_req['headers']['X-Subject-Token']
        project_id = os_auth_req['json']['token']['project']['id']
        return token, project_id


class GetRegionURL():
    """GetRegionURL Returns FQDN of a public API service endpoint for a given Openstack Region"""
    def __init__(self, host, username, password, tenant, region):
        """Initialize GetRegionURL()"""
        self.host = host
        self.username = username
        self.password = password
        self.tenant = tenant
        self.region = region

    def get_token(self):
        """Calls GetToken().get_token_v3() to obtain an Auth token"""
        return GetToken().get_token_v3(
            self.host,
            self.username,
            self.password,
            self.tenant)

    def get_region_url(self):
        """GetRegionURL Returns FQDN of a public API service endpoint for an Openstack Region"""
        try:
            token = self.get_token()
            if not self.get_token:
                raise DUCommFailure("GetRegionURL: Failed to obtain token from \
                        {}".format(self.host))
            headers = {'Content-Type': 'application/json', 'X-Auth-Token': token}
            services_api = '{}/keystone/v3/services?type=regionInfo'.format(self.host)
            response_services_api = requests.get("{}".format(services_api),
                                                 verify=False,
                                                 headers=headers)
            if response_services_api.status_code not in (200, 201):
                msg = "GetRegionURL: Failed to obtain services regionInfo from {}".format(self.host)
                raise DUCommFailure(msg)
        except DUCommFailure as err:
            raise DUCommFailure(str(err))
        except Exception as err:
            raise DUCommFailure("get_region_URL: Exception: {}".format(err))

        try:
            service_id = {"json": response_services_api.json()}['json']['services'][0]['id']
            endpoints_api = "{}/keystone/v3/endpoints?service_id={}".format(self.host, service_id)
            response_endpoints_api = requests.get(endpoints_api, verify=False, headers=headers)
            if response_endpoints_api.status_code not in (200, 201):
                msg = "GetRegionURL: Failed to obtain Region EndPoints from \
                        {} for service id: {} ".format(self.host, service_id)
                raise DUCommFailure(msg)
            json_endpoints = {"json": response_endpoints_api.json()}['json']['endpoints']
            for endpoint in json_endpoints:
                if endpoint['region_id'] == self.region and endpoint['interface'] == "public":
                    return re.search("//(.*?)/", endpoint['url']).group(1)
            msg = "GetRegionURL.get_region_url: No endpoint matched for \
                    region: {}, host: {}, tenant: {}, username: {}, endpoints: {}"\
                    .format(self.region, self.host, self.tenant, self.username, json_endpoints)
            raise CLIException(str(msg))
        except DUCommFailure as err:
            raise DUCommFailure(str(err))
        except Exception as err:
            raise DUCommFailure("get_region_URL: Exception: {}".format(err))
