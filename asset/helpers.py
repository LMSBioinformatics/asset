
from hashlib import md5
import math
from pathlib import Path
from random import randrange
import sys

import networkx as nx


def md5_digest(path: Path) -> str:
    ''' Generate the md5 digest for a file '''

    digest = md5()
    with open(path, 'rb') as F:
        for chunk in iter(lambda: F.read(4096), b''):
            digest.update(chunk)
    return digest.hexdigest()


def make_key(asset_net: [nx.DiGraph | None]=None) -> str:
    ''' Generate a random id '''

    k = '{:08x}'.format(randrange(16**8))
    if asset_net:
        while k in asset_net.nodes:
            k = '{:08x}'.format(randrange(16**8))
    return k


def convert_size(size_bytes: int) -> str:
    ''' Convert bytes into a human-readable format '''

    if size_bytes == 0:
        return '0 B'

    size_precis = {0:0, 1:0, 2:0, 3:1, 4:2, 5:2, 6:2, 7:2, 8:2}
    size_string = {0:'B', 1:'KB', 2:'MB', 3:'GB', 4:'TB', 5:'PB', 6:'EB', 7:'ZB', 8:'YB'}

    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    return f'{size_bytes / p:.{size_precis[i]}f} {size_string[i]}'


def dir_exists_or_create(path: Path, mkdir: bool=False) -> None:
    ''' Check if a directory exist, make it if requested '''

    if (path := path.resolve()).is_dir():
        return
    if mkdir:
        path.mkdir(parents=True, exist_ok=True)
    else:
        print(f'Directory {path} does not exist, cannot continue unless instructed')
        sys.exit(1)


def file_exists_or_creatable(path: Path, mkdir: bool=False, force: bool=False) -> None:
    ''' Check if a file exists and whether it can be created '''

    path = path.resolve()
    dir_exists_or_create(path.parent, mkdir)
    if path.exists() and not force:
        print(f'File {path} exists, cannot continue unless instructed')
        sys.exit(1)


def du(path: Path) -> int:
    ''' Return the size of a file or directory (recursive) '''

    return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
