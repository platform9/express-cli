import re
import netifaces
from .exceptions import SSHInfoMissing, MissingVIPDetails


def build_express_run_command():
    """Build Ansible-Playbook Command"""
#     ansible-playbook -i /tmp/pf9_zlha37f3/exp-inventory \
#             -l pmk \
#             -e "skip_prereq=1 autoreg='on' \
#             du_fqdn='cfe-tomchris.platform9.horse' \
#             ctrl_ip='131.153.252.189' \
#             du_username='tom.christopoulos@platform9.com' \
#             du_password=''" \
#             /pf9/pf9-express/express/pf9-k8s-express.yml \
#             2>$1 | tee /home/tomchris/pf9/log/express_2020_02_04-17_02_31.log


def validate_ssh_details(user, password, ssh_key):

    missing = []
    if not user:
        missing.append('SSH user')
    if not password and not ssh_key:
        missing.append('SSH password or SSH key')

    if missing:
        raise SSHInfoMissing(missing)


def get_local_node_addresses():
    """
    Get non local IPv4 addresses
    """
    nw_ifs = netifaces.interfaces()
    nonlocal_ips = set()
    ignore_ip_re = re.compile('^(0.0.0.0|127.0.0.1)$')
    ignore_if_re = re.compile('^(q.*-[0-9a-fA-F]{2}|tap.*|virbr.*)$')

    for iface in nw_ifs:
        if ignore_if_re.match(iface):
            continue
        addrs = netifaces.ifaddresses(iface)
        try:
            if netifaces.AF_INET in addrs:
                ips = addrs[netifaces.AF_INET]
                for ip in ips:
                    # Not interested in loopback IPs
                    if not ignore_ip_re.match(ip['addr']):
                        nonlocal_ips.add(ip['addr'])
            else:
                # move to next interface if this interface doesn't
                # have IPv4 addresses
                continue
        except KeyError:
            pass

    return list(nonlocal_ips)


def check_vip_needed(masters, vip, vip_if):
    missing = []
    if len(masters) > 1:
        if not vip:
            missing.append('VIP')
        if not vip_if:
            missing.append('VIP network interface')

    if missing:
        raise MissingVIPDetails(missing)

    return True
