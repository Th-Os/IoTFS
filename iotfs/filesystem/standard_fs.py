# -*- coding: utf-8 -*-

from iotfs.filesystem.fs import FileSystem


class StandardFileSystem(FileSystem):

    """
    StandardFileSystem is a pyfuse3 implementation and implements all file system operations.
    All functions are commented with information provided by the pyfuse3 (https://www.github.com/libfuse/pyfuse3)
    project.

    ...

    Attributes
    ----------
    mount_point : str
        a mounting point for the filesystem.
    debug : bool, optional
        this defines whether the logging output should include the debug level

    """

    def __init__(self, mount_point, debug=False):
        """
        Parameters
        ----------
        mount_point : str
            a mounting point for the filesystem.
        debug : bool, optional
            this defines whether the logging output should include the debug level
        """
        super().__init__(mount_point, debug)
