from argparse import ArgumentParser
import concurrent.futures
import os
from queue import Queue

from corefs.filesystem.fs import FileSystemStarter, FileSystem
#from corefs.filesystem.standard_fs import StandardFileSystem
from corefs.filesystem.producer_fs import ProducerFilesystem
from corefs.connector._listener import Listener

from corefs.utils import _logging


class CoreFS():

    def __init__(self, mountpoint, fs=None, adapters=[], connectors=[], debug=False):
        log = _logging.create_logger(debug=debug)
        log.info("Starting application.")
        os.environ["MOUNT_POINT"] = os.path.abspath(mountpoint)
        queue = Queue(0)
        if fs is None or not isinstance(fs, FileSystem):
            fs = ProducerFilesystem(mountpoint, queue, debug=debug)
        try:
            if not os.path.isdir(mountpoint):
                os.mkdir(mountpoint)
            # FileSystemStarter(fs).start()
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(adapters) + 2) as executor:
                executor.submit(FileSystemStarter(fs).start)
                executor.submit(Listener(queue).start)
                for adapter in adapters:
                    executor.submit(adapter.start)
        except (BaseException, Exception) as e:
            log.error(e)
