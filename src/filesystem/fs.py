#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyfuse3
from pyfuse3 import FUSEError
import trio

import utils
from filesystem._fs import _FileSystem

# Observer Pattern with signals and not over this. This could result in problems between threads and trio


class FileSystem(_FileSystem):

    def __init__(self, mount_point, debug=False):
        super().__init__(mount_point, debug)
        self.debug = debug
        self.mount_point = mount_point


class FileSystemStarter():

    def __init__(self, fs):
        self.log = utils.init_logging(self.__class__.__name__)
        if not isinstance(fs, FileSystem):
            self.log.error("Parameter is no Filesystem.")
        self.fs = fs

    def start(self):
        fuse_log = utils.init_logging("pyfuse3", self.fs.debug)
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
