import re
import netifaces
import ipaddress
from .exceptions import SSHInfoMissing, MissingVIPDetails


def print_help_msg(command):
    """Print Command's Help message"""
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))


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
    Get non local IPv4/IPV6 addresses
    """
    nw_ifs = netifaces.interfaces()
    nonlocal_ips = set()
    ignore_ip_re = re.compile('^(0.0.0.0|127.0.0.1)$')
    ignore_if_re = re.compile('^(q.*-[0-9a-fA-F]{2}|tap.*|virbr.*)$')

    for iface in nw_ifs:
        if ignore_if_re.match(iface):
            continue
        addrs = netifaces.ifaddresses(iface)
        
        ips = []
        if netifaces.AF_INET in addrs:
            ips.extend(addrs[netifaces.AF_INET])
        if netifaces.AF_INET6 in addrs:
            ips.extend(addrs[netifaces.AF_INET6])
        
        for ip in ips:
            try:
                ip_addr = ipaddress.ip_address(ip['addr'])
            except ValueError:
                # the link local sometime appears to have an invalid prefix
                # ignore those interfaces
                continue
            # Add non-link local/loopback or multicast ip addresses
            if not (ip_addr.is_loopback or ip_addr.is_link_local or ip_addr.is_multicast):
                nonlocal_ips.add(ip['addr'])
        

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
