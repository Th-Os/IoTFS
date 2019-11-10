import concurrent.futures
import os
from queue import Queue

from corefs.filesystem.fs import FileSystemStarter, FileSystem
from corefs.filesystem.producer_fs import ProducerFileSystem

from corefs.utils import _logging


class CoreFS():

    """
    CoreFS initiates a FUSE filesystem with the given attributes.

    ...

    Attributes
    ----------
    fs : corefs.filesystem.fs.FileSystem
        a filesystem object inheriting from FileSystem
    adapters : list
        input adapters inheriting corefs.input._adapter.Adapter that define the way data flows into the filesystem
    listeners : list
        listeners inheriting corefs.input._listener.Listener that define listening processes
    debug : bool, optional
        this defines whether the logging output should include the debug level

    """

    def __init__(self, fs, adapters=[], listeners=[], debug=False):
        """
        Parameters
        ----------
        fs : corefs.filesystem.fs.FileSystem
            a filesystem object inheriting from FileSystem
        adapters : list
            input adapters inheriting corefs.input._adapter.Adapter that define the way data flows into the filesystem
        listeners : list
            listeners inheriting corefs.input._listener.Listener that define listening processes
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
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(adapters) + len(listeners) + 1) as executor:
                executor.submit(FileSystemStarter(fs).start)
                for adapter in adapters:
                    executor.submit(adapter.start)
                for listener in listeners:
                    executor.submit(listener.start)

        except (BaseException, Exception) as e:
            log.error(e)
