#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Using code and comments of https://github.com/libfuse/pyfuse3/blob/master/examples/passthroughfs.py
'''

import os
import sys

# If we are running from the pyfuse3 source directory, try
# to load the module from there first.
# basedir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
# if (os.path.exists(os.path.join(basedir, 'setup.py')) and
#    os.path.exists(os.path.join(basedir, 'src', 'pyfuse3.pyx'))):
#    sys.path.insert(0, os.path.join(basedir, 'src'))

from argparse import ArgumentParser
import stat as stat_m
import logging
import errno
import pyfuse3
import trio
import faulthandler
from pyfuse3 import FUSEError
from os import fsencode, fsdecode
from collections import defaultdict

faulthandler.enable()

log = logging.getLogger(__name__)

FUSEError = None


class TestFs(pyfuse3.Operations):

    enable_writeback_cache = True

    def __init__(self, mnt_point):
        super().__init__()
        self.mnt_point = mnt_point
        self._inode_path_map = {
            # pyfuse3.ROOT_INODE: os.path.abspath(os.path.join(".", mnt_point))
        }
        self._lookup_cnt = defaultdict(lambda: 0)
        self._fd_inode_map = dict()
        self._inode_fd_map = dict()
        self._fd_open_count = dict()

    def _inode_to_path(self, inode):
        try:
            if inode == pyfuse3.ROOT_INODE:
                os.lstat(os.path.abspath(os.path.join(".", self.mnt_point)))
                val = os.path.abspath(os.path.join(".", self.mnt_point))
            else:
                val = self._inode_path_map[inode]
        except KeyError:
            raise FUSEError(errno.ENOENT)
        if isinstance(val, set):
            # In case of hardlinks, pick any path
            val = next(iter(val))
        log.info("Inode to Path: " + val)
        return val

    def _add_path(self, inode, path):
        log.info('_add_path for %d, %s', inode, path)
        self._lookup_cnt[inode] += 1

        # With hardlinks, one inode may map to multiple paths.
        if inode not in self._inode_path_map and inode is not pyfuse3.ROOT_INODE:
            self._inode_path_map[inode] = path
            return

        val = self._inode_path_map[inode]
        if isinstance(val, set):
            val.add(path)
        elif val != path:
            self._inode_path_map[inode] = {path, val}

    async def lookup(self, parent_inode, name, ctx=None):
        log.info("lookup")
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
        name = fsdecode(name)
        log.debug('lookup for %s in %d', name, parent_inode)
        path = os.path.join(self._inode_to_path(parent_inode), name)
        attr = self._getattr(path=path)
        if name != '.' and name != '..':
            self._add_path(attr.st_ino, path)
        return attr

    async def forget(self, inode_list):
        log.info("forget")
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
            log.debug('forgetting about inode %d', inode)
            assert inode not in self._inode_fd_map
            del self._lookup_cnt[inode]
            try:
                del self._inode_path_map[inode]
            except KeyError:  # may have been deleted
                pass

    async def getattr(self, inode, ctx=None):
        log.info("getattr")
        '''Get attributes for *inode*
        *ctx* will be a `RequestContext` instance.
        This method should return an `EntryAttributes` instance with the
        attributes of *inode*. The `~EntryAttributes.entry_timeout` attribute is
        ignored in this context.
        '''
        if inode in self._inode_fd_map:
            return self._getattr(fd=self._inode_fd_map[inode])
        else:
            return self._getattr(path=self._inode_to_path(inode))

    def _getattr(self, path=None, fd=None):
        assert fd is None or path is None
        assert not(fd is None and path is None)
        log.info("Path: " + path)
        try:
            if fd is None:
                log.info("before stat")
                stat = os.lstat(path)
                log.info("got stat")
            else:
                stat = os.fstat(fd)
        except OSError as exc:
            log.error("OSERROR")
            raise FUSEError(exc.errno)
        log.info("Found stat")
        entry = pyfuse3.EntryAttributes()
        for attr in ('st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
                     'st_rdev', 'st_size', 'st_atime_ns', 'st_mtime_ns',
                     'st_ctime_ns'):
            setattr(entry, attr, getattr(stat, attr))
        entry.generation = 0
        entry.entry_timeout = 0
        entry.attr_timeout = 0
        entry.st_blksize = 512
        entry.st_blocks = (
            (entry.st_size+entry.st_blksize-1) // entry.st_blksize)

        log.info("Set entries")
        return entry

    async def setattr(self, inode, attr, fields, fh, ctx):
        log.info("setattr")
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
        # We use the f* functions if possible so that we can handle
        # a setattr() call for an inode without associated directory
        # handle.
        if fh is None:
            path_or_fh = self._inode_to_path(inode)
            truncate = os.truncate
            chmod = os.chmod
            chown = os.chown
            stat = os.lstat
        else:
            path_or_fh = fh
            truncate = os.ftruncate
            chmod = os.fchmod
            chown = os.fchown
            stat = os.fstat

        try:
            if fields.update_size:
                truncate(path_or_fh, attr.st_size)

            if fields.update_mode:
                # Under Linux, chmod always resolves symlinks so we should
                # actually never get a setattr() request for a symbolic
                # link.
                assert not stat_m.S_ISLNK(attr.st_mode)
                chmod(path_or_fh, stat_m.S_IMODE(attr.st_mode))

            if fields.update_uid:
                chown(path_or_fh, attr.st_uid, -1, follow_symlinks=False)

            if fields.update_gid:
                chown(path_or_fh, -1, attr.st_gid, follow_symlinks=False)

            if fields.update_atime and fields.update_mtime:
                if fh is None:
                    os.utime(path_or_fh, None, follow_symlinks=False,
                             ns=(attr.st_atime_ns, attr.st_mtime_ns))
                else:
                    os.utime(path_or_fh, None,
                             ns=(attr.st_atime_ns, attr.st_mtime_ns))
            elif fields.update_atime or fields.update_mtime:
                # We can only set both values, so we first need to retrieve the
                # one that we shouldn't be changing.
                oldstat = stat(path_or_fh)
                if not fields.update_atime:
                    attr.st_atime_ns = oldstat.st_atime_ns
                else:
                    attr.st_mtime_ns = oldstat.st_mtime_ns
                if fh is None:
                    os.utime(path_or_fh, None, follow_symlinks=False,
                             ns=(attr.st_atime_ns, attr.st_mtime_ns))
                else:
                    os.utime(path_or_fh, None,
                             ns=(attr.st_atime_ns, attr.st_mtime_ns))

        except OSError as exc:
            raise FUSEError(exc.errno)

        return await self.getattr(inode)

    async def readlink(self, inode, ctx):
        log.info("readlink")
        '''Return target of symbolic link *inode*.
        *ctx* will be a `RequestContext` instance.
        '''
        path = self._inode_to_path(inode)
        try:
            target = os.readlink(path)
        except OSError as exc:
            raise FUSEError(exc.errno)
        return fsencode(target)

    async def mknod(self, parent_inode, name, mode, rdev, ctx):
        log.info("mknod")
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
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        try:
            os.mknod(path, mode=(mode & ~ctx.umask), device=rdev)
            os.chown(path, ctx.uid, ctx.gid)
        except OSError as exc:
            raise FUSEError(exc.errno)
        attr = self._getattr(path=path)
        self._add_path(attr.st_ino, path)
        return attr

    async def mkdir(self, parent_inode, name, mode, ctx):
        log.info("mkdir")
        '''Create a directory
        This method must create a new directory *name* with mode *mode* in the
        directory with inode *parent_inode*. *ctx* will be a `RequestContext`
        instance.
        This method must return an `EntryAttributes` instance with the
        attributes of the newly created directory entry.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
        '''
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        try:
            os.mkdir(path, mode=(mode & ~ctx.umask))
            os.chown(path, ctx.uid, ctx.gid)
        except OSError as exc:
            raise FUSEError(exc.errno)
        attr = self._getattr(path=path)
        self._add_path(attr.st_ino, path)
        return attr

    async def unlink(self, parent_inode, name, ctx):
        log.info("unlink")
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
        name = fsdecode(name)
        parent = self._inode_to_path(inode_p)
        path = os.path.join(parent, name)
        try:
            inode = os.lstat(path).st_ino
            os.unlink(path)
        except OSError as exc:
            raise FUSEError(exc.errno)
        if inode in self._lookup_cnt:
            self._forget_path(inode, path)

    async def rmdir(self, parent_inode, name, ctx):
        log.info("rmdir")
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
        name = fsdecode(name)
        parent = self._inode_to_path(inode_p)
        path = os.path.join(parent, name)
        try:
            inode = os.lstat(path).st_ino
            os.rmdir(path)
        except OSError as exc:
            raise FUSEError(exc.errno)
        if inode in self._lookup_cnt:
            self._forget_path(inode, path)

    async def symlink(self, parent_inode, name, target, ctx):
        log.info("symlink")
        '''Create a symbolic link
        This method must create a symbolink link named *name* in the directory
        with inode *parent_inode*, pointing to *target*.  *ctx* will be a
        `RequestContext` instance.
        The method must return an `EntryAttributes` instance with the attributes
        of the newly created directory entry.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
        '''
        name = fsdecode(name)
        target = fsdecode(target)
        parent = self._inode_to_path(inode_p)
        path = os.path.join(parent, name)
        try:
            os.symlink(target, path)
            os.chown(path, ctx.uid, ctx.gid, follow_symlinks=False)
        except OSError as exc:
            raise FUSEError(exc.errno)
        stat = os.lstat(path)
        self._add_path(stat.st_ino, path)
        return await self.getattr(stat.st_ino)

    async def rename(self, parent_inode_old, name_old, parent_inode_new,
                     name_new, flags, ctx):
        log.info("rename")
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
        if flags != 0:
            raise FUSEError(errno.EINVAL)

        name_old = fsdecode(name_old)
        name_new = fsdecode(name_new)
        parent_old = self._inode_to_path(inode_p_old)
        parent_new = self._inode_to_path(inode_p_new)
        path_old = os.path.join(parent_old, name_old)
        path_new = os.path.join(parent_new, name_new)
        try:
            os.rename(path_old, path_new)
            inode = os.lstat(path_new).st_ino
        except OSError as exc:
            raise FUSEError(exc.errno)
        if inode not in self._lookup_cnt:
            return

        val = self._inode_path_map[inode]
        if isinstance(val, set):
            assert len(val) > 1
            val.add(path_new)
            val.remove(path_old)
        else:
            assert val == path_old
        self._inode_path_map[inode] = path_new

    async def link(self, inode, new_parent_inode, new_name, ctx):
        log.info("link")
        '''Create directory entry *name* in *parent_inode* refering to *inode*.
        *ctx* will be a `RequestContext` instance.
        The method must return an `EntryAttributes` instance with the
        attributes of the newly created directory entry.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
        '''
        new_name = fsdecode(new_name)
        parent = self._inode_to_path(new_inode_p)
        path = os.path.join(parent, new_name)
        try:
            os.link(self._inode_to_path(inode), path, follow_symlinks=False)
        except OSError as exc:
            raise FUSEError(exc.errno)
        self._add_path(inode, path)
        return await self.getattr(inode)

    async def open(self, inode, flags, ctx):
        log.info("open")
        '''Open a inode *inode* with *flags*.
        *ctx* will be a `RequestContext` instance.
        *flags* will be a bitwise or of the open flags described in the
        :manpage:`open(2)` manpage and defined in the `os` module (with the
        exception of ``O_CREAT``, ``O_EXCL``, ``O_NOCTTY`` and ``O_TRUNC``)
        This method must return an integer file handle. The file handle will be
        passed to the `read`, `write`, `flush`, `fsync` and `release` methods to
        identify the open file.
        '''
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

    async def read(self, fd, off, size):
        log.info("read")
        '''Read *size* bytes from *fh* at position *off*
        *fh* will by an integer filehandle returned by a prior `open` or
        `create` call.
        This function should return exactly the number of bytes requested except
        on EOF or error, otherwise the rest of the data will be substituted with
        zeroes.
        '''
        os.lseek(fd, offset, os.SEEK_SET)
        return os.read(fd, length)

    async def write(self, fd, off, buf):
        log.info("write")
        '''Write *buf* into *fh* at *off*
        *fh* will by an integer filehandle returned by a prior `open` or
        `create` call.
        This method must return the number of bytes written. However, unless the
        file system has been mounted with the ``direct_io`` option, the file
        system *must* always write *all* the provided data (i.e., return
        ``len(buf)``).
        '''
        os.lseek(fd, offset, os.SEEK_SET)
        return os.write(fd, buf)

    async def flush(self, fh):
        log.info("flush")
        '''Handle close() syscall.
        *fh* will by an integer filehandle returned by a prior `open` or
        `create` call.
        This method is called whenever a file descriptor is closed. It may be
        called multiple times for the same open file (e.g. if the file handle
        has been duplicated).
        '''

        raise FUSEError(errno.ENOSYS)

    async def release(self, fh):
        log.info("release")
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

    async def fsync(self, fh, datasync):
        log.info("fsync")
        '''Flush buffers for open file *fh*
        If *datasync* is true, only the file contents should be
        flushed (in contrast to the metadata about the file).
        *fh* will by an integer filehandle returned by a prior `open` or
        `create` call.
        '''
        raise FUSEError(errno.ENOSYS)

    async def opendir(self, inode, ctx):
        log.info("opendir")
        '''Open the directory with inode *inode*
        *ctx* will be a `RequestContext` instance.
        This method should return an integer file handle. The file handle will
        be passed to the `readdir`, `fsyncdir` and `releasedir` methods to
        identify the directory.
        '''
        return inode

    # original head was readdir(self, fh, start_id, token):
    async def readdir(self, inode, start_id, token):
        log.info("readdir")
        '''Read entries in open directory *fh*.
        This method should list the contents of directory *fh* (as returned by a
        prior `opendir` call), starting at the entry identified by *start_id*.
        Instead of returning the directory entries directly, the method must
        call `readdir_reply` for each directory entry. If `readdir_reply`
        returns True, the file system must increase the lookup count for the
        provided directory entry by one and call `readdir_reply` again for the
        next entry (if any). If `readdir_reply` returns False, the lookup count
        must *not* be increased and the method should return without further
        calls to `readdir_reply`.
        The *start_id* parameter will be either zero (in which case listing
        should begin with the first entry) or it will correspond to a value that
        was previously passed by the file system to the `readdir_reply`
        function in the *next_id* parameter.
        If entries are added or removed during a `readdir` cycle, they may or
        may not be returned. However, they must not cause other entries to be
        skipped or returned more than once.
        :file:`.` and :file:`..` entries may be included but are not
        required. However, if they are reported the filesystem *must not*
        increase the lookup count for the corresponding inodes (even if
        `readdir_reply` returns True).
        '''
        path = self._inode_to_path(inode)
        log.debug('reading %s', path)
        entries = []
        for name in os.listdir(path):
            if name == '.' or name == '..':
                continue
            attr = self._getattr(path=os.path.join(path, name))
            entries.append((attr.st_ino, name, attr))

        log.debug('read %d entries, starting at %d', len(entries), start_id)

        # This is not fully posix compatible. If there are hardlinks
        # (two names with the same inode), we don't have a unique
        # offset to start in between them. Note that we cannot simply
        # count entries, because then we would skip over entries
        # (or return them more than once) if the number of directory
        # entries changes between two calls to readdir().
        for (ino, name, attr) in sorted(entries):
            if ino <= start_id:
                continue
            if not pyfuse3.readdir_reply(token, fsencode(name), attr, ino):
                break
        self._add_path(attr.st_ino, os.path.join(path, name))

    async def releasedir(self, fh):
        log.info("releasedir")
        '''Release open directory
        This method will be called exactly once for each `opendir` call. After
        *fh* has been released, no further `readdir` requests will be received
        for it (until it is opened again with `opendir`).
        '''

        raise FUSEError(errno.ENOSYS)

    async def fsyncdir(self, fh, datasync):
        log.info("fsyncdir")
        '''Flush buffers for open directory *fh*
        If *datasync* is true, only the directory contents should be
        flushed (in contrast to metadata about the directory itself).
        '''

        raise FUSEError(errno.ENOSYS)

    async def statfs(self, ctx):
        log.info("statfs")
        '''Get file system statistics
        *ctx* will be a `RequestContext` instance.
        The method must return an appropriately filled `StatvfsData` instance.
        '''
        root = self._inode_path_map[pyfuse3.ROOT_INODE]
        stat_ = pyfuse3.StatvfsData()
        try:
            statfs = os.statvfs(root)
        except OSError as exc:
            raise FUSEError(exc.errno)
        for attr in ('f_bsize', 'f_frsize', 'f_blocks', 'f_bfree', 'f_bavail',
                     'f_files', 'f_ffree', 'f_favail'):
            setattr(stat_, attr, getattr(statfs, attr))
        stat_.f_namemax = statfs.f_namemax - (len(root)+1)
        return stat_

    def stacktrace(self):
        '''Asynchronous debugging
        This method will be called when the ``fuse_stacktrace`` extended
        attribute is set on the mountpoint. The default implementation logs the
        current stack trace of every running Python thread. This can be quite
        useful to debug file system deadlocks.
        '''

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

        log.error("\n".join(code))

    async def setxattr(self, inode, name, value, ctx):
        log.info("setxattr")
        '''Set extended attribute *name* of *inode* to *value*.
        *ctx* will be a `RequestContext` instance.
        The attribute may or may not exist already. Both *name* and *value* will
        be of type `bytes`. *name* is guaranteed not to contain zero-bytes
        (``\\0``).
        '''

        raise FUSEError(errno.ENOSYS)

    async def getxattr(self, inode, name, ctx):
        log.info("getxattr")
        '''Return extended attribute *name* of *inode*
        *ctx* will be a `RequestContext` instance.
        If the attribute does not exist, the method must raise `FUSEError` with
        an error code of `ENOATTR`. *name* will be of type `bytes`, but is
        guaranteed not to contain zero-bytes (``\\0``).
        '''

        raise FUSEError(errno.ENOSYS)

    async def listxattr(self, inode, ctx):
        log.info("listxattr")
        '''Get list of extended attributes for *inode*
        *ctx* will be a `RequestContext` instance.
        This method must return a sequence of `bytes` objects.  The objects must
        not include zero-bytes (``\\0``).
        '''

        raise FUSEError(errno.ENOSYS)

    async def removexattr(self, inode, name, ctx):
        log.info("removexattr")
        '''Remove extended attribute *name* of *inode*
        *ctx* will be a `RequestContext` instance.
        If the attribute does not exist, the method must raise `FUSEError` with
        an error code of `ENOATTR`. *name* will be of type `bytes`, but is
        guaranteed not to contain zero-bytes (``\\0``).
        '''

        raise FUSEError(errno.ENOSYS)

    async def access(self, inode, mode, ctx):
        log.info("Access")
        '''Check if requesting process has *mode* rights on *inode*.
        *ctx* will be a `RequestContext` instance.
        The method must return a boolean value.
        If the ``default_permissions`` mount option is given, this method is not
        called.
        When implementing this method, the `get_sup_groups` function may be
        useful.
        '''
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

    async def create(self, parent_inode, name, mode, flags, ctx):
        log.info("Create")
        '''Create a file with permissions *mode* and open it with *flags*
        *ctx* will be a `RequestContext` instance.
        The method must return a tuple of the form *(fh, attr)*, where *fh* is a
        file handle like the one returned by `open` and *attr* is an
        `EntryAttributes` instance with the attributes of the newly created
        directory entry.
        (Successful) execution of this handler increases the lookup count for
        the returned inode by one.
        '''
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

    def _forget_path(self, inode, path):
        log.debug('forget %s for %d', path, inode)
        val = self._inode_path_map[inode]
        if isinstance(val, set):
            val.remove(path)
            if len(val) == 1:
                self._inode_path_map[inode] = next(iter(val))
        else:
            del self._inode_path_map[inode]


def init_logging(debug=False):
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(threadName)s: '
                                  '[%(name)s] %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.StreamHandler()  # FileHandler("fuse3.log")
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

    log.info("Mountpoint: " + options.mountpoint)
    testfs = TestFs(options.mountpoint)
    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('fsname=test')

    if options.debug_fuse:
        fuse_options.add('debug')
    pyfuse3.init(testfs, options.mountpoint, fuse_options)
    try:
        trio.run(pyfuse3.main)
        # test
        # os.mkdir(os.path.join("dir", "sub"))
        # os.open(os.path.join("dir", "bob.data"), os.O_CREAT)
        # print("hello loop")
    except:
        pyfuse3.close(unmount=False)
        raise

    pyfuse3.close()


if __name__ == '__main__':
    main()
