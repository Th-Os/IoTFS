from argparse import ArgumentParser
import json
import os

from corefs.core import CoreFS
from corefs.filesystem.standard_fs import StandardFileSystem


def parse_args():
    '''Parse command line'''

    parser = ArgumentParser()

    parser.add_argument('mountpoint', type=str,
                        help='Where to mount the file system')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debugging output')
    return parser.parse_args()


def main():
    options = parse_args()
    fd = os.open("./structure.json", os.O_RDONLY)
    structure = json.load(fd)
    os.close(fd)
    fs = StandardFileSystem(
        options.mountpoint, structure_json=structure, debug=options.debug)

    CoreFS(fs, debug=options.debug)


if __name__ == "__main__":
    main()
