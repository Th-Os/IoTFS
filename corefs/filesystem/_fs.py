#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyfuse3
import errno
import stat
import time
import os

from pyfuse3 import FUSEError

try:
    import faulthandler
except ImportError:
    pass
else:
    faulthandler.enable()

from filesystem.node import File, Directory, EntryAttributes
from filesystem.node import DIR_TYPE, SWAP_TYPE, FILE_TYPE, UTF_8_ENCODING, BYTE_ENCODING

from utils import _logging


def wrapper(func):
    async def f(*args, **kwargs):
        args[0].log.info("unique: %d, operation: %s",
                         args[0].unique, func.__name__)
        result = await func(*args, **kwargs)
        args[0].log.info("unique: %d, success", args[0].unique)
        args[0].unique += 1
        return result
    return f


class _FileSystem(pyfuse3.Operations):

    supports_dot_lookup = True
    enable_writeback_cache = True
    enable_acl = False

    def __init__(self, mount_point, debug=False):
        super(_FileSystem, self).__init__()

        # fuse debug starts with 2 for operations
        self.unique = 2
        self.log = _logging.create_logger(self.__class__.__name__, debug)
        self.log.info("Init %s", self.__class__.__name__)
        self.nodes = dict()
        self.nodes[pyfuse3.ROOT_INODE] = Directory(
            "root", os.path.abspath(mount_point), root=True)

        self.log.debug("Size of nodes: %d", len(self.nodes))

        # TODO: Think about reimplementing this into node.py
        self._fd_inode_map = dict()
        self._inode_fd_map = dict()
        self._fd_open_count = dict()

    def __add_inode(self, name, parent_inode, node_type=FILE_TYPE, data="", mode=7777):
        path = self.nodes[parent_inode].get_full_path()
        self.log.info('__add_inode with path %s and name %s', path, name)
        if path[-1] != os.path.sep:
            path += os.path.sep
            self.log.debug("new path: %s", path)
        inode = list(self.nodes.keys())[-1] + 1

        # With hardlinks, one inode may map to multiple paths.
        if inode not in self.nodes and inode is not pyfuse3.ROOT_INODE:
            self.log.debug("Found no inode")
            self.log.debug(
                "Create: inode %d, with path: %s, and name: %s", inode, path, name)
            if node_type == FILE_TYPE or node_type == SWAP_TYPE:
                self.nodes[inode] = File(
                    name, path, mode=mode, parent=parent_inode, data=data)
            else:
                self.nodes[inode] = Directory(
                    name, path, mode=mode, parent=parent_inode)
            self.nodes[inode].inc_open_count()
            self.log.debug(self.nodes)
        return inode

    def __try_remove_inode(self, inode):
        self.log.info("Trying to remove inode %d.", inode)
        try:
            if self.nodes[inode].get_open_count() <= 1:
                self.log.debug("Removed inode %d", inode)
                del self.nodes[inode]
            else:
                self.log.debug("Didn't remove inode %d", inode)
        except KeyError:
            self.log.warning("Inode %d doesn't exist.", inode)

    def __try_decrease_op_count(self, inode):
        self.log.warning("Trying to decrease op count of %d.", inode)
        try:
            self.nodes[inode].dec_open_count()
            if self.nodes[inode].get_open_count() == 0:
                self.nodes[inode].lock()
            self.log.warning("New op count: %d",
                             self.nodes[inode].get_open_count())
        except KeyError:
            self.log.error("No inode with key %d.", inode)
        except Exception as e:
            self.log.error(e)

    def __try_increase_op_count(self, inode):
        self.log.warning("Trying to increase op count of %d.", inode)
        try:
            self.nodes[inode].inc_open_count()
        except KeyError:
            self.warning("Inode %d does not exist.", inode)
        except Exception as e:
            self.log.error(e)

    def __get_children(self, inode):
        if type(self.nodes[inode]) is not Directory:
            self.log.error("Inode %d is no directory.")
            raise NotADirectoryError("Inode %d is no directory.")
        return [idx for idx in self.nodes if self.nodes[idx].get_parent() == inode]

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

    def __get_node_by_name(self, name, array=None):
        if array is None:
            array = self.nodes
        self.log.info("get node by name: %s", name)
        for idx in array:
            self.log.debug(idx)
            self.log.debug("check %s vs %s", self.nodes[idx].get_name(
                encoding=UTF_8_ENCODING), name)
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
        self.log.info("get attributes of %i", inode)
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

        self.log.debug(self.nodes[inode])
        if inode in self.nodes and self.nodes[inode].has_attr() and self.nodes[inode].get_attr().st_ino != 0:
            self.log.info("inode %d has attribute", inode)
            return self.nodes[inode].get_attr()

        else:
            entry = EntryAttributes()
            node = None
            # TODO: Here is a fundamental error! somehow everything is freezing.
            try:
                if inode in self.nodes:
                    self.log.info(
                        "existing inode without attributes or st_ino = 0: %d", inode)
                    self.log.debug("does node exist in nodes? %s",
                                   inode in self.nodes)
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
                    self.log.debug("This is a file of type %i.",
                                   node.get_type())
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

    @wrapper
    async def getattr(self, inode, ctx=None):
        self.log.info("----")
        self.log.info("getattr: %i", inode)
        self.log.info("----")
        return self.__getattr(inode)

    @wrapper
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

    # http://man7.org/linux/man-pages/man7/xattr.7.html
    @wrapper
    async def setxattr(self, inode, name, value, ctx):
        '''Set extended attribute *name* of *inode* to *value*.
        *ctx* will be a `RequestContext` instance.
        The attribute may or may not exist already. Both *name* and *value* will
        be of type `bytes`. *name* is guaranteed not to contain zero-bytes
        (``\\0``).
        '''
        self.log.info("----")
        self.log.info("setxattr: %i", inode)
        self.log.debug("setxattr: %s", name)
        self.log.debug("setxattr: %s", value)
        self.log.info("----")

        # raise FUSEError(errno.ENOSYS)

    @wrapper
    async def getxattr(self, inode, name, ctx):
        '''Return extended attribute *name* of *inode*
        *ctx* will be a `RequestContext` instance.
        If the attribute does not exist, the method must raise `FUSEError` with
        an error code of `ENOATTR`. *name* will be of type `bytes`, but is
        guaranteed not to contain zero-bytes (``\\0``).
        '''

        self.log.info("----")
        self.log.info("getxattr: %i", inode)
        self.log.debug("getxattr: %s", name)
        self.log.info("----")

        # https://github.com/libfuse/pyfuse3/blob/master/src/xattr.h ENOATTR = ENODATA
        raise FUSEError(errno.ENODATA)

    @wrapper
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
        name = name.decode("utf-8")
        self.log.debug("Name: %s", name)
        self.log.debug("Trying to find existing inode")
        children = self.__get_children(parent_inode)
        for inode in children:
            node = self.nodes[inode]
            if node.get_name(encoding=UTF_8_ENCODING) == name:
                self.log.debug("Found existing inode %d", inode)
                if self.nodes[inode].is_locked():
                    self.log.error("Inode %d is locked", inode)
                    raise FUSEError(errno.ENOENT)
                else:
                    return self.__getattr(inode)
        self.log.debug("Couldn't find inode. Is it a swap file?")
        self.log.debug("swp? %s", name[-4:])
        if name[-4:] == ".swp":
            self.log.debug("Found .swp")

            # Name of source file: .x.swp -> x
            src_name = name[1:-4]
            node = self.__get_node_by_name(src_name)

            # Case: Swap File is created before real file.
            if node is None:
                self.log.debug(
                    "Found no corresponing file to swap %s with name %s", name, src_name)
                node = self.nodes[self.__add_inode(src_name, parent_inode)]
            return self.__getattr(self.__add_inode(name, parent_inode, data=node.get_data()))

        # If no . and .. -> no existing inode -> create new one
        # if name != '.' and name != '..':
            # return self.__getattr(self.__add_inode(self.__get_path(parent_inode, name.encode("utf-8"))))
        # new error
        # raise Exception("Lookup failed.")
        # raise pyfuse3.FUSEError(errno.ENOENT)

        attr = EntryAttributes()
        attr.st_ino = 0

        return attr

    @wrapper
    async def open(self, inode, flags, ctx):
        self.log.info("----")
        self.log.info("open: %d", inode)
        self.log.info("----")

        '''Open a inode *inode* with *flags*.
        *ctx* will be a `RequestContext` instance.
        *flags* will be a bitwise or of the open flags described in the
        :manpage:`open(2)` manpage and defined in the `os` module (with the
        exception of ``O_CREAT``, ``O_EXCL``, ``O_NOCTTY`` and ``O_TRUNC``)
        This method must return a `FileInfo` instance. The `FileInfo.fh` field
        must contain an integer file handle, which will be passed to the `read`,
        `write`, `flush`, `fsync` and `release` methods to identify the open
        file. The `FileInfo` instance may also have relevant configuration
        attributes set; see the `FileInfo` documentation for more information.
        '''

        # TODO: Add permission handling to nodes.
        '''
        assert flags & os.O_CREAT == 0
        if not (flags & os.O_RDWR or flags & os.O_RDONLY or flags & os.O_WRONLY or flags & os.O_APPEND):
            self.log.error("False permission.")
            self.log.debug("read write: %d", flags & os.O_RDWR)
            self.log.debug("read only: %d", flags & os.O_RDONLY)
            self.log.debug("read write: %d", flags & os.O_WRONLY)
            self.log.debug("append: %d", flags & os.O_APPEND)
            self.log.debug("whole flags: %d", flags)
            raise pyfuse3.FUSEError(errno.EPERM)
        '''
        self.__try_increase_op_count(inode)
        return pyfuse3.FileInfo(fh=inode)

    @wrapper
    async def read(self, inode, off, size):
        self.log.info("----")
        self.log.info("read: %d", inode)
        self.log.info("----")

        '''Read *size* bytes from *fh* at position *off*
        *fh* will by an integer filehandle returned by a prior `open` or
        `create` call.
        This function should return exactly the number of bytes requested except
        on EOF or error, otherwise the rest of the data will be substituted with
        zeroes.
        '''

        self.log.debug(self.nodes[inode].get_data()[off: off+size])
        return self.nodes[inode].get_data()[off: off+size]

    # TODO: implement mode and flags
    @wrapper
    async def create(self, parent_inode, name, mode, flags, ctx):
        self.log.info("----")
        self.log.info("create: %s", name)
        self.log.info("----")

        '''Create a file with permissions *mode* and open it with *flags*
        *ctx* will be a `RequestContext` instance.
        The method must return a tuple of the form *(fh, attr)*, where *fh* is a
        file handle like the one returned by `open` and *attr* is an
        `EntryAttributes` instance with the attributes of the newly created
        directory entry.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
        '''

        if name.decode("utf-8")[-4:] == ".swp":
            self.log.debug("Creating a swap file.")
        try:
            self.log.debug("Trying to get inode")
            inode = self.__add_inode(name, parent_inode, mode=mode)
            self.log.debug("Got inode %d", inode)
            attr = self.__getattr(inode)
            self.log.debug("got attributes for inode %d", inode)
            self.log.debug(str(attr))
        except Exception as e:
            self.log.error(e)
            self.log.error("Create Failed")

        return (inode, attr)

    @wrapper
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
        except KeyError:
            self.log.warning("Inode %d does not exist.", inode)
        except Exception as e:
            self.log.error(e)
            self.log.error("Write was not successful.")
        return len(buf)

    @wrapper
    async def access(self, inode, mode, ctx):
        '''Check if requesting process has *mode* rights on *inode*.
        *ctx* will be a `RequestContext` instance.
        The method must return a boolean value.
        If the ``default_permissions`` mount option is given, this method is not
        called.
        When implementing this method, the `get_sup_groups` function may be
        useful.
        '''

        self.log.info("----")
        self.log.info("access: %i", inode)
        self.log.info("----")

        self.log.debug("access: %s", mode)
        # raise FUSEError(errno.ENOSYS)

    @wrapper
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
        self.nodes[inode].unlock()
        self.__try_decrease_op_count(inode)

    @wrapper
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

        children = self.__get_children(parent_inode)
        if len(children) == 0:
            self.log.warning(
                "Found no children for parent_inode %d.", parent_inode)
            return
        for inode in children:
            try:
                if self.nodes[inode].get_name() == name:
                    self.log.info("Lock inode: %d", inode)
                    self.nodes[inode].set_invisible()
                    if self.nodes[inode].get_open_count() == 1:
                        self.nodes[inode].lock()
            except KeyError:
                self.log.warning("Inode %d does not exist.", inode)

    @wrapper
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

        # TODO: Really decrease op count?
        # self.__try_decrease_op_count(inode)

    @wrapper
    async def forget(self, inode_list):
        self.log.info("----")
        self.log.info("forget: %s", inode_list)
        self.log.info("----")
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
            self.log.debug("inode: %d, nlookup: %d", inode, nlookup)
            try:
                if self.nodes[inode].get_open_count() > nlookup:
                    self.nodes[inode].dec_open_count(nlookup)
                    self.log.debug("inode %d with lookup count of %d",
                                   inode, self.nodes[inode].get_open_count())

            except KeyError:  # may have been deleted
                self.log.warning("Inode %d does not exist anymore.", inode)
                pass
            finally:
                self.__try_remove_inode(inode)

    @wrapper
    async def fsync(self, inode, datasync):
        '''Flush buffers for open file *fh*
        If *datasync* is true, only the file contents should be
        flushed (in contrast to the metadata about the file).
        *fh* will by an integer filehandle returned by a prior `open` or
        `create` call.
        '''

        self.log.info("----")
        self.log.info("fsync: %i", inode)
        self.log.info("----")
        # raise FUSEError(errno.ENOSYS)

    @wrapper
    async def symlink(self, parent_inode, name, target, ctx):
        '''Create a symbolic link
        This method must create a symbolink link named *name* in the directory
        with inode *parent_inode*, pointing to *target*.  *ctx* will be a
        `RequestContext` instance.
        The method must return an `EntryAttributes` instance with the attributes
        of the newly created directory entry.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
        '''

        self.log.info("----")
        self.log.info("symlink: %s", name)
        self.log.info("----")
        # raise FUSEError(errno.ENOSYS)

    @wrapper
    async def rename(self, parent_inode_old, name_old, parent_inode_new, name_new, flags, ctx):
        '''Rename a directory entry.
        This method must rename *name_old* in the directory with inode
        *parent_inode_old* to *name_new* in the directory with inode
        *parent_inode_new*.  If *name_new* already exists, it should be
        overwritten.
        *flags* may be `RENAME_EXCHANGE` or `RENAME_NOREPLACE`. If
        `RENAME_NOREPLACE` is specified, the filesystem must not overwrite
        *name_new* if it exists and return an error instead. If
        `RENAME_EXCHANGE` is specified, the filesystem must atomically exchange
        the two files, i.e. both must exist and neither may be deleted.
        *ctx* will be a `RequestContext` instance.
        Let the inode associated with *name_old* in *parent_inode_old* be
        *inode_moved*, and the inode associated with *name_new* in
        *parent_inode_new* (if it exists) be called *inode_deref*.
        If *inode_deref* exists and has a non-zero lookup count, or if there are
        other directory entries referring to *inode_deref*), the file system
        must update only the directory entry for *name_new* to point to
        *inode_moved* instead of *inode_deref*.  (Potential) removal of
        *inode_deref* (containing the previous contents of *name_new*) must be
        deferred to the `forget` method to be carried out when the lookup count
        reaches zero (and of course only if at that point there are no more
        directory entries associated with *inode_deref* either).
        '''

        self.log.info("----")
        self.log.info("rename: %s to %s", name_old, name_new)
        self.log.info("----")

        # See https://github.com/libfuse/pyfuse3/blob/1730558574361bf7b05b1be2a228a0443deca088/examples/tmpfs.py#L224
        if flags != 0:
            raise FUSEError(errno.EINVAL)

        entry_old = await self.lookup(parent_inode_old, name_old)

        self.nodes[entry_old.st_ino].set_parent(parent_inode_new)
        self.nodes[entry_old.st_ino].set_name(name_new)

    @wrapper
    async def link(self, inode, new_parent_inode, new_name, ctx):
        '''Create directory entry *name* in *parent_inode* refering to *inode*.
        *ctx* will be a `RequestContext` instance.
        The method must return an `EntryAttributes` instance with the
        attributes of the newly created directory entry.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
        '''

        self.log.info("----")
        self.log.info("link: %i to %s", inode, new_name)
        self.log.info("----")

        # raise FUSEError(errno.ENOSYS)

    @wrapper
    async def readlink(self, inode, ctx):
        '''Return target of symbolic link *inode*.
        *ctx* will be a `RequestContext` instance.
        '''

        # raise FUSEError(errno.ENOSYS)
        self.log.info("----")
        self.log.info("readlink: %i", inode)
        self.log.info("----")

    @wrapper
    async def mknod(self, parent_inode, name, mode, rdev, ctx):
        '''Create (possibly special) file
        This method must create a (special or regular) file *name* in the
        directory with inode *parent_inode*. Whether the file is special or
        regular is determined by its *mode*. If the file is neither a block nor
        character device, *rdev* can be ignored. *ctx* will be a
        `RequestContext` instance.
        The method must return an `EntryAttributes` instance with the attributes
        of the newly created directory entry.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
       '''

        self.log.info("----")
        self.log.info("mknod: %s", name)
        self.log.info("----")

        self.log.debug("With mode: %s", mode)

        # TODO: implement mode behavior
        inode = self.__add_inode(name, parent_inode, mode=mode)
        return self.__getattr(inode)

    @wrapper
    async def mkdir(self, parent_inode, name, mode, ctx):
        self.log.info("----")
        self.log.info("mkdir: %s", name)
        self.log.info("----")

        return self.__getattr(self.__add_inode(name, parent_inode,
                                               node_type=DIR_TYPE, mode=mode))

    @wrapper
    async def opendir(self, inode, ctx):
        self.log.info("----")
        self.log.info("opendir: %d", inode)
        self.log.info("----")
        self.__try_increase_op_count(inode)
        return inode

    @wrapper
    async def readdir(self, inode, start_id, token):
        self.log.info("----")
        self.log.info("readdir: %d", inode)
        self.log.info("----")
        self.log.debug("start_id: %s", start_id)
        dir_path = self.nodes[inode].get_full_path()
        self.log.debug("dirpath: %s", dir_path)
        arr = self.__get_children(inode)
        self.log.debug("items in dir: %d", len(arr))
        try:
            for key in arr:
                node = self.nodes[key]
                self.log.debug("Key: %s, Value_name: %s", key, node.get_name())

                # TODO: This could be problematic: < -> results in loop, <= results in false ls
                if key <= start_id:
                    continue

                # Omitting swap files.
                if node.get_type() == SWAP_TYPE:
                    self.log.debug("swp: %s", node.get_name())
                    continue
                if node.is_invisible() is True:
                    self.log.debug("Node %s is invisible.", node.get_name())
                    continue
                if not pyfuse3.readdir_reply(token, node.get_name(), await self.getattr(key), key):
                    break
        except Exception as e:
            self.log.error("Readdir failed.")
            self.log.error(e)
        return

    @wrapper
    async def rmdir(self, parent_inode, name, ctx):
        self.log.info("----")
        self.log.info("rmdir: %s", name)
        self.log.info("----")
        '''Remove directory *name*
        This method must remove the directory *name* from the directory with
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

        try:
            self.log.debug("Getting childs of: %s",
                           self.nodes[parent_inode].get_name())
            self.log.debug(self.__get_children(parent_inode))

            filtered_list = [idx for idx in self.__get_children(
                parent_inode) if self.nodes[idx].get_name() == name]

            self.log.debug("filtered list with name %s:", name)
            self.log.debug(filtered_list)

            if len(filtered_list) > 1:
                self.log.error("Found more than one node.")
            inode = filtered_list[0]

            # Forget path for readdir. But it will be accessible via getattr, if lookup_count > 1.
            self.nodes[inode].set_invisible()
            if self.nodes[inode].get_open_count() == 1:
                self.nodes[inode].lock()
        except Exception as e:
            self.log.error(e)

    @wrapper
    async def releasedir(self, inode):
        self.log.info("----")
        self.log.info("releasedir: %d", inode)
        self.log.info("----")
        '''Release open directory
        This method will be called exactly once for each `opendir` call. After
        *fh* has been released, no further `readdir` requests will be received
        for it (until it is opened again with `opendir`).
        '''
        self.nodes[inode].unlock()
        self.__try_decrease_op_count(inode)

    @wrapper
    async def fsyncdir(self, inode, datasync):
        '''Flush buffers for open directory *fh*
        If *datasync* is true, only the directory contents should be
        flushed (in contrast to metadata about the directory itself).
        '''

        self.log.info("----")
        self.log.info("fsyncdir: %d", inode)
        self.log.info("----")

        # raise FUSEError(errno.ENOSYS)

    @wrapper
    async def statfs(self, ctx):
        '''Get file system statistics
        *ctx* will be a `RequestContext` instance.
        The method must return an appropriately filled `StatvfsData` instance.

        See https://linux.die.net/man/2/statvfs
        and https://github.com/libfuse/pyfuse3/blob/1730558574361bf7b05b1be2a228a0443deca088/examples/tmpfs.py#L323
        '''

        self.log.info("----")
        self.log.info("statfs")
        self.log.info("----")

        stats = pyfuse3.StatvfsData()
        stats.f_bsize = 512
        stats.f_frsize = 512

        size_sum = 0
        for inodes in self.nodes:
            size_sum += self.nodes[inodes].get_attr().st_size

        stats.f_blocks = size_sum // stats.f_frsize
        stats.f_bfree = max(size_sum // stats.f_frsize, 1024)
        stats.f_bavail = stats.f_bfree

        count = len(self.nodes)
        stats.f_files = count

        # TODO: Think about max size of filesystem
        stats.f_ffree = max(count, 200)
        stats.favail = stats.f_ffree

        return stats

    def stacktrace(self):
        '''Asynchronous debugging
        This method will be called when the ``fuse_stacktrace`` extended
        attribute is set on the mountpoint. The default implementation logs the
        current stack trace of every running Python thread. This can be quite
        useful to debug file system deadlocks.
        '''

        self.log.info("----")
        self.log.info("stacktrace")
        self.log.info("----")

        import sys
        import traceback

        code = list()
        for threadId, frame in sys._current_frames().items():
            code.append("\n# ThreadID: %s" % threadId)
            for filename, lineno, name, line in traceback.extract_stack(frame):
                code.append('%s:%d, in %s' %
                            (os.path.basename(filename), lineno, name))
                if line:
                    code.append("    %s" % (line.strip()))

        self.log.error("\n".join(code))

    @wrapper
    async def listxattr(self, inode, ctx):
        '''Get list of extended attributes for *inode*
        *ctx* will be a `RequestContext` instance.
        This method must return a sequence of `bytes` objects.  The objects must
        not include zero-bytes (``\\0``).
        '''

        # raise FUSEError(errno.ENOSYS)
        self.log.info("----")
        self.log.info("listxattr: %d", inode)
        self.log.info("----")

    @wrapper
    async def removexattr(self, inode, name, ctx):
        '''Remove extended attribute *name* of *inode*
        *ctx* will be a `RequestContext` instance.
        If the attribute does not exist, the method must raise `FUSEError` with
        an error code of `ENOATTR`. *name* will be of type `bytes`, but is
        guaranteed not to contain zero-bytes (``\\0``).
        '''

        # raise FUSEError(errno.ENOSYS)
        self.log.info("----")
        self.log.info("removexattr: %d", inode)
        self.log.info("----")
