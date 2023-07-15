#!/usr/bin/python3.9

''' asset: a tracker for shared assets on HPC clusters '''

###############################################################################
#    __   ____  ____  ____  ____
#   / _\ / ___)/ ___)(  __)(_  _)
#  /    \\___ \\___ \ ) _)   )(
#  \_/\_/(____/(____/(____) (__)
#
###############################################################################


import argparse
from pathlib import Path
import sys

from asset import __prog__, __version__, __status__
from asset.commands import \
    asset_avail, asset_pull, asset_add, asset_mod, asset_del

from asset.assetfile import get_asset_path, init_yaml

from rich_argparse import ArgumentDefaultsRichHelpFormatter, RawDescriptionRichHelpFormatter
from rich import print


# globals #####################################################################


# parse the $ASSETPATH environmental variable
try:
    asset_path = get_asset_path()
except:
    asset_path = [None]


class RichFormatter(
        ArgumentDefaultsRichHelpFormatter, RawDescriptionRichHelpFormatter):
    ''' A custom rich text formatter for argparse that fuses two via multiple
    inheritance '''

    pass


# argparse ####################################################################


commands = {}

parser = argparse.ArgumentParser(
    prog=__prog__,
    description=r'''
                         __   ____  ____  ____  ____
                        / _\ / ___)/ ___)(  __)(_  _)
                       /    \\___ \\___ \ ) _)   )(
                       \_/\_/(____/(____/(____) (__)

    [bold]asset[/bold] manages the storage, access, and maintenance of central 'reference
 collections' for resources that are frequently duplicated by individual users.
  It is ambivalent to what these resources are. [bold]asset[/bold] increases resilience and
      reproducibility whilst reducing the burden on shared filesystems.
''',
    epilog=f'''
[dark_orange]Loaded asset paths:[/dark_orange]
{", ".join(str(p) for p in asset_path) if asset_path else None}
''',
    formatter_class=RichFormatter,
    exit_on_error=False,
    allow_abbrev=False)
subparsers = parser.add_subparsers(
    title='commands',
    metavar='{command}',
    dest='command',
    required=True)

parser.add_argument(
    '-v', '--version',
    action='version', version=f'{__prog__} v{__version__} ({__status__})',
    help='show the program version and exit')

# user presented
commands['avail'] = commands['spider'] = subparsers.add_parser(
    'avail',
    aliases=['spider'],
    help='list (avail) or detail list (spider) all available assets',
    description='list (avail) or detail list (spider) all available assets',
    formatter_class=ArgumentDefaultsRichHelpFormatter)
commands['avail'].add_argument(
    'search', type=str, nargs='?',
    help='complete or partial asset path or search term')
commands['avail'].add_argument(
    '--exact', action='store_true',
    help='disable fuzzy matching')

# user presented
commands['pull'] = subparsers.add_parser(
    'pull',
    help='retrieve the location of an asset',
    description='retrieve the location of an asset',
    formatter_class=ArgumentDefaultsRichHelpFormatter)
commands['pull'].add_argument(
    'search', type=str,
    help='asset search path')

# user hidden (no help text)
commands['init'] = subparsers.add_parser(
    'init',
    description='create a new asset description file',
    formatter_class=ArgumentDefaultsRichHelpFormatter)
commands['init'].add_argument(
    'path', type=Path,
    help='asset description file')
commands['init'].add_argument(
    'store', type=Path,
    help='data store location')
commands['init'].add_argument(
    '--mkdir', action='store_true',
    help='create directory for `store` if necessary')
commands['init'].add_argument(
    '--force', action='store_true',
    help='overwrite existing asset description file')

# user hidden (no help text)
commands['add'] = subparsers.add_parser(
    'add',
    description='add an asset or collection',
    formatter_class=ArgumentDefaultsRichHelpFormatter)
commands['add'] .add_argument(
    '--alias', type=str, nargs='+', required=True,
    help='name(s) to register')
commands['add'] .add_argument(
    '--tag', type=str, nargs='+', default=None,
    help='tag(s) to associate')
commands['add'] .add_argument(
    '--item', type=Path, default=None,
    help='path to asset')
commands['add'] .add_argument(
    '--parent', type=str,
    help='parent of the asset or collection')
commands['add'] .add_argument(
    '--inherit', action='store_true',
    help='make item discoverable with the same basename as its parent')
commands['add'] .add_argument(
    '--description', type=str,
    help='description text')
commands['add'] .add_argument(
    '--mode', type=str, choices=['copy', 'move', 'link'], default='link',
    help='copy or move asset(s) into the store or link in place')
commands['add'] .add_argument(
    '--nodigest', dest='digest', action='store_false',
    help='don\'t calculate md5 digests for file assets')

# user hidden (no help text)
commands['mod'] = subparsers.add_parser(
    'mod',
    description='modify an asset or collection',
    formatter_class=ArgumentDefaultsRichHelpFormatter)
commands['mod'].add_argument(
    'search', type=str, nargs='?',
    help='complete or partial asset path or search term')
commands['mod'] .add_argument(
    '--alias', type=str, nargs='+',
    help='replacement name(s) to register')
commands['mod'] .add_argument(
    '--tag', type=str, nargs='+', default=None,
    help='replacement tag(s) to associate')
commands['mod'] .add_argument(
    '--item', type=Path, default=None,
    help='replacement path to asset')
commands['mod'] .add_argument(
    '--parent', type=str,
    help='replacement parent of the asset or collection')
commands['mod'] .add_argument(
    '--inherit', action='store_true',
    help='make item discoverable with the same basename as its parent')
commands['mod'] .add_argument(
    '--description', type=str,
    help='replacement description text')
commands['mod'] .add_argument(
    '--mode', type=str, choices=['copy', 'move', 'link'], default='link',
    help='copy or move asset(s) into the store or link in place')
commands['mod'] .add_argument(
    '--nodigest', dest='digest', action='store_false',
    help='don\'t calculate md5 digests for file assets')

# user hidden (no help text)
commands['del'] = subparsers.add_parser(
    'del',
    description="delete an asset",
    formatter_class=ArgumentDefaultsRichHelpFormatter)
commands['del'].add_argument(
    'search', type=str,
    help='asset search path')
commands['del'] .add_argument(
    '--recursive', action='store_true',
    help='allow recursive deletion of child assets')

###############################################################################


if __name__ == '__main__':

    # catch program name by itself
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # catch command name by itself
    if len(sys.argv) == 2 \
            and sys.argv[1] in commands \
            and sys.argv[1] not in ('avail', 'spider'):
        commands[sys.argv[1]].print_help()
        sys.exit(0)

    # catch unknown command and errors
    try:
        args = parser.parse_args()
    except argparse.ArgumentError:
        parser.print_help()
        sys.exit(1)

    # print(args)

    # Run the relevant command from asset.commands
    match args.command:
        case 'init':
            init_yaml(args)
        case 'avail' | 'spider':
            asset_avail(args)
        case 'pull':
            asset_pull(args)
        case 'add':
            asset_add(args)
        case 'mod':
            asset_mod(args)
        case 'del':
            asset_del(args)
