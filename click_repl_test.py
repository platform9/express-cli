import click
import click_repl
import os
from prompt_toolkit.history import FileHistory

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Pleasantries CLI"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)

@cli.command()
@click.option('--name', default='world')
def hello(name):
    """Say hello"""
    click.echo('Hello, {}!'.format(name))

@cli.command()
@click.option('--name', default='moon')
def goodnight(name):
    """Say goodnight"""
    click.echo('Goodnight, {}.'.format(name))

@cli.command()
@click.option('--name', default='moon')
def exit():
    """exit"""
    sys.exit(1)

@cli.command()
def repl():
    """Start an interactive session"""
    prompt_kwargs = {
        'history': FileHistory(os.path.expanduser('~/.repl_history'))
    }
    click_repl.repl(click.get_current_context(), prompt_kwargs=prompt_kwargs)

if __name__ == '__main__':
    cli(obj={})
