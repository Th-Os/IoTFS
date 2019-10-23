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

from corefs.filesystem.node import Directory, Types, Encodings
from corefs.filesystem.node_dict import NodeDict

from corefs.utils import _logging


def wrapper(*params):
    def decorator(func):
        async def f(*args, **kwargs):
            fs = args[0]
            fs.log.info("unique: %d, operation: %s",
                        fs.unique, func.__name__)
            s = ""
            for param in params:
                s += " {0},".format(args[param])
            s = s[:-1]
            fs.log.debug("---")
            fs.log.debug(func.__name__ + ":" + s)
            fs.log.debug("---")
            result = await func(*args, **kwargs)
            fs.log.info("unique: %d, success", fs.unique)
            fs.unique += 2
            return result
        return f
    return decorator


class _FileSystem(pyfuse3.Operations):

    supports_dot_lookup = True
    enable_writeback_cache = True
    enable_acl = False

    def __init__(self, mount_point, debug=False):
        super(_FileSystem, self).__init__()

        self.log = _logging.create_logger(self.__class__.__name__, debug)
        self.log.info("Init %s", self.__class__.__name__)

        # fuse debug log ("unique ...") starts with 2 for operations and increments each operation with 2
        self.unique = 2

        self.nodes = NodeDict(logger=self.log)
        self.nodes[pyfuse3.ROOT_INODE] = Directory(
            "root", os.path.abspath(mount_point), 0o754, root=True)

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
        if inode not in self.nodes:
            self.log.error("Inode not in nodes!")
            raise Exception("Didn't find inode in nodes.")
        node = self.nodes[inode]

        entry = pyfuse3.EntryAttributes()

        entry.st_mode = node.mode
        self.log.debug(oct(node.mode))
        self.log.debug(oct(node.get_permissions()))
        entry.st_size = node.size

        entry.st_atime_ns = node.atime
        entry.st_ctime_ns = node.ctime
        entry.st_mtime_ns = node.mtime
        entry.st_gid = node.gid
        entry.st_uid = node.uid
        entry.st_ino = inode
        self.nodes[inode] = node
        self.log.debug(oct(entry.st_mode))
        self.log.debug(self.nodes[inode])
        return entry

    @wrapper(1)
    async def getattr(self, inode, ctx=None):
        return self.__getattr(inode)

    @wrapper(1)
    async def setattr(self, inode, attr, fields, fh, ctx):
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
        node = self.nodes[inode]
        try:
            if fields.update_size:
                node.size = attr.st_size
                self.log.debug("new size: %d", node.size)
            if fields.update_mode:
                node.mode = attr.st_mode
                self.log.debug("new mode: %s", oct(node.mode))
            if fields.update_uid:
                node.uid = attr.st_uid
                self.log.debug("new uid: %d", node.uid)
            if fields.update_gid:
                node.gid = attr.st_gid
                self.log.debug("new gid: %d", node.gid)
            if fields.update_atime:
                node.atime = attr.st_atime_ns
                self.log.debug("new atime: %d", node.atime)
            if fields.update_mtime:
                node.mtime = attr.st_mtime_ns
                self.log.debug("new mtime: %d", node.mtime)
            node.ctime = int(time.time() * 1e9)
            self.nodes[inode] = node

        except OSError as exc:
            raise FUSEError(exc.errno)

        return await self.getattr(inode)

    # http://man7.org/linux/man-pages/man7/xattr.7.html
    @wrapper(1, 2, 3)
    async def setxattr(self, inode, name, value, ctx):
        '''Set extended attribute *name* of *inode* to *value*.
        *ctx* will be a `RequestContext` instance.
        The attribute may or may not exist already. Both *name* and *value* will
        be of type `bytes`. *name* is guaranteed not to contain zero-bytes
        (``\\0``).
        '''
        pass

    '''
    unique: 432, opcode: GETXATTR (22), nodeid: 2, insize: 65, pid: 12455
    [corefs.StandardFileSystem | MainThread | 2019-10-16 23:25:23.454] INFO: unique: 400, operation: getxattr
    [corefs.StandardFileSystem | MainThread | 2019-10-16 23:25:23.454] DEBUG: ---
    [corefs.StandardFileSystem | MainThread | 2019-10-16 23:25:23.455] DEBUG: getxattr: 2, b'security.selinux'
    [corefs.StandardFileSystem | MainThread | 2019-10-16 23:25:23.455] DEBUG: ---
    unique: 432, error: -61 (No data available), outsize: 16
    unique: 434, opcode: GETXATTR (22), nodeid: 2, insize: 72, pid: 12455
    [corefs.StandardFileSystem | MainThread | 2019-10-16 23:25:23.455] INFO: unique: 400, operation: getxattr
    [corefs.StandardFileSystem | MainThread | 2019-10-16 23:25:23.455] DEBUG: ---
    [corefs.StandardFileSystem | MainThread | 2019-10-16 23:25:23.455] DEBUG: getxattr: 2, b'system.posix_acl_access'
    [corefs.StandardFileSystem | MainThread | 2019-10-16 23:25:23.455] DEBUG: ---
   unique: 434, error: -61 (No data available), outsize: 16

    '''

    @wrapper(1, 2)
    async def getxattr(self, inode, name, ctx):
        '''Return extended attribute *name* of *inode*
        *ctx* will be a `RequestContext` instance.
        If the attribute does not exist, the method must raise `FUSEError` with
        an error code of `ENOATTR`. *name* will be of type `bytes`, but is
        guaranteed not to contain zero-bytes (``\\0``).
        '''
        # https://github.com/libfuse/pyfuse3/blob/master/src/xattr.h ENOATTR = ENODATA
        raise FUSEError(errno.ENODATA)

    @wrapper(2)
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

        self.log.debug("current nodes")
        self.log.debug(self.nodes)
        name = name.decode("utf-8")
        self.log.debug("Name: %s", name)
        self.log.debug("Trying to find existing inode")
        children = self.nodes.get_children(parent_inode)
        for inode in children:
            node = self.nodes[inode]
            if node.get_name(encoding=Encodings.UTF_8_ENCODING) == name:
                self.log.debug("Found existing inode %d", inode)
                if self.nodes[inode].is_locked():
                    self.log.error("Inode %d is locked", inode)
                    raise FUSEError(errno.ENOENT)
                else:
                    return self.__getattr(inode)
        self.log.debug("Couldn't find inode. Is it a swap file?")

        if len(name) > 4 and name[-4:] == ".swp":
            self.log.debug("Found .swp")

            # Name of source file: .x.swp -> x
            src_name = name[1:-4]
            node = self.nodes.get_node_by_name(src_name)

            # Case: Swap File is created before real file.
            if node is None:
                self.log.debug(
                    "Found no corresponing file to swap %s with name %s", name, src_name)
                node = self.nodes[self.nodes.add_inode(
                    src_name, parent_inode)]
            return self.__getattr(self.nodes.add_inode(name, parent_inode, data=node.get_data()))

        # raise FUSEError(errno.ENOENT)

        self.log.warning(
            "No swap file either. Returning empty EntryAttributs with timeout.")
        attr = pyfuse3.EntryAttributes()
        attr.st_ino = 0
        attr.entry_timeout = 5

        return attr

    @wrapper(1)
    async def open(self, inode, flags, ctx):
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
        assert flags & os.O_CREAT == 0
        if not (flags & os.O_RDWR or flags & os.O_RDONLY or flags & os.O_WRONLY or flags & os.O_APPEND):
            self.log.error("False permission.")
            self.log.debug("read write: %d", flags & os.O_RDWR)
            self.log.debug("read only: %d", flags & os.O_RDONLY)
            self.log.debug("read write: %d", flags & os.O_WRONLY)
            self.log.debug("append: %d", flags & os.O_APPEND)
            self.log.debug("whole flags: %s", oct(flags))
            # raise pyfuse3.FUSEError(errno.EPERM)
        self.nodes.try_increase_op_count(inode)
        return pyfuse3.FileInfo(fh=inode)

    @wrapper(1)
    async def read(self, inode, off, size):
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
    @wrapper(2)
    async def create(self, parent_inode, name, mode, flags, ctx):
        '''Create a file with permissions *mode* and open it with *flags*
        *ctx* will be a `RequestContext` instance.
        The method must return a tuple of the form *(fh, attr)*, where *fh* is a
        file handle like the one returned by `open` and *attr* is an
        `EntryAttributes` instance with the attributes of the newly created
        directory entry.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
        '''

        # TODO: If name already exists, what should be done?

        if name.decode("utf-8")[-4:] == ".swp":
            self.log.debug("Creating a swap file.")
        try:
            self.log.debug("Trying to get inode")
            inode = self.nodes.add_inode(name, parent_inode, mode=mode)
            self.log.debug("Got inode %d", inode)
            attr = self.__getattr(inode)
            self.log.debug("got attributes for inode %d", inode)
            self.log.debug(str(attr))
        except Exception as e:
            self.log.error(e)
            self.log.error("Create Failed")

        return (inode, attr)

    @wrapper(1, 2)
    async def write(self, inode, off, buf):
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
            data = node.get_data(encoding=Encodings.UTF_8_ENCODING)
            self.log.debug("data: %s", data)
            buffer = buf.decode("utf-8")
            self.log.debug("buffer: %s", buffer)
            output = data[:off] + buffer + data[off:]
            self.log.debug("output: %s", output)
            self.nodes[inode].data = output
        except KeyError:
            self.log.warning("Inode %d does not exist.", inode)
        except Exception as e:
            self.log.error(e)
            self.log.error("Write was not successful.")
        return len(buf)

    @wrapper(1)
    async def access(self, inode, mode, ctx):
        '''Check if requesting process has *mode* rights on *inode*.
        *ctx* will be a `RequestContext` instance.
        The method must return a boolean value.
        If the ``default_permissions`` mount option is given, this method is not
        called.
        When implementing this method, the `get_sup_groups` function may be
        useful.
        '''
        self.log.debug("access: %s", mode)
        # raise FUSEError(errno.ENOSYS)

    @wrapper(1)
    async def release(self, inode):
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
        self.nodes.try_decrease_op_count(inode)

    @wrapper(2)
    async def unlink(self, parent_inode, name, ctx):
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

        children = self.nodes.get_children(parent_inode)
        if len(children) == 0:
            self.log.warning(
                "Found no children for parent_inode %d.", parent_inode)
            return
        for inode in children:
            try:
                if self.nodes[inode].get_name() == name:
                    self.log.info("Lock inode: %d", inode)
                    self.log.info("open_count: %d",
                                  self.nodes[inode].open_count)
                    self.nodes[inode].set_invisible()
                    if self.nodes[inode].open_count <= 1:
                        self.nodes[inode].lock()
            except KeyError:
                self.log.warning("Inode %d does not exist.", inode)

    @wrapper(1)
    async def flush(self, inode):
        '''Handle close() syscall.
        *fh* will by an integer filehandle returned by a prior `open` or
        `create` call.
        This method is called whenever a file descriptor is closed. It may be
        called multiple times for the same open file (e.g. if the file handle
        has been duplicated).
        '''

        # TODO: Really decrease op count?
        # self.try_decrease_op_count(inode)

    @wrapper(1)
    async def forget(self, inode_list):
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
                if self.nodes[inode].open_count > nlookup:
                    self.nodes[inode].dec_open_count(nlookup)
                    self.log.debug("inode %d with lookup count of %d",
                                   inode, self.nodes[inode].open_count)

            except KeyError:  # may have been deleted
                self.log.warning("Inode %d does not exist anymore.", inode)
                pass
            finally:
                self.nodes.try_remove_inode(inode)

    @wrapper(1)
    async def fsync(self, inode, datasync):
        '''Flush buffers for open file *fh*
        If *datasync* is true, only the file contents should be
        flushed (in contrast to the metadata about the file).
        *fh* will by an integer filehandle returned by a prior `open` or
        `create` call.
        '''
        pass

    @wrapper(2)
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
        pass

    @wrapper(2, 4)
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
        # See https://github.com/libfuse/pyfuse3/blob/1730558574361bf7b05b1be2a228a0443deca088/examples/tmpfs.py#L224
        if flags != 0:
            raise FUSEError(errno.EINVAL)

        entry_old = await self.lookup(parent_inode_old, name_old)

        self.log.info(entry_old)
        self.nodes[entry_old.st_ino].parent = parent_inode_new
        self.nodes[entry_old.st_ino].name = name_new
        self.log.info("parent inodes from %d to %d",
                      parent_inode_old, parent_inode_new)
        self.log.info("name from %s to %s", name_old, name_new)
        self.log.info("flags %d", flags)

    @wrapper(1, 3)
    async def link(self, inode, new_parent_inode, new_name, ctx):
        '''Create directory entry *name* in *parent_inode* refering to *inode*.
        *ctx* will be a `RequestContext` instance.
        The method must return an `EntryAttributes` instance with the
        attributes of the newly created directory entry.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
        '''
        pass

    @wrapper(1)
    async def readlink(self, inode, ctx):
        '''Return target of symbolic link *inode*.
        *ctx* will be a `RequestContext` instance.
        '''
        pass

    @wrapper(2)
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
        self.log.debug("With mode: %s", mode)

        inode = self.nodes.add_inode(name, parent_inode, mode=mode)
        return self.__getattr(inode)

    @wrapper(2)
    async def mkdir(self, parent_inode, name, mode, ctx):
        return self.__getattr(self.nodes.add_inode(name, parent_inode,
                                                   node_type=Types.DIR, mode=mode))

    @wrapper(1)
    async def opendir(self, inode, ctx):
        self.nodes.try_increase_op_count(inode)
        return inode

    @wrapper(1)
    async def readdir(self, inode, start_id, token):
        self.log.debug("start_id: %s", start_id)
        dir_path = self.nodes[inode].get_full_path()
        self.log.debug("dirpath: %s", dir_path)
        arr = self.nodes.get_children(inode)
        self.log.debug("items in dir: %d", len(arr))
        try:
            for key in arr:
                node = self.nodes[key]
                self.log.debug("Key: %s, Value_name: %s", key, node.get_name())

                if key <= start_id:
                    continue

                # Omitting swap files.
                if node.type == Types.SWAP:
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

    @wrapper(2)
    async def rmdir(self, parent_inode, name, ctx):
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
            self.log.debug(self.nodes.get_children(parent_inode))

            filtered_list = [idx for idx in self.nodes.get_children(
                parent_inode) if self.nodes[idx].get_name() == name]

            self.log.debug("filtered list with name %s:", name)
            self.log.debug(filtered_list)

            if len(filtered_list) > 1:
                self.log.error("Found more than one node.")
            inode = filtered_list[0]

            # Forget path for readdir. But it will be accessible via getattr, if lookup_count > 1.
            self.nodes[inode].set_invisible()
            if self.nodes[inode].open_count <= 1:
                self.nodes[inode].lock()
        except Exception as e:
            self.log.error(e)

    @wrapper(1)
    async def releasedir(self, inode):
        '''Release open directory
        This method will be called exactly once for each `opendir` call. After
        *fh* has been released, no further `readdir` requests will be received
        for it (until it is opened again with `opendir`).
        '''
        self.nodes[inode].unlock()
        self.nodes.try_decrease_op_count(inode)

    @wrapper(1)
    async def fsyncdir(self, inode, datasync):
        '''Flush buffers for open directory *fh*
        If *datasync* is true, only the directory contents should be
        flushed (in contrast to metadata about the directory itself).
        '''
        pass

    @wrapper()
    async def statfs(self, ctx):
        '''Get file system statistics
        *ctx* will be a `RequestContext` instance.
        The method must return an appropriately filled `StatvfsData` instance.

        See https://linux.die.net/man/2/statvfs
        and https://github.com/libfuse/pyfuse3/blob/1730558574361bf7b05b1be2a228a0443deca088/examples/tmpfs.py#L323
        '''

        stats = pyfuse3.StatvfsData()
        stats.f_bsize = 512
        stats.f_frsize = 512

        size_sum = 0
        for inodes in self.nodes:
            size_sum += self.nodes[inodes].size

        stats.f_blocks = size_sum // stats.f_frsize
        stats.f_bfree = max(size_sum // stats.f_frsize, 1024)
        stats.f_bavail = stats.f_bfree

        count = len(self.nodes)
        stats.f_files = count

        # TODO: Think about max size of filesystem
        stats.f_ffree = max(count, 200)
        stats.f_favail = stats.f_ffree

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

    @wrapper(1)
    async def listxattr(self, inode, ctx):
        '''Get list of extended attributes for *inode*
        *ctx* will be a `RequestContext` instance.
        This method must return a sequence of `bytes` objects.  The objects must
        not include zero-bytes (``\\0``).
        '''
        pass

    @wrapper(1)
    async def removexattr(self, inode, name, ctx):
        '''Remove extended attribute *name* of *inode*
        *ctx* will be a `RequestContext` instance.
        If the attribute does not exist, the method must raise `FUSEError` with
        an error code of `ENOATTR`. *name* will be of type `bytes`, but is
        guaranteed not to contain zero-bytes (``\\0``).
        '''
        pass
