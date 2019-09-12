import click
import os
from prettytable import PrettyTable


@click.group()
def inventory():
    """Manage Platform9 Express Inventories"""

@config.command('list')
@click.pass_obj
def list(obj):
    """List Platform9 Express Inventories."""
    # lists pf9-express inventories 
    pf9_exp_conf_dir = obj['pf9_exp_conf_dir']

    if os.path.exists(pf9_exp_conf_dir):
        count = 1
        result = PrettyTable()
        result.field_names = ["#","Active", "Conf", "Management Plane", "Region"]
        files = [f for f in os.listdir(pf9_exp_conf_dir) if os.path.isfile(os.path.join(pf9_exp_conf_dir, f))]

