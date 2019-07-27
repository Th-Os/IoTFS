#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''

'''

import trio
import pyfuse3
import errno
import logging
import stat
import time
from argparse import ArgumentParser
import os
import sys
from collections import defaultdict

from pyfuse3 import FUSEError

try:
    import faulthandler
except ImportError:
    pass
else:
    faulthandler.enable()

log = logging.getLogger(__name__)


class TestFs(pyfuse3.Operations):

    supports_dot_lookup = True
    enable_writeback_cache = True

    def __init__(self):
        super(TestFs, self).__init__()
        # self.files = dict({
        #    pyfuse3.ROOT_INODE+1: dict({"name": b"a_name", "data": b"a_data", "type": "file", "path": "./"}),
        #    pyfuse3.ROOT_INODE+2: dict({"name": b"message", "data": b"hello world\n", "type": "file", "path": "./"})
        # })
        self.files = dict()
        self._lookup_cnt = defaultdict(lambda: 0)
        self._fd_inode_map = dict()
        self._inode_fd_map = dict()
        self._fd_open_count = dict()

    def _inode_to_path(self, inode):
        try:
            node = self.files[inode]
            path = node["path"] + node["name"].decode("utf-8")
        except KeyError:
            raise FUSEError(errno.ENOENT)
        log.info("Inode to Path: " + path)
        return path

    def _add_inode(self, path, node_type="file", data=None):
        log.info('_add_node for %s', path)
        if len(self.files) == 0:
            inode = pyfuse3.ROOT_INODE + 1
        else:
            inode = list(self.files.keys())[-1] + 1
        self._add_path(inode, path, node_type, data)
        return inode

    def _add_path(self, inode, path, node_type, data=None):
        log.info('_add_path for %d, %s', inode, path)
        self._lookup_cnt[inode] += 1

        # With hardlinks, one inode may map to multiple paths.
        if inode not in self.files and inode is not pyfuse3.ROOT_INODE:
            log.info("Found no inode")
            log.info("Create: inode %d, with path: %s", inode, path)
            name = path.split(os.path.sep)[-1]
            path = path[:-len(name)]
            log.info("name: %s, path: %s", name, path)
            if node_type == "file" and data is None:
                data = "No data.\n"
            if type(data) is str:
                data = data.encode("utf-8")
            if type(name) is str:
                name = name.encode("utf-8")
            self.files[inode] = dict(
                {"name": name, "path": path, "data": data, "type": node_type})
            log.info(self.files)
            return

        # TODO: Implement Change Path
        """
        val = self.files[inode]
        if isinstance(val, set):
            val.add(path)
        elif val != path:
            self.files[inode] = {path, val}
        """

    def __get_path(self, parent_inode, name):
        if type(name) is not str:
            name = name.decode("utf-8")
        else:
            log.info("Path is already encoded in utf-8")
        try:
            if parent_inode == pyfuse3.ROOT_INODE:
                path = os.path.join(".", name)
                log.info("new path: %s", path)
            else:
                node = self.files[parent_inode]
                path = node["path"] + \
                    os.path.join(node["name"].decode(
                        "utf-8"), name)
                log.info("new path: %s", path)
            return path
        except:
            raise Exception("Failed getting path.")

    def __get_node_by_name(self, name):
        log.info("get node by name: %s", name)
        if type(name) is str:
            name = name.encode("utf-8")
        for idx in self.files:
            if self.files[idx]["name"] == name:
                return self.files[idx]
        raise Exception("Found no node for name %s", name)

    def __get_index_by_name(self, name):
        log.info("get node by name: %s", name)
        if type(name) is str:
            name = name.encode("utf-8")
        for idx in self.files:
            if self.files[idx]["name"] == name:
                return idx
        raise Exception("Found no node for name %s", name)

    def _getattr(self, inode):
        '''
            dev_t     st_dev;         /* ID of device containing file */
            ino_t     st_ino;         /* Inode number */
            mode_t    st_mode;        /* File type and mode */
            nlink_t   st_nlink;       /* Number of hard links */
            uid_t     st_uid;         /* User ID of owner */
            gid_t     st_gid;         /* Group ID of owner */
            dev_t     st_rdev;        /* Device ID (if special file) */
            off_t     st_size;        /* Total size, in bytes */
            blksize_t st_blksize;     /* Block size for filesystem I/O */
            blkcnt_t  st_blocks;      /* Number of 512B blocks allocated */

            /* Since Linux 2.6, the kernel supports nanosecond
                precision for the following timestamp fields.
                For the details before Linux 2.6, see NOTES. */

            struct timespec st_atim;  /* Time of last access */
            struct timespec st_mtim;  /* Time of last modification */
            struct timespec st_ctim;  /* Time of last status change */
        '''
        entry = pyfuse3.EntryAttributes()
        node = None
        # TODO: Hier ist das Problem: eigentlich sollte 4 kein attribut haben!
        if inode in self.files and "attr" in self.files[inode]:
            log.info("inode: %d, st_ino: %d", inode,
                     self.files[inode]["attr"].st_ino)
        if inode in self.files and "attr" in self.files[inode] and self.files[inode]["attr"].st_ino != 0:
            log.info("inode %d has attribute", inode)
            return self.files[inode]["attr"]
        elif inode == pyfuse3.ROOT_INODE:
            log.info("root inode")
            entry.st_mode = (stat.S_IFDIR | 0o755)
            entry.st_size = 0
        else:
            try:
                log.info("new inode: %d", inode)
                node = self.files[inode]
                if node["name"].decode("utf-8").endswith(".swp"):
                    node["type"] = "swp"
                if node["type"] == "dir":
                    entry.st_mode = (stat.S_IFDIR | 0o755)
                    entry.st_size = 0
                elif node["type"] == "swp":
                    log.info("its a swap FILE !!!")
                    entry.st_mode = (stat.S_IFREG | 0o666)
                    entry.st_size = len(node["data"])
                else:
                    entry.st_mode = (stat.S_IFREG | 0o666)
                    entry.st_size = len(node["data"])
            except:
                raise FUSEError(errno.ENOENT)

        # current time in nanoseconds
        stamp = int(time.time() * 1e9)
        entry.st_atime_ns = stamp
        entry.st_ctime_ns = stamp
        entry.st_mtime_ns = stamp
        entry.st_gid = os.getgid()
        entry.st_uid = os.getuid()
        entry.st_ino = inode

        # if new node -> add attr field with entry
        if node is not None:
            self.files[inode]["attr"] = entry
        return entry

    async def getattr(self, inode, ctx=None):
        log.info("----")
        log.info("getattr: %i", inode)
        log.info("----")
        return self._getattr(inode)

    async def lookup(self, parent_inode, name, ctx=None):
        log.info("----")
        log.info("lookup: %s", name)
        log.info("----")

        # TODO: parent_inode save in dict and evaluate here
        log.info("Parent Inode: %i", parent_inode)
        name = name.decode("utf-8")
        log.info("Name: %s", name)
        log.info("swp? %s", name[-4:])
        if name[-4:] == ".swp":
            self._add_inode(self.__get_path(parent_inode, name),
                            self.__get_node_by_name(name[1:-4])["data"])
            log.info("Found .swp")

            # This was needed for finding the non swp file.
            # name = name[1:-4]
            # log.info("New name: %s", name)
        for key, node in self.files.items():
            if node["name"] == name.encode("utf-8"):
                log.info("FOUND")
                return self._getattr(key)
        # If no . and .. -> no existing inode -> create new one
        # if name != '.' and name != '..':
            # return self._getattr(self._add_inode(self.__get_path(parent_inode, name.encode("utf-8"))))
        # new error
        # raise Exception("Lookup failed.")
        # raise pyfuse3.FUSEError(errno.ENOENT)

        # If no node is found
        attr = pyfuse3.EntryAttributes()
        attr.st_ino = 0
        return attr

    async def mkdir(self, parent_inode, name, mode, ctx):
        log.info("----")
        log.info("mkdir: %s", name)
        log.info("----")
        return self._getattr(self._add_inode(self.__get_path(parent_inode, name), node_type="dir"))
        """
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        try:
            os.mkdir(path, mode=(mode & ~ctx.umask))
            os.chown(path, ctx.uid, ctx.gid)
        except OSError as exc:
            raise FUSEError(exc.errno)
        attr = self._getattr(path=path)
        self._add_path(attr.st_ino, path)
        return attr
        """

    async def opendir(self, inode, ctx):
        log.info("----")
        log.info("opendir: %d", inode)
        log.info("----")
        return inode

    async def readdir(self, inode, start_id, token):
        log.info("----")
        log.info("readdir: %d", inode)
        log.info("----")
        log.info(start_id)
        if inode == pyfuse3.ROOT_INODE:
            dir_path = "./"
        else:
            dir_path = self._inode_to_path(inode) + "/"
        log.info("dirpath: %s", dir_path)
        arr = {k: v for k, v in self.files.items() if v["path"] == dir_path}
        log.info("items in dir: %d", len(arr))
        for key, value in arr.items():
            log.info("Key: %s, Value_name: %s", key, value["name"])
            if key <= start_id:
                continue
            if value["type"] == "swp":
                log.info("swp: %s", value["name"])
                continue
            if not pyfuse3.readdir_reply(token, value["name"], await self.getattr(key), key):
                break
        return

    async def open(self, inode, flags, ctx):
        log.info("----")
        log.info("open: %d", inode)
        log.info("----")
        """
        if inode in self._inode_fd_map:
            fd = self._inode_fd_map[inode]
            self._fd_open_count[fd] += 1
            return fd
        assert flags & os.O_CREAT == 0
        try:
            fd = os.open(self._inode_to_path(inode), flags)
        except OSError as exc:
            raise FUSEError(exc.errno)
        self._inode_fd_map[inode] = fd
        self._fd_inode_map[fd] = inode
        self._fd_open_count[fd] = 1
        return fd
        """
        # if flags & os.O_RDWR or flags & os.O_WRONLY:
        #    raise pyfuse3.FUSEError(errno.EPERM)
        return inode

    async def read(self, inode, off, size):
        log.info("----")
        log.info("read: %d", inode)
        log.info("----")
        log.info(self.files[inode]["data"][off: off+size])
        return self.files[inode]["data"][off: off+size]

    # TODO: implement mode and flags
    async def create(self, parent_inode, name, mode, flags, ctx):
        log.info("----")
        log.info("create: %s", name)
        log.info("----")
        '''Create a file with permissions *mode* and open it with *flags*
        *ctx* will be a `RequestContext` instance.
        The method must return a tuple of the form *(fh, attr)*, where *fh* is a
        file handle like the one returned by `open` and *attr* is an
        `EntryAttributes` instance with the attributes of the newly created
        directory entry.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
        '''
        inode = self._add_inode(self.__get_path(parent_inode, name))
        attr = self._getattr(inode)

        """
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        try:
            fd = os.open(path, flags | os.O_CREAT | os.O_TRUNC)
        except OSError as exc:
            raise FUSEError(exc.errno)
        attr = self._getattr(fd=fd)
        self._add_path(attr.st_ino, path)
        self._inode_fd_map[attr.st_ino] = fd
        self._fd_inode_map[fd] = attr.st_ino
        self._fd_open_count[fd] = 1
        return (fd, attr)
        """

        return (inode, attr)

    async def release(self, inode):
        log.info("----")
        log.info("release: %s", inode)
        log.info("----")
        '''Release open file
        This method will be called when the last file descriptor of *fh* has
        been closed, i.e. when the file is no longer opened by any client
        process.
        *fh* will by an integer filehandle returned by a prior `open` or
        `create` call. Once `release` has been called, no future requests for
        *fh* will be received (until the value is re-used in the return value of
        another `open` or `create` call).
        This method may return an error by raising `FUSEError`, but the error
        will be discarded because there is no corresponding client request.
        '''
        """
        if self._fd_open_count[fd] > 1:
            self._fd_open_count[fd] -= 1
            return

        del self._fd_open_count[fd]
        inode = self._fd_inode_map[fd]
        del self._inode_fd_map[inode]
        del self._fd_inode_map[fd]
        try:
            os.close(fd)
        except OSError as exc:
            raise FUSEError(exc.errno)
        """
        pass

    async def releasedir(self, inode):
        log.info("----")
        log.info("releasedir: %d", inode)
        log.info("----")
        '''Release open directory
        This method will be called exactly once for each `opendir` call. After
        *fh* has been released, no further `readdir` requests will be received
        for it (until it is opened again with `opendir`).
        '''

        pass

    async def setattr(self, inode, attr, fields, fh, ctx):
        log.info("----")
        log.info("setattr: %d", inode)
        log.info("----")
        '''Change attributes of *inode*
        *fields* will be an `SetattrFields` instance that specifies which
        attributes are to be updated. *attr* will be an `EntryAttributes`
        instance for *inode* that contains the new values for changed
        attributes, and undefined values for all other attributes.
        Most file systems will additionally set the
        `~EntryAttributes.st_ctime_ns` attribute to the current time (to
        indicate that the inode metadata was changed).
        If the syscall that is being processed received a file descriptor
        argument (like e.g. :manpage:`ftruncate(2)` or :manpage:`fchmod(2)`),
        *fh* will be the file handle returned by the corresponding call to the
        `open` handler. If the syscall was path based (like
        e.g. :manpage:`truncate(2)` or :manpage:`chmod(2)`), *fh* will be
        `None`.
        *ctx* will be a `RequestContext` instance.
        The method should return an `EntryAttributes` instance (containing both
        the changed and unchanged values).
        '''

        new_attr = self.files[inode]["attr"]

        try:
            if fields.update_size:
                new_attr.st_size = attr.st_size

            if fields.update_mode:
                new_attr.st_mode = attr.st_mode

            if fields.update_uid:
                new_attr.st_uid = attr.st_uid

            if fields.update_gid:
                new_attr.st_gid = attr.st_gid

            if fields.update_atime:
                new_attr.st_atime_ns = attr.st_atime_ns
            if fields.update_mtime:
                new_attr.st_mtime_ns = attr.st_mtime_ns

            new_attr.st_ctime_ns = int(time.time() * 1e9)
            self.files[inode]["attr"] = new_attr

        except OSError as exc:
            raise FUSEError(exc.errno)

        return await self.getattr(inode)

    async def unlink(self, parent_inode, name, ctx):
        log.info("----")
        log.info("unlink: %s", name)
        log.info("----")
        '''Remove a (possibly special) file
            This method must remove the (special or regular) file *name* from the
            direcory with inode *parent_inode*.  *ctx* will be a `RequestContext`
            instance.
            If the inode associated with *file* (i.e., not the *parent_inode*) has a
            non-zero lookup count, or if there are still other directory entries
            referring to this inode (due to hardlinks), the file system must remove
            only the directory entry (so that future calls to `readdir` for
            *parent_inode* will no longer include *name*, but e.g. calls to
            `getattr` for *file*'s inode still succeed). (Potential) removal of the
            associated inode with the file contents and metadata must be deferred to
            the `forget` method to be carried out when the lookup count reaches zero
            (and of course only if at that point there are no more directory entries
            associated with the inode either).
            '''

        idx = self.__get_index_by_name(name)
        log.info("inode: %d", idx)
        del self.files[idx]

    async def flush(self, inode):
        log.info("----")
        log.info("flush: %d", inode)
        log.info("----")


def init_logging(debug=False):
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(threadName)s: '
                                  '[%(name)s] %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler("fuse3.log")  # logging.StreamHandler()

    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    if debug:
        handler.setLevel(logging.DEBUG)
        root_logger.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)
        root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)


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
    init_logging(options.debug)

    testfs = TestFs()
    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('fsname=iotfs')
    if options.debug_fuse:
        fuse_options.add('debug')
    pyfuse3.init(testfs, options.mountpoint, fuse_options)
    try:
        trio.run(pyfuse3.main)
    except:
        pyfuse3.close(unmount=False)
        raise

    pyfuse3.close()


if __name__ == '__main__':
    main()
