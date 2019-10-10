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
        super().__init__(mount_point, debug)
        self.debug = debug
        self.mount_point = mount_point

    async def create(self, parent_inode, name, mode, flags, ctx):
        return await super().create(parent_inode, name, mode, flags, ctx)

    async def mknod(self, parent_inode, name, mode, rdev, ctx):
        return await super().mknod(parent_inode, name, mode, rdev, ctx)

    async def mkdir(self, parent_inode, name, mode, ctx):
        return await super().mkdir(parent_inode, name, mode, ctx)

    async def read(self, inode, off, size):
        return await super().read(inode, off, size)

    async def readdir(self, inode, start_id, token):
        return await super().readdir(inode, start_id, token)

    async def write(self, inode, off, buf):
        return await super().write(inode, off, buf)

    async def rename(self, parent_inode_old, name_old, parent_inode_new, name_new, flags, ctx):
        return await super().rename(parent_inode_old, name_old, parent_inode_new, name_new, flags, ctx)

    async def unlink(self, parent_inode, name, ctx):
        return await super().unlink(parent_inode, name, ctx)

    async def rmdir(self, parent_inode, name, ctx):
        return await super().rmdir(parent_inode, name, ctx)


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
