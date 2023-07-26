from asset.helpers import convert_size

import networkx as nx
from rich.tree import Tree


def display_tree(asset_net: nx.DiGraph, detail: bool=False) -> Tree:
    ''' Render an asset network as a tree '''

    def _add_to_tree(node: str, text:str) -> None:
        if (parent := list(asset_net.predecessors(node))):
            tree_nodes[node] = tree_nodes[parent[0]].add(text)
        else:
            tree_nodes[node] = tree.add(text)

    tree = Tree(asset_net.graph['path'])
    tree_nodes = {}

    for node in nx.topological_sort(asset_net):
        meta = asset_net.nodes[node]
        tag_text = ''
        if (tags := meta.get('tag', [])):
            tag_text = \
                f':[cyan]' \
                f'{"[/cyan]:[cyan]".join(tags)}' \
                f'[/cyan]'
        text_format = 'bright_magenta' if 'item' in meta else 'dark_orange'
        text = \
            f'[{text_format}]' \
            f'{f"[/{text_format}]|[{text_format}]".join(meta["alias"])}' \
            f'[/{text_format}]' \
            + tag_text
        if detail:
            if (description := meta.get('description', '')):
                text += f'\n{description}'
            if 'item' in meta:
                if (cli := meta.get('cli', '')):
                    text += f'\n[bright_black][{cli}][/bright_black]'
                text += \
                    f'\n[bright_black]created={meta["create_time"]}' \
                    f'\tupdated={meta["update_time"]}'
                if (size := meta.get('size', '')):
                    text += f'\nsize={convert_size(meta["size"])}'
                text += f'''\t{f"md5={meta['md5']}" if "md5" in meta else ""}[/bright_black]'''
        _add_to_tree(node, text)
    return tree
