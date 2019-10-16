import os
import time
import stat
from enum import Enum

import pyfuse3


class Encodings(Enum):
    BYTE_ENCODING = 0  # filesystem encoding
    UTF_8_ENCODING = 1


class Types(Enum):
    FILE = 0
    DIR = 1
    SWAP = 2


class Node():

    def __init__(self, name, path, mode, parent, file_type, open_count):
        self._name = name
        self.path = path
        self.parent = parent
        self.type = file_type

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

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = os.fsencode(name)

    def get_name(self, encoding=Encodings.BYTE_ENCODING):
        if encoding == Encodings.BYTE_ENCODING:
            return self._name
        else:
            return os.fsdecode(self._name)

    def get_full_path(self):
        return self.path + self.get_name(encoding=Encodings.UTF_8_ENCODING)

    def get_attr(self, inode):
        entry = pyfuse3.EntryAttributes()
        entry.st_mode = self.mode
        entry.st_size = self.size
        entry.st_atime_ns = self.atime
        entry.st_ctime_ns = self.ctime
        entry.st_mtime_ns = self.mtime
        entry.st_gid = os.getgid()
        entry.st_uid = os.getuid()
        entry.st_ino = inode
        return entry

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
            "name": self.name,
            "path": self.path,
            "mode": oct(self.mode),
            "parent": self.parent,
            "type": self.type.name,
            "invisible": self.invisible,
            "open_count": self.open_count,
            "lock": self.locked
        }

    def __repr__(self):
        return "Node(name: {0}, path: {1}, type: {2}, mode: {3}, invisible: {4}, open_count: {5}, lock: {6})".format(
            self.name, self.path, self.type.name, oct(self.mode), self.invisible, self.open_count, self.locked)


class LockedNode():

    def __init__(self, node):
        self.name = node.get_name(encoding=Encodings.UTF_8_ENCODING)
        self.path = node.path
        self.type = node.type.name
        self.mode = node.mode
        self.size = node.size
        self.uid = node.uid
        self.gid = node.gid
        self.atime = node.atime
        self.mtime = node.mtime
        self.ctime = node.ctime


class File(Node):

    def __init__(self, name, path, mode, parent=None, data="", unlink=False, open_count=0):
        super().__init__(name, path, mode,
                         parent, Types.FILE, open_count=open_count)
        self.data = data
        if self.get_name(encoding=Encodings.UTF_8_ENCODING).endswith(".swp"):
            self.type = Types.SWAP

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
            return self.data
        else:
            return os.fsdecode(self.data)

    def get_data_size(self, encoding=Encodings.UTF_8_ENCODING):
        return len(self.get_data(encoding=encoding))

    def to_dict(self):
        return {
            **super().to_dict(),
            "data": self.data
        }

    def __repr__(self):
        return "File(name: {0}, ".format(self.name) +\
            "path: {0}, ".format(self.path) +\
            "mode: {0}, ".format(oct(self.mode)) +\
            "parent: {0}, ".format(self.parent) +\
            "type: {0}, ".format(self.type.name) +\
            "data: {0}, ".format(self.data) +\
            "open_count: {0}, ".format(self.open_count) +\
            "invisible: {0}, ".format(self.invisible) +\
            "lock: {0})".format(self.locked)


class LockedFile(LockedNode):

    def __init__(self, node):
        super().__init__(node)
        self.data = node.get_data(encoding=Encodings.UTF_8_ENCODING)


class Directory(Node):

    def __init__(self, name, path, mode, parent=None, unlink=False, root=False, open_count=0):
        super().__init__(name, path, mode, parent, Types.DIR, open_count=open_count)
        self.root = root
        self.mode = self.mode | stat.S_IFDIR
        self.size = 0

    def is_root(self):
        return self.root

    def get_full_path(self):
        if self.is_root():
            return self.path + os.sep
        return self.path + self.get_name(encoding=Encodings.UTF_8_ENCODING)

    def to_dict(self):
        return {
            **super().to_dict()
        }

    def __repr__(self):
        return "Directory(name: {0}, ".format(self.name) +\
            "path: {0}, ".format(self.path) +\
            "mode: {0}, ".format(oct(self.mode)) +\
            "parent: {0}, ".format(self.parent) +\
            "type: {0}, ".format(self.type.name) +\
            "root: {0}, ".format(self.root) +\
            "open_count: {0}, ".format(self.open_count) +\
            "invisible: {0}, ".format(self.invisible) +\
            "lock: {0})".format(self.locked)


class LockedDirectory(LockedNode):

    def __init__(self, node):
        super().__init__(node)
        self.root = node.is_root()

    def is_root(self):
        return self.root
