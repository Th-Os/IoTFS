from argparse import ArgumentParser
import fs

def parse_args():
    '''Parse command line'''

    parser = ArgumentParser()

    parser.add_argument('mountpoint', type=str,
                        help='Where to mount the file system')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debugging output')
    parser.add_argument('--debug-fuse', action='store_true', default=False,
                        help='Enable FUSE debugging output')
    return parser.parse_args()

def main():
    options = parse_args()
    fs.start(options.mountpoint, options.debug, options.debug_fuse)

if __name__ == "__main__":
    main()