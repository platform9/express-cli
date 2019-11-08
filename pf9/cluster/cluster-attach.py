import os
import sys
import time
import requests
import argparse
import json
import signal
import ConfigParser

# global variables
control_plane_pause = 30


def _parse_args():
    ap = argparse.ArgumentParser(sys.argv[0],formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('cluster_name', help='cluster name')
    ap.add_argument('du_url', help='du_url')
    ap.add_argument('du_username', help='du_username')
    ap.add_argument('du_password', help='du_password')
    ap.add_argument('du_tenant', help='du_tenant')
    ap.add_argument('master_nodes', help='comma-delimited list of ip addresses')
    ap.add_argument('worker_nodes', help='comma-delimited list of ip addresses')
    ap.add_argument("--verbose", "-v", help="increase verbosity", action="store_true")
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


def get_token(du_host, username, password, project_name):
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
        project_id, token = get_token(du_url, du_username, du_password, du_tenant)
        write_host("--> project_id = {}".format(project_id))
    except:
        fail_bootstrap("failed to get token")

    return(project_id, token)


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


def wait_for_n_active_masters(project_id,cluster_name,master_node_num):
    TIMEOUT = 15
    POLL_INTERVAL = 30
    timeout = int(time.time()) + (60 * TIMEOUT)
    flag_found_n_masters = False
    while True:
        n = get_num_active_masters(project_id,cluster_name)
        write_host("waiting for {} masters to become active (n={})".format(master_node_num,n))
        if int(n) == int(master_node_num):
            flag_found_n_masters = True
            break
        elif int(time.time()) > timeout:
            break
        else:
            time.sleep(POLL_INTERVAL)

    # enforce TIMEOUT
    if not flag_found_n_masters:
        fail_bootstrap("TIMEOUT: waiting for {} masters to become active".format(master_node_num))


def get_num_active_masters(project_id,cluster_name):
    num_active_masters = 0
    try:
        api_endpoint = "qbert/v3/{}/nodes".format(project_id)
        pf9_response = requests.get("{}/{}".format(du_url,api_endpoint), verify=False, headers=headers)
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
        if node['clusterName'] == cluster_name:
            try:
                node['isMaster']
                node['api_responding']
            except:
                continue

            if node['isMaster'] == 1 and node['api_responding'] == 1:
                num_active_masters += 1

    return(num_active_masters)


def get_resmgr_hostid(du_url,project_id,host_ip):
    try:
        api_endpoint = "resmgr/v1/hosts".format(project_id)
        pf9_response = requests.get("{}/{}".format(du_url,api_endpoint), verify=False, headers=headers)
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
        for key, value in host['extensions']['interfaces']['data'].iteritems():
            for iface_name, iface_ip in host['extensions']['interfaces']['data']['iface_ip'].iteritems():
                if iface_ip == host_ip:
                    return(host['id'])


def get_uuids(project_id, host_ips):
    # map list of IPs to list of UUIDs
    host_uuids = []
    for host_ip in host_ips:
        host_uuid = get_resmgr_hostid(du_url, project_id, host_ip)
        if host_uuid != None:
            host_uuids.append(host_uuid)

    return(host_uuids)


def cluster_convergence_status(cluster_uuid):
    converge_status = "pending"
    try:
        api_endpoint = "qbert/v3/{}/clusters/{}".format(project_id,cluster_uuid)
        pf9_response = requests.get("{}/{}".format(du_url,api_endpoint), verify=False, headers=headers)
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


def wait_for_cluster():
    TIMEOUT = 5
    POLL_INTERVAL = 2

    # timeout loop
    timeout = int(time.time()) + (60 * TIMEOUT)
    flag_cluster_exists = False
    while True:
        cluster_status, cluster_uuid = cluster_exists(args.cluster_name)
        write_host("--> waiting for cluster to be created, status = {}".format(cluster_status))
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


def attach_to_cluster(cluster_uuid, project_id, node_type, uuid_list):
    write_host("[Attaching {} Nodes to Cluster]".format(node_type))

    # configure attach payload (master nodes)
    cluster_attach_payload = []
    for uuid in uuid_list:
        if node_type == 'master':
            master_flag = True
        else:
            master_flag = False

        payload_item = {
            "uuid": uuid,
            "isMaster": master_flag
        }
        cluster_attach_payload.append(payload_item)

    # wait for cluster to be ready
    TIMEOUT = 5
    POLL_INTERVAL = 2

    # timeout loop
    timeout = int(time.time()) + (60 * TIMEOUT)
    flag_cluster_ready = False
    while True:
        cluster_status = cluster_convergence_status(cluster_uuid)
        write_host("waiting for cluster to become ready, status = {}".format(cluster_status))
        if cluster_status == "ok":
            flag_cluster_ready = True
            break
        elif int(time.time()) > timeout:
            break
        else:
            time.sleep(POLL_INTERVAL)

    # enforce TIMEOUT
    if not flag_cluster_ready:
        fail_bootstrap("TIMEOUT: waiting for cluster to become ready")

    # attach to cluster (retry loop)
    num_retries = 5
    cnt = 0
    while cnt < num_retries:
        if cnt > 0:
            write_host("--> attaching to cluster (retry {})".format(cnt))
        else:
            write_host("--> attaching to cluster")

        try:
            api_endpoint = "qbert/v3/{}/clusters/{}/attach".format(project_id,cluster_uuid)
            pf9_response = requests.post("{}/{}".format(du_url,api_endpoint), verify=False, headers=headers, data=json.dumps(cluster_attach_payload))
            if pf9_response.status_code == 200:
                write_host("Build Completed | {}".format(int(time.time())))
                write_host("--> successfully attached to cluster")
                break
            else:
                write_host("failed to attach to cluster: {}".format(pf9_response.text))
        except:
            None

        cnt += 1
        time.sleep(5)

    if cnt >= num_retries:
        write_host("Build Failed | {}".format(int(time.time())))
        fail_bootstrap("failed to attach to cluster after {} attempts".format(num_retries))


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

# get uuids for master nodes
master_nodes = get_uuids(project_id,args.master_nodes.split(','))
write_host("\n[Discovering UUIDs for Cluster Nodes]")
write_host("--> Master Nodes")
for node in master_nodes:
    write_host("{}".format(node))

# get uuids for worker nodes
worker_nodes = get_uuids(project_id,args.worker_nodes.split(','))
write_host("--> Worker Nodes")
for node in worker_nodes:
    write_host("{}".format(node))

# wait for cluster to by ready
write_host("\n[Attaching to Cluster: {}]".format(args.cluster_name))
cluster_uuid = wait_for_cluster()

# attach master nodes
attach_to_cluster(cluster_uuid, project_id, 'master', master_nodes)
wait_for_n_active_masters(project_id,args.cluster_name,len(master_nodes))

# attach worker nodes
attach_to_cluster(cluster_uuid, project_id, 'worker', worker_nodes)

