from argparse import ArgumentParser

from iotfs.main import IoTFS
from iotfs.filesystem.standard_fs import StandardFileSystem

'''
This file is needed to start IoTFS in this package for testing purpose.
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
    IoTFS(fs, debug=options.debug)


if __name__ == "__main__":
    main()
