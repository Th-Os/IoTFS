from argparse import ArgumentParser
import concurrent.futures
import os

from filesystem.fs import FileSystemStarter, FileSystem
from filesystem.standard_fs import StandardFileSystem

from utils import _logging


class CoreFS():

    def __init__(self, mountpoint, fs=None, adapters=[], connectors=[], debug=False):
        log = _logging.create_logger(debug=debug)
        log.info("Starting application.")
        os.environ["MOUNT_POINT"] = os.path.abspath(mountpoint)

        if fs is None or not isinstance(fs, FileSystem):
            fs = StandardFileSystem(mountpoint, debug)
        try:
            if not os.path.isdir(mountpoint):
                os.mkdir(mountpoint)
            FileSystemStarter(fs).start()
            '''
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(adapters) + 1) as executor:
                executor.submit(FileSystemStarter(fs).start)
                for adapter in adapters:
                    executor.submit(adapter.start)
            '''
        except (BaseException, Exception) as e:
            log.error(e)


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
    CoreFS(options.mountpoint, debug=options.debug)


if __name__ == "__main__":
    main()
