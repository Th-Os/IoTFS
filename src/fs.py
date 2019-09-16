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
import os
from collections import defaultdict

from pyfuse3 import FUSEError

try:
    import faulthandler
except ImportError:
    pass
else:
    faulthandler.enable()

from node import File, Directory, DIR_TYPE, SWAP_TYPE, FILE_TYPE, UTF_8_ENCODING, BYTE_ENCODING
import utils


class TestFs(pyfuse3.Operations):

    supports_dot_lookup = True
    enable_writeback_cache = True

    def __init__(self, mount_point, debug=False):
        super(TestFs, self).__init__()
        self.log = utils.init_logging(self.__class__.__name__, debug)
        self.log.info("Init %s", self.__class__.__name__)
        self.nodes = dict()
        self.nodes[pyfuse3.ROOT_INODE] = Directory("root", os.path.abspath(mount_point), root=True)

        self.log.debug("Size of nodes: %d", len(self.nodes))
        # reimplement this into node.py
        self._lookup_cnt = defaultdict(lambda: 0)
        self._fd_inode_map = dict()
        self._inode_fd_map = dict()
        self._fd_open_count = dict()

    def __add_inode(self, name, path, node_type=FILE_TYPE, data=""):
        self.log.info('__add_inode for %s', path)
        '''
        if len(self.nodes) == 0:
            inode = pyfuse3.ROOT_INODE + 1
        else:
        '''
        inode = list(self.nodes.keys())[-1] + 1

        self._lookup_cnt[inode] += 1

        # With hardlinks, one inode may map to multiple paths.
        if inode not in self.nodes and inode is not pyfuse3.ROOT_INODE:
            self.log.debug("Found no inode")
            self.log.debug("Create: inode %d, with path: %s, and name: %s", inode, path, name)
            if node_type == FILE_TYPE or node_type == SWAP_TYPE:
                self.nodes[inode] = File(name, path, data)
            else:
                self.nodes[inode] = Directory(name, path)
            self.log.debug(self.nodes)
        return inode

    def __get_path(self, parent_inode, name):
        self.log.debug("__get_path for inode with name %s", name)
        if type(name) is not str:
            name = name.decode("utf-8")
        else:
            self.log.debug("node name is already encoded in utf-8")
        try:
            if parent_inode == pyfuse3.ROOT_INODE:
                path = os.path.join(self.nodes[parent_inode].get_path(), name)
                self.log.info("new path: %s", path)
            else:
                node = self.nodes[parent_inode]
                path = node["path"] + \
                    os.path.join(node["name"].decode(
                        "utf-8"), name)
                self.log.info("new path: %s", path)
            return path
        except Exception as e:
            self.log.error(e.msg)

    # Needs some refactoring... Is this even needed?
    def __get_path_inode(self, inode):
        self.log.debug("Get Path by Inode: %d", inode)
        self.log.debug("Is inode in files? %s", (inode in self.nodes))
        if inode == pyfuse3.ROOT_INODE:
            return "."
        if inode not in self.nodes:
            # This could be an error.
            return self.__get_path_inode(pyfuse3.ROOT_INODE)
        try:
            path = self.nodes[inode].get_full_path() + os.path.sep
        except Exception as e:
            self.log.error(e)
            raise Exception(
                "Failed to combine path and node of inode %d" % inode)
        self.log.debug("Result path: %s", path)
        return path

    def __get_node_by_name(self, name):
        self.log.info("get node by name: %s", name)
        for idx in self.nodes:
            self.log.debug(idx)
            self.log.debug("check %s vs %s", self.nodes[idx].get_name(encoding=UTF_8_ENCODING), name)
            if self.nodes[idx].get_name(encoding=UTF_8_ENCODING) == name:
                return self.nodes[idx]
            self.log.debug("failed")
        # nano for new file -> results in didnt find any
        # TODO: What behavior would be appropriate for no found node?
        self.log.error("didn't find any")
        return None

    def __get_index_by_name(self, name):
        self.log.info("get node by name: %s", name)
        for idx in self.nodes:
            if self.nodes[idx].get_name(BYTE_ENCODING) == name:
                return idx
        raise Exception("Found no node for name %s", name)

    def __getattr(self, inode):
        '''
        stat manpage
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

        # probably not needed
        '''
        elif inode == pyfuse3.ROOT_INODE:
            self.log.info("root inode")
            entry.st_mode = (stat.S_IFDIR | 0o755)
            entry.st_size = 0
        '''
        self.log.debug(self.nodes[inode].to_dict())
        if inode in self.nodes and self.nodes[inode].has_attr() and self.nodes[inode].get_attr().st_ino != 0:
            self.log.info("inode %d has attribute", inode)
            return self.nodes[inode].get_attr()

        else:
            entry = pyfuse3.EntryAttributes()
            node = None
            # TODO: Here is a fundamental error! somehow everything is freezing.
            try:
                if inode in self.nodes:
                    self.log.info("existing inode without attributes or st_ino = 0: %d", inode)
                    self.log.debug("does node exist in nodes? %s", inode in self.nodes)
                    node = self.nodes[inode]
                    self.log.debug("got node from nodes")
                    self.log.debug(node.to_dict())
                else:
                    self.log.error("Inode not in nodes!")
                    raise Exception("Didn't find inode in nodes.")

                # debug this
                if node.get_type() == DIR_TYPE:
                    self.log.debug("This is a directory.")
                    entry.st_mode = (stat.S_IFDIR | 0o755)
                    entry.st_size = 0
                elif node.get_type() == FILE_TYPE or node.get_type() == SWAP_TYPE:
                    self.log.debug("This is a file of type %i.", node.get_type())
                    entry.st_mode = (stat.S_IFREG | 0o666)
                    entry.st_size = node.get_data_size(encoding=UTF_8_ENCODING)
                    self.log.debug("size of file: %d", entry.st_size)
                else:
                    self.log.error("Found no corresponding type.")
            except Exception as e:
                self.log.error(e)
                raise FUSEError(errno.ENOENT)

        # current time in nanoseconds
        stamp = int(time.time() * 1e9)
        entry.st_atime_ns = stamp
        entry.st_ctime_ns = stamp
        entry.st_mtime_ns = stamp
        entry.st_gid = os.getgid()
        entry.st_uid = os.getuid()
        entry.st_ino = inode
        node.set_attr(entry)
        self.nodes[inode] = node

        self.log.debug("Resulting node of getattr call:")
        self.log.debug(node)

        return entry

    async def getattr(self, inode, ctx=None):
        self.log.info("----")
        self.log.info("getattr: %i", inode)
        self.log.info("----")
        return self.__getattr(inode)

    async def lookup(self, parent_inode, name, ctx=None):
        '''Look up a directory entry by name and get its attributes.
        This method should return an `EntryAttributes` instance for the
        directory entry *name* in the directory with inode *parent_inode*.
        If there is no such entry, the method should either return an
        `EntryAttributes` instance with zero ``st_ino`` value (in which case
        the negative lookup will be cached as specified by ``entry_timeout``),
        or it should raise `FUSEError` with an errno of `errno.ENOENT` (in this
        case the negative result will not be cached).
        *ctx* will be a `RequestContext` instance.
        The file system must be able to handle lookups for :file:`.` and
        :file:`..`, no matter if these entries are returned by `readdir` or not.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
        '''

        self.log.info("----")
        self.log.info("lookup: %s", name)
        self.log.info("----")
        self.log.debug("current nodes")
        self.log.debug(self.nodes)
        # TODO: parent_inode save in dict and evaluate here
        self.log.info("Parent Inode: %i", parent_inode)
        name = name.decode("utf-8")
        self.log.debug("Name: %s", name)
        self.log.debug("swp? %s", name[-4:])

        self.log.debug("Trying to find existing inode")
        for key, node in self.nodes.items():
            if node.get_name(encoding=UTF_8_ENCODING) == name:
                self.log.debug("%s, %s have the same name",
                               node.get_name(encoding=UTF_8_ENCODING), name)
                self.log.debug("parent path: %s", self.__get_path_inode(parent_inode))
                self.log.debug("node path: %s", node.get_path)
                if self.__get_path_inode(parent_inode) == node.get_path():
                    self.debug("Found existing inode %d", key)
                    return self.__getattr(key)
        self.log.debug("Couldn't find inode. Is it a swap file?")
        if name[-4:] == ".swp":
            self.log.debug("Found .swp")

            # Name of source file: .x.swp -> x
            src_name = name[1:-4]
            node = self.__get_node_by_name(src_name)
            parent_path = self.nodes[parent_inode].get_full_path()
            if node is None:
                self.log.debug("Found no corresponing file to swap %s with name %s", name, src_name)
                node = self.nodes[self.__add_inode(src_name, parent_path)]
            return self.__getattr(self.__add_inode(name, parent_path, data=node.get_data()))

        # If no . and .. -> no existing inode -> create new one
        # if name != '.' and name != '..':
            # return self.__getattr(self.__add_inode(self.__get_path(parent_inode, name.encode("utf-8"))))
        # new error
        # raise Exception("Lookup failed.")
        # raise pyfuse3.FUSEError(errno.ENOENT)

        '''
        This creates a inode -> not good!
        parent_node = self.nodes[parent_inode]
        path = parent_node.get_full_path()
        self.log.debug("Parent node: %s", parent_node)
        return self.__getattr(self.__add_inode(name, path))
        '''

        attr = pyfuse3.EntryAttributes()
        attr.st_ino = 0

        return attr

    async def mkdir(self, parent_inode, name, mode, ctx):
        self.log.info("----")
        self.log.info("mkdir: %s", name)
        self.log.info("----")
        return self.__getattr(self.__add_inode(name, self.nodes[parent_inode].get_full_path(), node_type=DIR_TYPE))
        """
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        try:
            os.mkdir(path, mode=(mode & ~ctx.umask))
            os.chown(path, ctx.uid, ctx.gid)
        except OSError as exc:
            raise FUSEError(exc.errno)
        attr = self.__getattr(path=path)
        self._add_path(attr.st_ino, path)
        return attr
        """

    async def opendir(self, inode, ctx):
        self.log.info("----")
        self.log.info("opendir: %d", inode)
        self.log.info("----")
        return inode

    async def readdir(self, inode, start_id, token):
        self.log.info("----")
        self.log.info("readdir: %d", inode)
        self.log.info("----")
        self.log.debug("start_id: %s", start_id)
        dir_path = self.nodes[inode].get_full_path()
        self.log.debug("dirpath: %s", dir_path)
        arr = {k: node for k, node in self.nodes.items() if node.get_path() == dir_path}
        self.log.debug("items in dir: %d", len(arr))
        try:
            for key, node in arr.items():
                self.log.debug("Key: %s, Value_name: %s", key, node.get_name())

                # This could be problematic: < -> results in loop, <= results in false ls
                if key <= start_id:
                    continue

                self.log.debug("before swp check")
                # TODO: Right now: omitting swap files.
                if node.get_type() == SWAP_TYPE:
                    self.log.debug("swp: %s", node.get_name())
                    continue
                self.log.debug("before unlink check")
                if node.is_unlink() is True:
                    self.log.debug("Node %s is unlinked.", node.get_name())
                    continue
                self.log.debug("before readdir of %s", node.get_name())
                if not pyfuse3.readdir_reply(token, node.get_name(), await self.getattr(key), key):
                    break
            self.log.debug("after readdir")
        except Exception as e:
            self.log.error("Readdir failed.")
            self.log.error(e.msg)
        return

    async def rmdir(self, parent_inode, name, ctx):
        self.log.info("----")
        self.log.info("rmdir: %s", name)
        self.log.info("----")
        '''Remove directory *name*
        This method must remove the directory *name* from the direcory with
        inode *parent_inode*. *ctx* will be a `RequestContext` instance. If
        there are still entries in the directory, the method should raise
        ``FUSEError(errno.ENOTEMPTY)``.
        If the inode associated with *name* (i.e., not the *parent_inode*) has a
        non-zero lookup count, the file system must remove only the directory
        entry (so that future calls to `readdir` for *parent_inode* will no
        longer include *name*, but e.g. calls to `getattr` for *file*'s inode
        still succeed). Removal of the associated inode holding the directory
        contents and metadata must be deferred to the `forget` method to be
        carried out when the lookup count reaches zero.
        (Since hard links to directories are not allowed by POSIX, this method
        is not required to check if there are still other directory entries
        refering to the same inode. This conveniently avoids the ambigiouties
        associated with the ``.`` and ``..`` entries).
        '''
        name = os.fsdecode(name)

        idx = self.__get_index_by_name(name)

        self.log.info("forget inode: %d", idx)

        # TODO: forget path(s)
        # if inode in self._lookup_cnt:
        #    self._forget_path(inode, path)

    # TODO: Not enough data
    async def open(self, inode, flags, ctx):
        self.log.info("----")
        self.log.info("open: %d", inode)
        self.log.info("----")
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
        if flags & os.O_RDWR or flags & os.O_WRONLY:
            self.log.error("False permission.")
            # raise pyfuse3.FUSEError(errno.EPERM)
        return inode

    async def read(self, inode, off, size):
        self.log.info("----")
        self.log.info("read: %d", inode)
        self.log.info("----")
        self.log.info(self.nodes[inode].get_data()[off: off+size])
        return self.nodes[inode].get_data()[off: off+size]

    # TODO: implement mode and flags
    async def create(self, parent_inode, name, mode, flags, ctx):
        self.log.info("----")
        self.log.info("create: %s", name)
        self.log.info("----")

        if name.decode("utf-8")[-4:] == ".swp":
            self.log.debug("Creating a swap file.")
        '''Create a file with permissions *mode* and open it with *flags*
        *ctx* will be a `RequestContext` instance.
        The method must return a tuple of the form *(fh, attr)*, where *fh* is a
        file handle like the one returned by `open` and *attr* is an
        `EntryAttributes` instance with the attributes of the newly created
        directory entry.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
        '''
        try:
            self.log.debug("Trying to get inode")
            inode = self.__add_inode(name, self.nodes[parent_inode].get_full_path())
            self.log.debug("Got inode %d", inode)
            if inode is None:
                self.log.error("Inode already exists.")

                # Get node by name and path!
                self.__get_node_by_name()
            attr = self.__getattr(inode)
            self.log.debug("got attributes for inode %d", inode)
            self.log.debug(str(attr))
        except Exception as e:
            self.log.error(e)
            self.log.error("Create Failed")
        """
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        try:
            fd = os.open(path, flags | os.O_CREAT | os.O_TRUNC)
        except OSError as exc:
            raise FUSEError(exc.errno)
        attr = self.__getattr(fd=fd)
        self._add_path(attr.st_ino, path)
        self._inode_fd_map[attr.st_ino] = fd
        self._fd_inode_map[fd] = attr.st_ino
        self._fd_open_count[fd] = 1
        return (fd, attr)
        """

        return (inode, attr)

    async def release(self, inode):
        self.log.info("----")
        self.log.info("release: %s", inode)
        self.log.info("----")
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
        if self.nodes[inode].type == SWAP_TYPE:
            self.log.debug("deleting %s", self.nodes[inode])
            del self.nodes[inode]
        self.log.debug(self.nodes)

    async def releasedir(self, inode):
        self.log.info("----")
        self.log.info("releasedir: %d", inode)
        self.log.info("----")
        '''Release open directory
        This method will be called exactly once for each `opendir` call. After
        *fh* has been released, no further `readdir` requests will be received
        for it (until it is opened again with `opendir`).
        '''

        pass

    async def setattr(self, inode, attr, fields, fh, ctx):
        self.log.info("----")
        self.log.info("setattr: %d", inode)
        self.log.info("----")
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
        if inode not in self.nodes:
            self.log.error("Inode %d not saved.", inode)
            raise Exception("Inode not found.")
        new_attr = self.nodes[inode].get_attr()
        self.log.debug(new_attr)
        self.log.debug(fields)
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
            self.nodes[inode].set_attr(new_attr)

        except OSError as exc:
            raise FUSEError(exc.errno)

        return await self.getattr(inode)

    async def unlink(self, parent_inode, name, ctx):
        self.log.info("----")
        self.log.info("unlink: %s", name)
        self.log.info("----")
        '''Remove a (possibly special) file
            This method must remove the (special or regular) file *name* from the
            directory with inode *parent_inode*.  *ctx* will be a `RequestContext`
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
        self.nodes[idx].set_unlink(True)
        self.log.info("inode: %d", idx)

        # unlink is not prohibited to delete a item -> forget method
        # del self.nodes[idx]

        # TODO: forget path(s)

    async def flush(self, inode):
        self.log.info("----")
        self.log.info("flush: %d", inode)
        self.log.info("----")
        '''Handle close() syscall.
        *fh* will by an integer filehandle returned by a prior `open` or
        `create` call.
        This method is called whenever a file descriptor is closed. It may be
        called multiple times for the same open file (e.g. if the file handle
        has been duplicated).
        '''

    async def write(self, inode, off, buf):
        self.log.info(self.nodes)
        self.log.info("----")
        self.log.info("write inode: %d", inode)
        self.log.info("----")
        self.log.info("offset: %d", off)

        '''Write *buf* into *fh* at *off*
        *fh* will by an integer filehandle returned by a prior `open` or
        `create` call.
        This method must return the number of bytes written. However, unless the
        file system has been mounted with the ``direct_io`` option, the file
        system *must* always write *all* the provided data (i.e., return
        ``len(buf)``).
        '''

        try:
            output = ""
            node = self.nodes[inode]
            data = node.get_data(encoding=UTF_8_ENCODING)
            self.log.debug("data: %s", data)
            buffer = buf.decode("utf-8")
            self.log.debug("buffer: %s", buffer)
            output = data[:off] + buffer + data[off:]
            self.log.debug("output: %s", output)
            self.log.debug("current data: %s", self.nodes[inode].get_data())
            self.nodes[inode].set_data(output)

        except Exception as e:
            self.log.error(e)
            self.log.error("Write was not successful")
        return len(buf)

    async def forget(self, inode_list):
        self.log.info("forget")
        '''Decrease lookup counts for inodes in *inode_list*
        *inode_list* is a list of ``(inode, nlookup)`` tuples. This method
        should reduce the lookup count for each *inode* by *nlookup*.
        If the lookup count reaches zero, the inode is currently not known to
        the kernel. In this case, the file system will typically check if there
        are still directory entries referring to this inode and, if not, remove
        the inode.
        If the file system is unmounted, it may not have received `forget` calls
        to bring all lookup counts to zero. The filesystem needs to take care to
        clean up inodes that at that point still have non-zero lookup count
        (e.g. by explicitly calling `forget` with the current lookup count for
        every such inode after `main` has returned).
        This method must not raise any exceptions (not even `FUSEError`), since
        it is not handling a particular client request.
        '''
        for (inode, nlookup) in inode_list:
            if self._lookup_cnt[inode] > nlookup:
                self._lookup_cnt[inode] -= nlookup
                continue
            self.log.debug('forgetting about inode %d', inode)
            # assert inode not in self._inode_fd_map
            del self._lookup_cnt[inode]
            try:
                del self.nodes[inode]
            except KeyError:  # may have been deleted
                pass


async def start_async(mount_point, debug, debug_fuse):
    utils.init_logging("pyfuse3", debug_fuse)

    testfs = TestFs(mount_point, debug)
    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('fsname=iotfs')
    if debug_fuse:
        fuse_options.add('debug')
    pyfuse3.init(testfs, mount_point, fuse_options)
    try:
        await pyfuse3.main()
    except BaseException:
        logging.getLogger("pyfuse3").debug("BaseException occured")
        pyfuse3.close(unmount=False)
    except Exception:
        logging.getLogger("pyfuse3").debug("Exception occured")
        pyfuse3.close(unmount=False)

    pyfuse3.close()


def start(mount_point, debug, debug_fuse):
    utils.init_logging("pyfuse3", debug_fuse)

    testfs = TestFs(mount_point, debug)
    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('fsname=iotfs')
    if debug_fuse:
        fuse_options.add('debug')
    pyfuse3.init(testfs, mount_point, fuse_options)
    try:
        trio.run(pyfuse3.main)
    except BaseException:
        logging.getLogger("pyfuse3").debug("BaseException occured")
        pyfuse3.close(unmount=False)
    except Exception:
        logging.getLogger("pyfuse3").debug("Exception occured")
        pyfuse3.close(unmount=False)
    finally:
        pyfuse3.close()
