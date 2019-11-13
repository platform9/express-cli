import os
import sys
import time
import json
import click
from .cluster_utils import ClusterUtils
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class ClusterAttach(object):
    def __init__(self, ctx):
        self.ctx = ctx
        self.project_id = ctx.params['project_id']
        self.token = ctx.params['token']
        self.du_url = ctx.params['du_url']
        self.headers = { 'content-type': 'application/json', 'X-Auth-Token': self.token }

    def attach_to_cluster(self, cluster_uuid, node_type, uuid_list):
        click.echo("[Attaching {} Nodes to Cluster]".format(node_type))

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
            cluster_status = ClusterUtils(self.ctx).cluster_convergence_status(cluster_uuid)
            click.echo("waiting for cluster to become ready, status = {}".format(cluster_status))
            if cluster_status == "ok":
                flag_cluster_ready = True
                break
            elif int(time.time()) > timeout:
                break
            else:
                time.sleep(POLL_INTERVAL)

        # enforce TIMEOUT
        if not flag_cluster_ready:
            ClusterUtils(self.ctx).fail_bootstrap("TIMEOUT: waiting for cluster to become ready")

        # attach to cluster (retry loop)
        num_retries = 5
        cnt = 0
        while cnt < num_retries:
            if cnt > 0:
                click.echo("--> attaching to cluster (retry {})".format(cnt))
            else:
                click.echo("--> attaching to cluster")

            try:
                api_endpoint = "qbert/v3/{}/clusters/{}/attach".format(self.project_id, cluster_uuid)
                pf9_response = requests.post("{}/{}".format(self.du_url,api_endpoint), verify=False, headers=self.headers, data=json.dumps(cluster_attach_payload))
                if pf9_response.status_code == 200:
                    click.echo("--> successfully attached to cluster")
                    break
                else:
                    click.echo("failed to attach to cluster: {}".format(pf9_response.text))
            except:
                None

            cnt += 1
            time.sleep(5)

        if cnt >= num_retries:
            click.echo("Build Failed | {}".format(int(time.time())))
            ClusterUtils(self.ctx).fail_bootstrap("failed to attach to cluster after {} attempts".format(num_retries))
