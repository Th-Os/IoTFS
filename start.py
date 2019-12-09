from argparse import ArgumentParser

from corefs.core import CoreFS
from corefs.filesystem.standard_fs import StandardFileSystem

'''
This file is needed to start corefs in this package for testing purpose.
'''


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
    fs = StandardFileSystem(options.mountpoint, debug=options.debug)
    CoreFS(fs, debug=options.debug)


if __name__ == "__main__":
    main()
