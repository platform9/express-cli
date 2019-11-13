import os
import sys
import time
import json
import click
from future.utils import iteritems 
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class ClusterUtils(object):
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
            pf9_response = requests.get("{}/{}".format(self.du_url,api_endpoint), verify=False, headers=self.headers)
            if pf9_response.status_code != 200:
                return None

            # parse resmgr response
            try:
                json_response = json.loads(pf9_response.text)
            except:
                return None

            for item in json_response:
                if item['type'] == 'local':
                    return(item['nodePoolUuid'])
        except Exception as ex:
            return None


    def cluster_exists(self):
        try:
            api_endpoint = "qbert/v3/{}/clusters".format(self.project_id)
            pf9_response = requests.get("{}/{}".format(self.du_url,api_endpoint), verify=False, headers=self.headers)
            if pf9_response.status_code != 200:
                return False, None
        except:
            return False, None

        # parse resmgr response
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
            self.write_host("Waiting for cluster to be created, status = {}".format(cluster_status))
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
        return(cluster_uuid)


    def wait_for_n_active_masters(self, master_node_num):
        TIMEOUT = 15
        POLL_INTERVAL = 30
        timeout = int(time.time()) + (60 * TIMEOUT)
        flag_found_n_masters = False
        while True:
            n = self.get_num_active_masters()
            self.write_host("waiting for {} masters to become active (n={})".format(master_node_num,n))
            if int(n) == int(master_node_num):
                flag_found_n_masters = True
                break
            elif int(time.time()) > timeout:
                break
            else:
                time.sleep(POLL_INTERVAL)

        # enforce TIMEOUT
        if not flag_found_n_masters:
            self.fail_bootstrap("TIMEOUT: waiting for {} masters to become active".format(master_node_num))


    def get_num_active_masters(self):
        num_active_masters = 0
        try:
            api_endpoint = "qbert/v3/{}/nodes".format(self.project_id)
            pf9_response = requests.get("{}/{}".format(self.du_url, api_endpoint), verify=False, headers=self.headers)
            if pf9_response.status_code != 200:
                return(num_active_masters)
        except:
            return(num_active_masters)

        # parse response
        try:
            json_response = json.loads(pf9_response.text)
        except:
            return(num_active_masters)

        for node in json_response:
            if not 'clusterName' in node:
                continue
            if node['clusterName'] == self.cluster_name:
                try:
                    node['isMaster']
                    node['api_responding']
                except:
                    continue

                if node['isMaster'] == 1 and node['api_responding'] == 1:
                    num_active_masters += 1

        return(num_active_masters)


    def get_resmgr_hostid(self, host_ip):
        try:
            api_endpoint = "resmgr/v1/hosts".format(self.project_id)
            pf9_response = requests.get("{}/{}".format(self.du_url, api_endpoint), verify=False, headers = self.headers)
            if pf9_response.status_code != 200:
                return(None)
        except:
            return(None)

        # parse resmgr response
        try:
            json_response = json.loads(pf9_response.text)
        except:
            return None

        # sequentially search results
        for host in json_response:
            if not 'extensions' in host:
                continue
            for key, value in iteritems(host['extensions']['interfaces']['data']):
                for iface_name, iface_ip in iteritems(host['extensions']['interfaces']['data']['iface_ip']):
                    if iface_ip == host_ip:
                        return(host['id'])


    def get_uuids(self, host_ips):
        # map list of IPs to list of UUIDs
        host_uuids = []
        for host_ip in host_ips:
            host_uuid = self.get_resmgr_hostid(host_ip)
            if host_uuid != None:
                host_uuids.append(host_uuid)

        return(host_uuids)


    def cluster_convergence_status(self, cluster_uuid):
        converge_status = "pending"
        try:
            api_endpoint = "qbert/v3/{}/clusters/{}".format(self.project_id, cluster_uuid)
            pf9_response = requests.get("{}/{}".format(self.du_url, api_endpoint), verify=False, headers=self.headers)
            if pf9_response.status_code != 200:
                return converge_status
        except:
            return converge_status

        # parse resmgr response
        try:
            json_response = json.loads(pf9_response.text)
        except:
            return converge_status

        if json_response['status']:
            return(json_response['status'])
        else:
            return converge_status


    def create_cluster(self):
        self.write_host("Creating Cluster : {}".format(self.cluster_name))
        nodepool_id = self.get_nodepool_id()
        if nodepool_id == None:
            self.fail_bootstrap("failed to get nodepool_id for cloud provider")
        self.write_host("nodepool_id = {}".format(nodepool_id))

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
            "tags": {},
            "runtimeConfig": "",
            "nodePoolUuid": nodepool_id,
            "masterVipIpv4": self.ctx.params['mastervip'],
            "masterVipIface": self.ctx.params['mastervipif'],
            "metallbCidr": self.ctx.params['metallbcidr'],
            "networkPlugin": self.ctx.params['networkplugin']
        }
        self.write_host("--> cluster configuration")

        # create cluster (post to qbert)
        try:
            api_endpoint = "qbert/v3/{}/clusters".format(self.project_id)
            pf9_response = requests.post("{}/{}".format(self.du_url,api_endpoint), verify=False, headers=self.headers, data=json.dumps(cluster_create_payload))
        except:
            self.fail_bootstrap("failed to create cluster")

        # parse resmgr response
        try:
            json_response = json.loads(pf9_response.text)
        except:
            self.fail_bootstrap("cluster created, but response did not include the cluster uuid")
        self.write_host("cluster created successfully, id = {}".format(json_response['uuid']))


#class CreateCluster(object):
#    def __init__(self, ctx):
#        self.ctx = ctx
#        self.project_id = ctx.params['project_id']
#        self.token = ctx.params['token']
#        self.du_url = ctx.params['du_url']
#        self.cluster_name = ctx.params['cluster_name']
#        self.headers = { 'content-type': 'application/json', 'X-Auth-Token': self.token }
#        control_plane_pause = 30
