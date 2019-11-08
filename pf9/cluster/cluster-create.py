import os
import sys
import time
import requests
import shutil
import argparse
import json
import signal
import ConfigParser
from pprint import pprint

# global variables
control_plane_pause = 30


def _parse_args():
    ap = argparse.ArgumentParser(sys.argv[0],formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('du_url', help='du_url')
    ap.add_argument('du_username', help='du_username')
    ap.add_argument('du_password', help='du_password')
    ap.add_argument('du_tenant', help='du_tenant')
    ap.add_argument('cluster_name', help='cluster name')
    ap.add_argument('masterVip', help='IP address for VIP for master nodes')
    ap.add_argument('masterVipIf', help='Interface name for master/worker node')
    ap.add_argument('metallbCidr', help='IP range for MetalLB (<startIP>-<endIp>')
    ap.add_argument("--containersCidr", "-c", type=str, required=False, default='10.20.0.0/16', help="CIDR for container overlay")
    ap.add_argument("--servicesCidr", "-s", type=str, required=False, default='10.21.0.0/16', help="CIDR for services overlay")
    ap.add_argument("--externalDnsName", "-e", type=str, required=False, default='', help="External DNS name for master VIP")
    ap.add_argument("--privileged", "-p", type=bool, required=False, default=True, help="Enable privileged mode for Kubernetes API")
    ap.add_argument("--appCatalogEnabled", "-a", type=bool, required=False, default=True, help="Enable Helm application catalog")
    ap.add_argument("--allowWorkloadsOnMaster", "-t", type=bool, required=False, default=False, help="Taint master nodes (to enable workloads)")
    ap.add_argument("--networkPlugin", "-o", type=str, required=False, default='flannel', help="SPecify non-defaault network plugin (default = flannel)")
    ap.add_argument("--verbose", "-v", help="increase verbosity")
    return ap.parse_args()


def fail_bootstrap(m):
    if m != None:
        sys.stdout.write("ERROR: {}\n".format(m))
    sys.exit(1)


def write_host(m):
    if m != None:
        sys.stdout.write("{}\n".format(m))
        sys.stdout.flush()


def sigint_handler(signum, frame):
    None


def login(du_host, username, password, project_name):
    url = "{}/keystone/v3/auth/tokens?nocatalog".format(du_host)
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
                    "name": project_name,
                    "domain": {"id": "default"}
                }
            }
        }
    }
    try:
        resp = requests.post(url, data=json.dumps(body), headers={'content-type': 'application/json'}, verify=False)
        json_response = json.loads(resp.text)
    except:
        fail_bootstrap("failed to parse json result")
    return json_response['token']['project']['id'], resp.headers['X-Subject-Token']


def login_du(du_url, du_username, du_password, du_tenant):
    write_host("Getting token from DU")
    write_host("--> DU: {}".format(du_url))
    write_host("--> Username: {}".format(du_username))
    write_host("--> Tenant: {}".format(du_tenant))
    try:
        project_id, token = login(du_url, du_username, du_password, du_tenant)
        write_host("--> project_id = {}".format(project_id))
    except:
        fail_bootstrap("failed to get token")

    return(project_id, token)


def get_nodepool_id():
    try:
        api_endpoint = "qbert/v3/{}/cloudProviders".format(project_id)
        pf9_response = requests.get("{}/{}".format(du_url,api_endpoint), verify=False, headers=headers)
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
    except:
        return None


def create_cluster():
    write_host("Creating Cluster : {}".format(args.cluster_name))
    nodepool_id = get_nodepool_id()
    if nodepool_id == None:
        fail_bootstrap("failed to get nodepool_id for cloud provider")
    write_host("nodepool_id = {}".format(nodepool_id))

    # configure cluster
    cluster_create_payload = {
        "name": args.cluster_name,
        "containersCidr": args.containersCidr,
        "servicesCidr": args.servicesCidr,
        "externalDnsName": args.externalDnsName,
        "privileged": args.privileged,
        "appCatalogEnabled": args.appCatalogEnabled,
        "allowWorkloadsOnMaster": args.allowWorkloadsOnMaster,
        "masterless": False,
        "tags": {},
        "runtimeConfig": "",
        "nodePoolUuid": nodepool_id,
        "masterVipIpv4": args.masterVip,
        "masterVipIface": args.masterVipIf,
        "metallbCidr": args.metallbCidr,
        "networkPlugin": args.networkPlugin
    }
    write_host("--> cluster configuration")
    write_host("{}".format(pprint(cluster_create_payload)))

    # create cluster (post to qbert)
    try:
        api_endpoint = "qbert/v3/{}/clusters".format(project_id)
        pf9_response = requests.post("{}/{}".format(du_url,api_endpoint), verify=False, headers=headers, data=json.dumps(cluster_create_payload))
    except:
        fail_bootstrap("failed to create cluster")

    # parse resmgr response
    try:
        json_response = json.loads(pf9_response.text)
    except:
        fail_bootstrap("cluster created, but response did not include the cluster uuid")
    write_host("cluster created successfully, id = {}".format(json_response['uuid']))


def cluster_exists(cluster_name):
    try:
        api_endpoint = "qbert/v3/{}/clusters".format(project_id)
        pf9_response = requests.get("{}/{}".format(du_url,api_endpoint), verify=False, headers=headers)
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
        if item['name'] == cluster_name:
            return(True, item['uuid'])

    # final return
    return False, None


def wait_for_cluster():
    TIMEOUT = 5
    POLL_INTERVAL = 2

    # timeout loop
    timeout = int(time.time()) + (60 * TIMEOUT)
    flag_cluster_exists = False
    while True:
        cluster_status, cluster_uuid = cluster_exists(args.cluster_name)
        write_host("Waiting for cluster to be created, status = {}".format(cluster_status))
        if cluster_status == True:
            flag_cluster_exists = True
            break
        elif int(time.time()) > timeout:
            break
        else:
            time.sleep(POLL_INTERVAL)

    # enforce TIMEOUT
    if not flag_cluster_exists:
        fail_bootstrap("TIMEOUT: waiting for cluster to be created (qbert)")

    # return cluster uuid
    return(cluster_uuid)


####################################################################################################
## main
####################################################################################################
args = _parse_args()

# set global vars
du_url = args.du_url
du_username = args.du_username
du_password = args.du_password
du_tenant = args.du_tenant

# login to du
project_id, token = login_du(args.du_url, args.du_username, args.du_password, args.du_tenant)
headers = { 'content-type': 'application/json', 'X-Auth-Token': token }

# create cluster
write_host("[Creating Cluster: {}]".format(args.cluster_name))
cluster_status, cluster_uuid = cluster_exists(args.cluster_name)
if cluster_status == True:
    fail_bootstrap("cluster already exists")
else:
    create_cluster()
    cluster_uuid = wait_for_cluster()
    write_host("--> UUID = {}".format(cluster_uuid))
