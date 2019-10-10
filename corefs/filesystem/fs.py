#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyfuse3
from pyfuse3 import FUSEError
import trio

from filesystem._fs import _FileSystem

from utils import _logging

# This could result in events for the connector.listener
# TODO: Producer & Consumer Pattern with Queue


class FileSystem(_FileSystem):

    def __init__(self, mount_point, debug=False):
        self.logger = _logging.create_logger("FileSystem")
        self.logger.info("Hello FileSystem")
        super(FileSystem, self).__init__(mount_point, debug)
        self.debug = debug
        self.mount_point = mount_point

    async def open(self, inode, flags, ctx):
        self.logger.warning("hello open call")
        super().open(inode, flags, ctx)
        self.logger.error("opened inode %d", inode)

    async def create(self, parent_inode, name, mode, flags, ctx):
        self.logger.warning("hello create call")
        super().create(parent_inode, name, mode, flags, ctx)
        self.logger.error("created %s", name)

    async def opendir(self, inode, ctx):
        self.logger.warning("hello opendir call!!!")
        return await super().opendir(inode, ctx)


class FileSystemStarter():

    def __init__(self, fs):
        self.log = _logging.create_logger(self.__class__.__name__)
        if not isinstance(fs, FileSystem):
            self.log.error("Parameter is no Filesystem.")
        self.fs = fs

    def start(self):
        fuse_log = _logging.create_logger("pyfuse3", self.fs.debug)
        fuse_options = set(pyfuse3.default_options)
        fuse_options.add('fsname=' + self.fs.__class__.__name__)
        if self.fs.debug:
            fuse_options.add('debug')
        pyfuse3.init(self.fs, self.fs.mount_point, fuse_options)
        try:
            trio.run(pyfuse3.main)
        except FUSEError:
            fuse_log.warning("FUSEError occured")
            pyfuse3.close(unmount=False)
        except BaseException as be:
            fuse_log.warning(be.args)
            fuse_log.warning("BaseException occured")
            pyfuse3.close(unmount=False)
        except Exception as e:
            fuse_log.warning(e.args)
            fuse_log.warning("Exception occured")
            pyfuse3.close(unmount=False)
        finally:
            pyfuse3.close()
