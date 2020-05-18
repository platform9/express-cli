##
## Ansible Inventory
##

[all]
[all:vars]
manage_hostname=False
manage_resolvers=False
dns_resolvers='["8.8.8.8", "8.8.4.4"]'

################################################################################################
## Kubernetes Groups
################################################################################################
[pmk:children]
k8s_worker

[k8s_worker]
$node_details

