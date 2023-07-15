from argparse import Namespace
import sys

from asset.assetfile import \
    get_asset_path, yaml_to_nx, nx_to_yaml, add_to_nx, search_nodes, \
    retrieve_item, del_from_nx, mod_nx_node
from asset.display import display_tree

import networkx as nx
from rich import print


def asset_avail(args: Namespace) -> None:
    ''' Logic for `asset avail` / `asset spider` '''

    # read the asset tree for each file in the $ASSETPATH
    for p in get_asset_path():
        asset_net = yaml_to_nx(p)
        # subset the tree if a search term was provided
        if args.search:
            asset_net = search_nodes(
                asset_net, args.search,
                ancestors=True, descendants=True,
                fuzzy=False if args.exact else True)
        # display the tree
        if asset_net:
            print(display_tree(asset_net, args.command == 'spider'))
            print()


def asset_pull(args: Namespace) -> None:
    ''' Logic for `asset pull` '''

    # read the asset tree for each file in the $ASSETPATH
    for p in get_asset_path():
        asset_net = yaml_to_nx(p)
        # return the path of the first item to match uniquely
        if (path := retrieve_item(asset_net, args.search)):
            print(path)
            sys.exit(0)
    # else die
    print(f'Could not resolve asset path: {args.search}')
    sys.exit(1)


def asset_add(args: Namespace) -> None:
    ''' Logic for `asset add` '''

    asset_net = yaml_to_nx(get_asset_path()[0])
    add_to_nx(args, asset_net)
    nx_to_yaml(asset_net)


def asset_mod(args: Namespace) -> None:
    ''' Logic for `asset mod` '''

    # read the asset tree for each file in the $ASSETPATH
    for p in get_asset_path():
        asset_net = yaml_to_nx(p)
        # make a copy so that we can compare the objects downstream
        an = asset_net.copy()
        # modify the first asset to match uniquely
        mod_nx_node(args, an)
        if not nx.utils.graphs_equal(asset_net, an):
            nx_to_yaml(an)
            sys.exit(0)
    # die if no changes made
    print(f'Could not resolve asset path: {args.search}')
    sys.exit(1)


def asset_del(args: Namespace) -> None:
    ''' Logic for `asset del` '''

    # read the asset tree for each file in the $ASSETPATH
    for p in get_asset_path():
        asset_net = yaml_to_nx(p)
        # make a copy so that we can compare the objects downstream
        an = asset_net.copy()
        # delete the first asset to match uniquely
        del_from_nx(args, an)
        if not nx.utils.graphs_equal(asset_net, an):
            nx_to_yaml(an)
            sys.exit(0)
    # die if no changes made
    print(f'Could not resolve asset path: {args.search}')
    sys.exit(1)
