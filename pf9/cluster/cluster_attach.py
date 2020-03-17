import click
import os
import sys
import time
import requests
import json
import signal

from ..exceptions import ClusterAttachFailed

# global variables
control_plane_pause = 30

def fail_bootstrap(m):
    if m != None:
        click.echo("ERROR: {}".format(m))
    sys.exit(1)


def write_host(m):
    if m != None:
        click.echo("{}".format(m))


class AttachCluster(object):

    def __init__(self, ctx):
        self.project_id = ctx.params['project_id']
        self.token = ctx.params['token']
        self.du_url = ctx.params['du_url']
        self.ctx = ctx
        self.headers = { 'content-type': 'application/json', 'X-Auth-Token': self.token }
        control_plane_pause = 30

    def cluster_exists(self, cluster_name):
        try:
            api_endpoint = "qbert/v3/{}/clusters".format(self.project_id)
            pf9_response = requests.get("{}/{}".format(self.du_url, api_endpoint),
                                        headers=self.headers)
            if pf9_response.status_code != 200:
                return False, None

            # parse qbert response
            json_response = json.loads(pf9_response.text)
            for item in json_response:
                if item['name'] == cluster_name:
                    return True, item['uuid']
        except:
            return False, None

        # final return
        return False, None

    def wait_for_n_active_masters(self, cluster_name, master_node_num):
        TIMEOUT = 15 # in mins
        POLL_INTERVAL = 30 # in secs
        total_timeout_duration = 60 * TIMEOUT
        timeout = int(time.time()) + total_timeout_duration
        current_active_masters = 0
        flag_found_n_masters = False
        with click.progressbar(length=total_timeout_duration, color="orange",
                           label='Waiting for all masters to become active') as bar:
            while True:
                current_active_masters = self.get_num_active_masters(cluster_name)
                if int(current_active_masters) == int(master_node_num):
                    flag_found_n_masters = True
                    break
                elif int(time.time()) < timeout - POLL_INTERVAL:
                    bar.update(POLL_INTERVAL)
                elif int(time.time()) > timeout:
                    break
                
                time.sleep(POLL_INTERVAL)

            # Success or failure... push the progress to 100%
            bar.update(total_timeout_duration)

        # enforce TIMEOUT
        if not flag_found_n_masters:
            msg = "Timed out waiting for {} master to become active. Current " \
                  "active count {}.".format(master_node_num, current_active_masters)
            raise FailedActiveMasters(msg)

    def get_num_active_masters(self, cluster_name):
        num_active_masters = 0
        try:
            api_endpoint = "qbert/v3/{}/nodes".format(self.project_id)
            pf9_response = requests.get("{}/{}".format(self.du_url, api_endpoint),
                                        headers=self.headers)
            if pf9_response.status_code != 200:
                return num_active_masters

            # parse response
            json_response = json.loads(pf9_response.text)
        except:
            return num_active_masters

        for node in json_response:
            if not 'clusterName' in node:
                continue
            if node['clusterName'] == cluster_name:
                try:
                    if node['isMaster'] ==  1 and node['api_responding'] == 1 \
                            and node['status'] == 'ok':
                        num_active_masters += 1
                except Exception:
                    continue
        return num_active_masters


    def get_resmgr_hostid(self, host_ip):
        try:
            api_endpoint = "resmgr/v1/hosts"
            pf9_response = requests.get("{}/{}".format(self.du_url, api_endpoint), 
                                        headers=self.headers)
            if pf9_response.status_code != 200:
                return None

            # parse resmgr response
            json_response = json.loads(pf9_response.text)
        except:
            return None

        # sequentially search results
        for host in json_response:
            if not 'extensions' in host:
                continue
            for key, value in host['extensions']['interfaces']['data'].items():
                for iface_name, iface_ip in host['extensions']['interfaces']['data']['iface_ip'].items():
                    if iface_ip == host_ip:
                        return host['id']


    def get_uuids(self, host_ips):
        # map list of IPs to list of UUIDs
        host_uuids = []
        for host_ip in host_ips:
            host_uuid = self.get_resmgr_hostid(host_ip)
            if host_uuid != None:
                host_uuids.append(host_uuid)
            else:
                # TODO: We should warn the end user and proceed?
                pass

        return host_uuids


    def cluster_convergence_status(self, cluster_uuid):
        converge_status = "pending"
        try:
            api_endpoint = "qbert/v3/{}/clusters/{}".format(self.project_id, cluster_uuid)
            pf9_response = requests.get("{}/{}".format(self.du_url, api_endpoint),
                                        headers=self.headers)
            if pf9_response.status_code != 200:
                return converge_status

            # parse qbert response
            json_response = json.loads(pf9_response.text)
        except:
            return converge_status

        if json_response['status']:
            return(json_response['status'])
        else:
            return converge_status


    def wait_for_cluster(self, cluster_name):
        TIMEOUT = 5
        POLL_INTERVAL = 2

        # timeout loop
        timeout = int(time.time()) + (60 * TIMEOUT)
        flag_cluster_exists = False
        while True:
            cluster_status, cluster_uuid = self.cluster_exists(cluster_name)
            write_host("Checking if cluster is available, status = {}".format(cluster_status))
            if cluster_status == True:
                flag_cluster_exists = True
                break
            elif int(time.time()) > timeout:
                break

            time.sleep(POLL_INTERVAL)

        # enforce TIMEOUT
        if not flag_cluster_exists:
            fail_bootstrap("TIMEOUT: waiting for cluster to be available")

        # return cluster uuid
        return cluster_uuid


    def attach_to_cluster(self, cluster_uuid, node_type, uuid_list):
        write_host("Attaching {} nodes to the cluster".format(node_type))

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
            cluster_status = self.cluster_convergence_status(cluster_uuid)
            write_host("Waiting for cluster to become ready, status = {}".format(cluster_status))
            if cluster_status == "ok":
                flag_cluster_ready = True
                break
            elif int(time.time()) > timeout:
                break

            time.sleep(POLL_INTERVAL)

        # enforce TIMEOUT
        if not flag_cluster_ready:
            fail_bootstrap("TIMEOUT: waiting for cluster to become ready")

        # attach to cluster (retry loop)
        num_retries = 5
        cnt = 0
        while cnt < num_retries:
            if cnt > 0:
                write_host("Attaching to cluster (retry {})".format(cnt))
            else:
                write_host("Attaching to cluster")

            try:
                api_endpoint = "qbert/v3/{}/clusters/{}/attach".format(self.project_id,
                                                                       cluster_uuid)
                pf9_response = requests.post("{}/{}".format(self.du_url, api_endpoint),
                                             headers=self.headers,
                                             data=json.dumps(cluster_attach_payload))
                if pf9_response.status_code == 200:
                    write_host("Successfully attached to cluster")
                    break
                else:
                    msg = "Failed to attach to cluster: {}".format(pf9_response.text)
                    write_host(msg)
            except:
                pass

            cnt += 1
            time.sleep(5)

        if cnt >= num_retries:
            msg = "Failed to attach to cluster after {} attempts".format(num_retries)
            fail_bootstrap(msg)
            raise ClusterAttachFailed(msg)


