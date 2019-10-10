import os
import pyfuse3
from enum import Enum


class Encodings(Enum):
    BYTE_ENCODING = 0  # filesystem encoding
    UTF_8_ENCODING = 1


class Types(Enum):
    FILE = 0
    DIR = 1
    SWAP = 2


class Node():

    def __init__(self, name, path, mode, parent, file_type, attr, open_count):
        self.set_name(name)
        self.set_path(path)
        self.parent = parent
        self.set_type(file_type)
        self.set_attr(attr)

        # TODO: Add mode
        self.mode = mode

        # Creating, opening, closing and removing a file, will result in open_count
        self.open_count = open_count

        # Attribute that will skip node at readdir call.
        self.invisible = False

        # If unlink or rmdir -> node needs to exist but ls mustn't show the item
        self.locked = False

    def set_name(self, name):
        self.name = os.fsencode(name)

    def get_name(self, encoding=Encodings.BYTE_ENCODING):
        if encoding == Encodings.BYTE_ENCODING:
            return self.name
        else:
            return os.fsdecode(self.name)

    def set_path(self, path):
        self.path = path

    def get_path(self):
        return self.path

    def get_full_path(self):
        return self.path + self.get_name(encoding=Encodings.UTF_8_ENCODING)

    def get_mode(self):
        return self.mode

    def set_parent(self, new_parent):
        self.parent = new_parent

    def get_parent(self):
        return self.parent

    def set_type(self, file_type):
        self.type = file_type

    def get_type(self):
        return self.type

    def set_attr(self, attr):
        self.attr = attr

    def get_attr(self):
        return self.attr

    def has_attr(self):
        return self.attr is not None

    def is_invisible(self):
        return self.invisible

    def set_invisible(self, invisible=True):
        self.invisible = invisible

    def inc_open_count(self, amount=1):
        self.open_count += amount

    def dec_open_count(self, amount=1):
        self.open_count -= amount

    def get_open_count(self):
        return self.open_count

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
            "mode": self.mode,
            "parent": self.parent,
            "type": self.type.name,
            "invisible": self.invisible,
            "open_count": self.open_count,
            "lock": self.locked
        }

    def __repr__(self):
        return "Node(name: {0}, path: {1}, type: {2}, mode: {3}, invisible: {4}, open_count: {5}, lock: {6})".format(
            self.name, self.path, self.type.name, self.mode, self.invisible, self.open_count, self.locked)


class LockedNode():

    def __init__(self, node):
        self.name = node.get_name(encoding=Encodings.UTF_8_ENCODING)
        self.path = node.get_path()
        self.type = node.get_type().name
        self.mode = node.get_mode()

    def get_name(self):
        return self.name

    def get_path(self):
        return self.path

    def get_type(self):
        return self.type

    def get_mode(self):
        return self.mode


class File(Node):

    def __init__(self, name, path, mode=7777, parent=0, data="", attr=None, unlink=False, open_count=0):
        super().__init__(name, path, mode, parent, Types.FILE,
                         attr=attr, open_count=open_count)
        self.set_data(data)
        if self.get_name(encoding=Encodings.UTF_8_ENCODING).endswith(".swp"):
            self.set_type(Types.SWAP)

    def set_data(self, data):
        if data is None:
            data = ""
        self.data = os.fsencode(data)

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
            "mode: {0}, ".format(self.mode) +\
            "parent: {0}, ".format(self.parent) +\
            "attr: {0}, ".format(self.attr) +\
            "type: {0}, ".format(self.type.name) +\
            "data: {0}, ".format(self.data) +\
            "open_count: {0}, ".format(self.open_count) +\
            "invisible: {0}, ".format(self.invisible) +\
            "lock: {0})".format(self.locked)


class LockedFile(LockedNode):

    def __init__(self, node):
        super().__init__(node)
        self.data = node.get_data(encoding=Encodings.UTF_8_ENCODING)

    def get_data(self):
        return self.data


class Directory(Node):

    def __init__(self, name, path, mode=7777, parent=0, attr=None, unlink=False, root=False, open_count=0):
        super().__init__(name, path, mode, parent, Types.DIR,
                         attr=attr, open_count=open_count)
        self.root = root

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
            "mode: {0}, ".format(self.mode) +\
            "parent: {0}, ".format(self.parent) +\
            "attr: {0}, ".format(self.attr) +\
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


class EntryAttributes(pyfuse3.EntryAttributes):

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return "EntryAttributes(st_ino: {0})".format(self.st_ino)
