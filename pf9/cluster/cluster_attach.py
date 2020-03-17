import os
import time
import requests
import json
import click

from pf9.cluster.exceptions import ClusterAttachFailed, FailedActiveMasters, ClusterNotAvailable
from pf9.modules.util import Logger

logger = Logger(os.path.join(os.path.expanduser("~"), 'pf9/log/pf9ctl.log')).get_logger(__name__)

def write_host(m):
    if m is not None:
        logger.info(m)
        click.echo("{}".format(m))


class AttachCluster(object):

    def __init__(self, ctx):
        self.ctx = ctx
        self.project_id = ctx.params['project_id']
        self.token = ctx.params['token']
        self.du_url = ctx.params['du_url']
        self.cluster_name = ctx.params['cluster_name']
        self.headers = { 'content-type': 'application/json', 'X-Auth-Token': self.token }

    def wait_for_n_active_masters(self, master_node_num):
        if master_node_num == 1:
            TIMEOUT_SECS = 900
        else:
            TIMEOUT_SECS = 900
        POLL_INTERVAL = 10  # in secs
        flag_found_n_masters = False
        start_time = time.time()
        with click.progressbar(length=TIMEOUT_SECS, color="orange",
                               label='Waiting for all masters to become active') as bar:
            log_counter = 0
            update_interval = time.time()
            while True:
                log_counter = log_counter + 1
                current_active_masters = self.get_num_active_masters()
                if int(current_active_masters) == int(master_node_num):
                    flag_found_n_masters = True
                    break
                elif int(time.time() - start_time) < TIMEOUT_SECS:
                    bar.update(time.time() - update_interval)
                    if log_counter % 3 == 0:
                        logger.info("{} of {} Master nodes active".format(current_active_masters, master_node_num))
                elif int(time.time() - start_time) > TIMEOUT_SECS:
                    break
                update_interval = time.time()
                time.sleep(POLL_INTERVAL)

            # Success or failure... push the progress to 100%
            bar.update(TIMEOUT_SECS)

        # enforce TIMEOUT
        if not flag_found_n_masters:
            msg = "Timed out waiting for {} master to become active. Current " \
                  "active count {}.".format(master_node_num, current_active_masters)
            raise FailedActiveMasters(msg)
        logger.info("{} of {} master nodes now available".format(master_node_num, current_active_masters))

    def get_num_active_masters(self):
        num_active_masters = 0
        try:
            api_endpoint = "qbert/v3/{}/nodes".format(self.project_id)
            pf9_response = requests.get("{}/{}".format(self.du_url, api_endpoint),
                                        headers=self.headers)
            if pf9_response.status_code != 200:
                return num_active_masters

            # parse response
            json_response = json.loads(pf9_response.text)
        except Exception as except_err:
            logger.exception("Failed get_num_active_masters: {}: {}".format(num_active_masters, except_err))
            return num_active_masters

        for node in json_response:
            if 'clusterName' not in node:
                continue
            if node['clusterName'] == self.cluster_name:
                try:
                    if node['isMaster'] == 1 and node['api_responding'] == 1 \
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
        except Exception as except_err:
            logger.exception(except_err)
            return None

        # sequentially search results
        for host in json_response:
            if 'extensions' not in host:
                continue
            # TODO: Why is there a loop in a loop where the values from the first loop aren't used?
            for key, value in host['extensions']['interfaces']['data'].items():
                for iface_name, iface_ip in host['extensions']['interfaces']['data']['iface_ip'].items():
                    if iface_ip == host_ip:
                        logger.info("Node host_id: {}".format(host['id']))
                        return host['id']

    def get_uuids(self, host_ips):
        # map list of IPs to list of UUIDs
        host_uuids = []
        for host_ip in host_ips:
            host_uuid = self.get_resmgr_hostid(host_ip)
            if host_uuid is not None:
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
        except Exception as except_err:
            logger.exception("Converge Status: {}: {}".format(converge_status, except_err))
            return converge_status

        if json_response['status']:
            return json_response['status']
        else:
            return converge_status

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
        write_host("Waiting for cluster to become ready")
        while True:
            cluster_status = self.cluster_convergence_status(cluster_uuid)
            logger.info("Waiting for cluster to become ready, status = {}".format(cluster_status))
            if cluster_status == "ok":
                flag_cluster_ready = True
                break
            elif int(time.time()) > timeout:
                break

            time.sleep(POLL_INTERVAL)

        # enforce TIMEOUT
        if not flag_cluster_ready:
            except_msg = "TIMEOUT: waiting for cluster to become ready"
            raise ClusterNotAvailable(except_msg)

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
        logger.info("Attach Complete")

        if cnt >= num_retries:
            msg = "Failed to attach to cluster after {} attempts".format(num_retries)
            raise ClusterAttachFailed(msg)
