from argparse import Namespace
from datetime import datetime
from functools import partial
import os
from pathlib import Path
import re
import shutil
import sys

from asset import __prog__, __version__, __status__
from asset.helpers import du, make_key, md5_digest, dir_exists_or_create, file_exists_or_creatable

import networkx as nx
import yaml
load_yaml = partial(yaml.load, Loader=yaml.Loader)
dump_yaml = partial(yaml.dump, Dumper=yaml.Dumper)


yaml_header = f'# {__prog__} v{__version__} ({__status__})'


def check_yaml(path: Path) -> bool:
    ''' Determine if a file is an asset description file '''

    with open(path) as F:
        return F.readline().startswith(f'# {__prog__}')


def get_asset_path() -> list:
    ''' Read the $ASSETPATH environmental variable '''

    asset_files = []
    if (asset_path := os.environ.get('ASSETPATH')) is None:
        return asset_files
    for p in asset_path.split(':'):
        try:
            p = Path(p).resolve(strict=True)
        except FileNotFoundError:
            print(f'Invalid path specified in $ASSETPATH: {p}')
            sys.exit(1)
        if not check_yaml(p):
            print(f'Path specified in $ASSETPATH is not an asset description file: {p}')
            sys.exit(1)
        asset_files.append(p)
    return asset_files


def init_yaml(args: Namespace) -> None:
    ''' Initialise a YAML asset description file '''

    dir_exists_or_create(args.store, args.mkdir)
    file_exists_or_creatable(args.path, args.mkdir, args.force)
    with open(args.path, 'w') as F:
        print(yaml_header, file=F)
        dump_yaml({'store': str(args.store), 'assets': {}}, F)


def yaml_to_nx(path: Path) -> nx.DiGraph:
    ''' Read an asset description file into an asset network object '''

    with open(path) as F:
        yaml_data = load_yaml(F)
    edges = []
    asset_net = nx.DiGraph(path=str(path), store=yaml_data['store'])
    for name, meta in yaml_data['assets'].items():
        if 'parent' in meta:
            edges.append((meta.pop('parent'), name))
        asset_net.add_node(name, **meta)
    asset_net.add_edges_from(edges)
    return asset_net


def nx_to_yaml(asset_net: nx.DiGraph) -> None:
    ''' Dump the asset network object into an asset description file '''

    assets = {}
    for name, meta in asset_net.nodes(data=True):
        if (parent := list(asset_net.predecessors(name))):
            meta['parent'] = parent[0]
        assets[name] = meta

    tmpfile = Path(f'{asset_net.graph["path"]}.tmp')
    with open(tmpfile, 'w') as F:
        print(yaml_header, file=F)
        dump_yaml({'store': asset_net.graph['store'], 'assets': assets}, F)
    shutil.move(tmpfile, Path(asset_net.graph["path"]))


def all_predecessors(asset_net: nx.DiGraph, node) -> list:
    ''' Walk the asset network from a leaf upwards, recording the path '''

    predecessor_path = []
    while (predecessor := list(asset_net.predecessors(node))):
        predecessor_path.append(node := predecessor[0])
    predecessor_path.reverse()
    return predecessor_path


def resolve_node(
        asset_net: nx.DiGraph, search: str, fuzzy: bool=False) -> list[str]:
    ''' Determine a list of potential matching nodes from a string representation '''

    alias_tag_list = [p.split(':') for p in search.split('/')]
    asset_sub_net = asset_net
    while alias_tag_list:
        alias, *tag = alias_tag_list.pop(0)
        if not fuzzy:
            nodes = [
                n for n, meta in asset_sub_net.nodes(data=True)
                if alias in meta['alias']
                and all(t in meta.get('tag', []) for t in tag)]
        else:  # fuzzy
            nodes = [
                n for n, meta in asset_sub_net.nodes(data=True)
                if re.search(
                    f'^.*{alias}.*$',
                    '_'.join(meta['alias']),
                    flags=re.I) is not None
                and all(
                    re.search(f'^.*{t}.*$', '_'.join(meta.get('tag', [])), flags=re.I) is not None
                    for t in tag)]
        if alias_tag_list:
            asset_sub_net = asset_sub_net.subgraph(
                [n for node in nodes for n in nx.descendants(asset_sub_net, node)])
    return [n for n in nodes]


def add_to_nx(args: Namespace, asset_net: nx.DiGraph) -> None:
    ''' Add an asset/collection to the asset network '''

    if args.inherit and not args.parent:
        print(f'Cannot `--inherit` without a parent')
    if args.parent:
        parent_search = resolve_node(asset_net, args.parent)
        if len(parent_search) > 1:
            print(f'Could not resolve asset path uniquely: {args.parent}')
            sys.exit(1)
        if len(parent_search) == 0:
            print(f'Could not resolve asset path: {args.parent}')
            sys.exit(1)
        parent = parent_search[0]
        search = list(asset_net.successors(parent))
    else:
        search = list(n for n, d in asset_net.in_degree() if d == 0)
    for alias in args.alias:
        if any(
                alias in asset_net.nodes[n]['alias']
                and all(t in asset_net.nodes[n].get('tag', []) for t in args.tag)
                for n in search):
            print('An item with the same alias and tag combination already exists here, cannot continue')
            sys.exit(1)
    name = make_key(asset_net)
    meta = {'create_time': datetime.now().strftime(('%Y-%m-%d %H:%M:%S'))}
    meta['update_time'] = meta['create_time']
    meta['alias'] = args.alias
    if args.description:
        meta['description'] = args.description
    if args.tag:
        meta['tag'] = args.tag
    if args.item:
        dest_base = \
            Path(asset_net.graph['store'], parent if args.inherit else name)
        path = args.item.resolve()
        meta['item'] = f'{dest_base}{"".join(path.suffixes)}'
        match args.mode:
            case 'copy':
                if path.is_dir():
                    shutil.copytree(path, meta['item'])
                else:
                    shutil.copy2(path, meta['item'])
            case 'move':
                shutil.move(path, meta['item'])
            case 'link':
                os.symlink(path, meta['item'])
        meta['size'] = du(path)
        if args.digest and not path.is_dir():
            meta['md5'] = md5_digest(meta['item'])
    asset_net.add_node(name, **meta)
    if args.parent:
        asset_net.add_edge(parent, name)


def search_nodes(
        asset_net: nx.DiGraph, search: str, ancestors: bool=False,
        descendants: bool=False, fuzzy: bool=True) -> nx.DiGraph:
    ''' Search the asset network by string '''

    if not (search_nodes := set(n for n in resolve_node(asset_net, search))) and fuzzy:
        search_nodes = set(n for n in resolve_node(asset_net, search, True))
    nodes = set()
    if ancestors:
        nodes |= set(
            n for node in search_nodes
            for n in all_predecessors(asset_net, node))
    if descendants:
        nodes |= set(
            n for node in search_nodes
            for n in nx.descendants(asset_net, node))
    return asset_net.subgraph(search_nodes | nodes)


def retrieve_item(asset_net: nx.DiGraph, search: str) -> str:
    ''' Retrieve an item from the asset network '''

    asset_sub_net = search_nodes(asset_net, search, False, False, False)
    if len(asset_sub_net) > 1:
        print(f'Could not resolve asset path uniquely: {search}')
        sys.exit(1)
    if len(asset_sub_net) == 0 \
            or 'item' not in (meta := asset_net.nodes[list(asset_sub_net.nodes)[0]]):
        return ''
    return meta['item']


def del_from_nx(args: Namespace, asset_net: nx.DiGraph) -> None:
    ''' Remove an item from the asset network '''

    asset_sub_net = search_nodes(asset_net, args.search, False, False, False)
    if len(asset_sub_net) > 1:
        print(f'Could not resolve asset path uniquely: {args.search}')
        sys.exit(1)
    if len(asset_sub_net) == 0:
        return
    node = list(asset_sub_net.nodes)[0]
    if asset_net.out_degree(node):
        if not args.recursive:
            print(f'Cannot remove an asset with children unless `--recursive` is specified')
            sys.exit(1)
        asset_net.remove_nodes_from(nx.descendants(asset_net, node))
    asset_net.remove_node(node)


def mod_nx_node(args: Namespace, asset_net: nx.DiGraph) -> None:
    ''' Modify an asset/collection in the asset network '''

    asset_sub_net = search_nodes(asset_net, args.search, False, False, False)
    if len(asset_sub_net) > 1:
        print(f'Could not resolve asset path uniquely: {args.search}')
        sys.exit(1)
    if len(asset_sub_net) == 0:
        return

    node = list(asset_sub_net.nodes)[0]
    meta = asset_net.nodes[node]

    if args.parent:
        parent_search = resolve_node(asset_net, args.parent)
        if len(parent_search) > 1:
            print(f'Could not resolve asset path uniquely: {args.parent}')
            sys.exit(1)
        if len(parent_search) == 0:
            print(f'Could not resolve asset path: {args.parent}')
            sys.exit(1)
        parent = parent_search[0]
        search = [n for n in asset_net.successors(parent) if n != node]
        for p in list(asset_net.predecessors(node)):
            asset_net.remove_edge(p, node)
        asset_net.add_edge(parent, node)
    elif (parent := list(asset_net.predecessors(node))):
        parent = parent[0]
        search = [n for n in asset_net.successors(parent) if n != node]
    else:
        if args.inherit:
            print(f'Cannot `--inherit` without a parent')
        search = list(n for n, d in asset_net.in_degree() if d == 0)

    if args.alias or args.tag:
        aliases = args.alias if args.alias else meta['alias']
        tags = args.tag if args.tag else meta.get('tag', [])
        for alias in aliases:
            if any(
                    alias in asset_net.nodes[n]['alias']
                    and all(t in asset_net.nodes[n].get('tag', []) for t in tags)
                    for n in search):
                print('An item with the same alias and tag combination already exists here, cannot continue')
                sys.exit(1)
        meta['alias'] = aliases
        if tags:
            meta['tag'] = tags

    meta['update_time'] = datetime.now().strftime(('%Y-%m-%d %H:%M:%S'))

    if args.description:
        meta['description'] = args.description

    if args.item:
        if 'item' in meta:
            if (path := Path(meta['item'])).is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        dest_base = \
            Path(asset_net.graph['store'], parent if args.inherit else node).resolve()
        path = args.item.resolve()
        meta['item'] = f'{dest_base}{"".join(path.suffixes)}'
        match args.mode:
            case 'copy':
                if path.is_dir():
                    shutil.copytree(path, meta['item'])
                else:
                    shutil.copy2(path, meta['item'])
            case 'move':
                shutil.move(path, meta['item'])
            case 'link':
                os.symlink(path, meta['item'])
        meta['size'] = du(path)
        if args.digest and not path.is_dir():
            meta['md5'] = md5_digest(meta['item'])
