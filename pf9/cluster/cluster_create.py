import os
import sys
import time
import requests
import json
import click
from ..exceptions import ClusterCreateFailed

class CreateCluster(object):
    def __init__(self, ctx):
        self.ctx = ctx
        self.project_id = ctx.params['project_id']
        self.token = ctx.params['token']
        self.du_url = ctx.params['du_url']
        self.cluster_name = ctx.params['cluster_name']
        self.headers = { 'content-type': 'application/json', 'X-Auth-Token': self.token }
        control_plane_pause = 30


    def fail_bootstrap(self, m):
        if m != None:
            click.echo("ERROR: {}\n".format(m))
        sys.exit(1)


    def write_host(self, m):
        if m != None:
            click.echo("{}".format(m))


    def get_nodepool_id(self):
        try:
            api_endpoint = "qbert/v3/{}/cloudProviders".format(self.project_id)
            pf9_response = requests.get("{}/{}".format(self.du_url,api_endpoint), headers=self.headers)
            if pf9_response.status_code != 200:
                return None

            # parse response
            try:
                json_response = json.loads(pf9_response.text)
            except:
                return None

            for item in json_response:
                if item['type'] == 'local':
                    return(item['nodePoolUuid'])
        except Exception as ex:
            return None


    def create_cluster(self):
        nodepool_id = self.get_nodepool_id()
        if nodepool_id == None:
            self.fail_bootstrap("failed to get nodepool_id for cloud provider")
        self.write_host("Using nodepool id: {}".format(nodepool_id))

        # configure cluster
        cluster_create_payload = {
            "name": self.ctx.params['cluster_name'],
            "containersCidr": self.ctx.params['containerscidr'],
            "servicesCidr": self.ctx.params['servicescidr'],
            "externalDnsName": self.ctx.params['externaldnsname'],
            "privileged": self.ctx.params['privileged'],
            "appCatalogEnabled": self.ctx.params['appcatalogenabled'],
            "allowWorkloadsOnMaster": self.ctx.params['allowworkloadsonmaster'],
            "masterless": False,
            "tags": {"pf9-system:monitoring": "true"}, # opt-out monitoring
            "runtimeConfig": "",
            "nodePoolUuid": nodepool_id,
            "masterVipIpv4": self.ctx.params['mastervip'],
            "masterVipIface": self.ctx.params['mastervipif'],
            "enableMetallb": True if self.ctx.params['metallbiprange'] else False,
            "metallbCidr": self.ctx.params['metallbiprange'],
            "networkPlugin": self.ctx.params['networkplugin']
        }

        # create cluster (post to qbert)
        try:
            api_endpoint = "qbert/v3/{}/clusters".format(self.project_id)
            pf9_response = requests.post("{}/{}".format(self.du_url,api_endpoint), headers=self.headers, data=json.dumps(cluster_create_payload))
        except Exception as e:
            msg = "Failed to create cluster: {}".format(e)
            self.fail_bootstrap(msg)
            raise ClusterCreateFailed(msg)

        # parse resmgr response
        try:
            json_response = json.loads(pf9_response.text)
        except:
            msg = "Cluster created, but response did not include the cluster uuid"
            self.fail_bootstrap(msg)
            raise ClusterCreateFailed(msg)

        return json_response['uuid']


    def cluster_exists(self):
        try:
            api_endpoint = "qbert/v3/{}/clusters".format(self.project_id)
            pf9_response = requests.get("{}/{}".format(self.du_url,api_endpoint), headers=self.headers)
            if pf9_response.status_code != 200:
                return False, None
        except:
            return False, None

        # parse response
        try:
            json_response = json.loads(pf9_response.text)
        except:
            return False, None

        for item in json_response:
            if item['name'] == self.cluster_name:
                return(True, item['uuid'])

        # final return
        return False, None


    def wait_for_cluster(self):
        TIMEOUT = 5
        POLL_INTERVAL = 2

        # timeout loop
        timeout = int(time.time()) + (60 * TIMEOUT)
        flag_cluster_exists = False
        while True:
            cluster_status, cluster_uuid = self.cluster_exists()
            self.write_host("Waiting for cluster create to complete, status = {}".format(cluster_status))
            if cluster_status == True:
                flag_cluster_exists = True
                break
            elif int(time.time()) > timeout:
                break
            else:
                time.sleep(POLL_INTERVAL)

        # enforce TIMEOUT
        if not flag_cluster_exists:
            self.fail_bootstrap("TIMEOUT: waiting for cluster to be created (qbert)")

        # return cluster uuid
        return cluster_uuid

