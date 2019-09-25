#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyfuse3
from pyfuse3 import FUSEError
import logging
import trio

import utils
from filesystem._fs import _FileSystem

# Observer Pattern with signals and not over this. This could result in problems between threads and trio


class FileSystem(_FileSystem):

    def __init__(self, mount_point, debug):
        super().__init__(mount_point, debug)
        self.observers = []

    def register(self, connector):
        self.observers.append(connector)

    def notify(self, message):
        for observer in self.observers:
            observer.update(message)

    def deregister(self, connector):
        if connector in self.observers:
            self.observers.remove(connector)

    def __add_inode(self, name, parent_inode, node_type, data):
        super().__add_inode(name, parent_inode, node_type, data)
        self.notify("Added inode with name {}".format(name))


class FileSystemStarter():

    def __init__(self, mount_point, name="iotfs", debug=False, debug_fuse=False):
        self.mount_point = mount_point
        self.fs = FileSystem(mount_point, debug)
        self.name = name
        self.debug = debug
        self.debug_fuse = debug_fuse

    def start(self):
        fuse_log = utils.init_logging("pyfuse3", self.debug_fuse)
        fuse_options = set(pyfuse3.default_options)
        fuse_options.add('fsname=' + self.name)
        if self.debug_fuse:
            fuse_options.add('debug')
        pyfuse3.init(self.fs, self.mount_point, fuse_options)
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
