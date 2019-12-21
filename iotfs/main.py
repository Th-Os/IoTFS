#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from argparse import ArgumentParser
import concurrent.futures
import os
from queue import Queue

from iotfs.filesystem.fs import FileSystemStarter, FileSystem
from iotfs.filesystem.standard_fs import StandardFileSystem
from iotfs.filesystem.producer_fs import ProducerFileSystem

from iotfs.utils import _logging


class IoTFS():

    """
    iotfs initiates a FUSE filesystem with the given attributes.

    ...

    Attributes
    ----------
    fs : iotfs.filesystem.fs.FileSystem
        a filesystem object inheriting from FileSystem
    adapters : list
        input adapters inheriting iotfs.input._adapter.Adapter that define the way data flows into the filesystem
    listeners : list
        listeners inheriting iotfs.input._listener.Listener that define listening processes
    debug : bool, optional
        this defines whether the logging output should include the debug level

    """

    def __init__(self, fs, listeners=[], debug=False):
        """
        Parameters
        ----------
        fs : iotfs.filesystem.fs.FileSystem
            a filesystem object inheriting from FileSystem
        adapters : list
            input adapters inheriting iotfs.input._adapter.Adapter that define the way data flows into the filesystem
        listeners : list
            listeners inheriting iotfs.input._listener.Listener that define listening processes
        debug : bool, optional
            this defines whether the logging output should include the debug level
        """

        log = _logging.create_logger(debug=debug)
        log.info("Starting application.")
        os.environ["MOUNT_POINT"] = os.path.abspath(fs.mount_point)
        if fs is None or not isinstance(fs, FileSystem):
            raise ValueError("No valid filesystem provided.")
        if len(listeners) > 0 and isinstance(fs, ProducerFileSystem):
            queue = Queue(0)
            fs.setQueue(queue)
            for listener in listeners:
                listener.setQueue(queue)
        try:
            if not os.path.isdir(fs.mount_point):
                log.warning("Creating mountpoint: %s", fs.mount_point)
                os.mkdir(fs.mount_point)
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(listeners) + 1) as executor:
                executor.submit(FileSystemStarter(fs).start)
                for listener in listeners:
                    executor.submit(listener.start)

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

    fs = StandardFileSystem(options.mountpoint, debug=options.debug)

    IoTFS(fs, debug=options.debug)


if __name__ == "__main__":
    main()
