import os
import time
import stat
from enum import Enum

import pyfuse3

from corefs.utils._fs_utils import Encodings, Types


class Node():

    def __init__(self, mode, parent, node_type, open_count):
        self.parent = parent
        self.type = node_type

        # Attributes
        self.mode = mode
        self.size = None

        self.uid = os.getuid()
        self.gid = os.getgid()

        stamp = int(time.time() * 1e9)
        self.atime = stamp
        self.mtime = stamp
        self.ctime = stamp

        # Creating, opening, closing and removing a file, will result in open_count
        self.open_count = open_count

        # Attribute that will skip node at readdir call.
        self.invisible = False

        # If unlink or rmdir -> node needs to exist but ls mustn't show the item
        self.locked = False

        self.xattr = dict()

    def get_permissions(self):
        return stat.S_IMODE(self.mode)

    def has_attr(self):
        return self.size is not None

    def is_invisible(self):
        return self.invisible

    def set_invisible(self, invisible=True):
        self.invisible = invisible

    def inc_open_count(self, amount=1):
        self.open_count += amount

    def dec_open_count(self, amount=1):
        self.open_count -= amount

    def unlock(self):
        self.locked = False

    def lock(self):
        self.locked = True

    def is_locked(self):
        return self.locked

    def to_dict(self):
        return {
            "parent": self.parent,
            "type": self.type.name,
            "mode": oct(self.mode),
            "invisible": self.invisible,
            "open_count": self.open_count,
            "lock": self.locked
        }

    def __repr__(self):
        return "Node(parent: {0}, type: {1}, mode: {2}, invisible: {3}, open_count: {4}, lock: {5})".format(
            self.parent, self.type.name, oct(self.mode), self.invisible, self.open_count, self.locked)


class LockedNode():

    def __init__(self, node, entry):
        self.inode = entry.inode
        self.name = entry.get_name(encoding=Encodings.UTF_8_ENCODING)
        self.path = entry.path
        self.type = node.type.name
        self.mode = node.mode
        self.size = node.size
        self.uid = node.uid
        self.gid = node.gid
        self.atime = node.atime
        self.mtime = node.mtime
        self.ctime = node.ctime


class File(Node):

    def __init__(self, mode, parent=None, data="", unlink=False, open_count=0):
        super().__init__(mode, parent, Types.FILE, open_count=open_count)
        self._data = data
        self.mode = self.mode | stat.S_IFREG

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        if data is None:
            data = ""
        self._data = os.fsencode(data)
        self.size = self.get_data_size()

    def get_data(self, encoding=Encodings.BYTE_ENCODING):
        if encoding == Encodings.BYTE_ENCODING:
            return self._data
        else:
            return os.fsdecode(self._data)

    def get_data_size(self, encoding=Encodings.UTF_8_ENCODING):
        return len(self.get_data(encoding=encoding))

    def to_dict(self):
        return {
            **super().to_dict(),
            "data": self._data
        }

    def __repr__(self):
        return "File(mode: {0}, ".format(oct(self.mode)) +\
            "data: {0}, ".format(self._data) +\
            "open_count: {0}, ".format(self.open_count) +\
            "invisible: {0}, ".format(self.invisible) +\
            "lock: {0})".format(self.locked)


class LinkedFile(File):

    def __init__(self, mode, parent=None, data="", unlink=False, open_count=0):
        super().__init__(mode, parent, data, unlink, open_count=open_count)
        self.mode = mode


class LockedFile(LockedNode):

    def __init__(self, node, entry):
        super().__init__(node, entry)
        self.data = node.get_data(encoding=Encodings.UTF_8_ENCODING)


class Directory(Node):

    def __init__(self, mode, parent=None, unlink=False, root=False, open_count=0):
        super().__init__(mode, parent, Types.DIR, open_count=open_count)
        self.root = root
        self.mode = self.mode | stat.S_IFDIR
        self.size = 0

    def is_root(self):
        return self.root

    def to_dict(self):
        return {
            **super().to_dict(),
            "root": self.root
        }

    def __repr__(self):
        return "Directory(mode: {0}, ".format(oct(self.mode)) +\
            "root: {0}, ".format(self.root) +\
            "open_count: {0}, ".format(self.open_count) +\
            "invisible: {0}, ".format(self.invisible) +\
            "lock: {0})".format(self.locked)


class LinkedDirectory(Directory):

    def __init__(self, mode, parent=None, unlink=False, root=False, open_count=0):
        super().__init__(mode, parent, unlink, root, open_count)
        self.mode = mode


class LockedDirectory(LockedNode):

    def __init__(self, node, entry):
        super().__init__(node, entry)
        self.root = node.is_root()

    def is_root(self):
        return self.root
