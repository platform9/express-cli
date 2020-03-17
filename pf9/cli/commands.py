import click
import sys
from os import path
from ..modules.util import Pf9ExpVersion

@click.group(invoke_without_command=True)
@click.pass_obj
def version(obj):
    """Show Platform9 Express version."""
    version_file_path = path.join(obj['pf9_exp_dir'], 'version')
    try: 
        current_version = Pf9ExpVersion().get_local(version_file_path)
    except (UnboundLocalError, Exception):
        click.echo('Installed PF9-Express version information not available\nTry:\n    $ express init --help')
        sys.exit(1)
    if current_version != '':
        click.echo('Installed Platform9 Express Version: %s' % current_version)
    else:
        click.echo('Installed PF9-Express version information not available\nTry:\n    $ express init --help')
