import click
from os import path
from ..modules.util import Pf9ExpVersion

@click.group(invoke_without_command=True)
@click.pass_obj
def version(obj):
    """Show Platform9 Express version."""
    # print current version of pf9-express 
    ver = Pf9ExpVersion()
    ver_file_path = path.join(obj['pf9_exp_dir'], 'version')
    try: 
        version = ver.get_local(ver_file_path)
    except:
        click.echo('Installed PF9-Express version information not available\nTry:\n    $ express init --help')
    else:
        if version != '':
            click.echo('Installed Platform9 Express Version: %s' % version)
        else:
            click.echo('Installed PF9-Express version information not available\nTry:\n    $ express init --help')



