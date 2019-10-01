import os
import pyfuse3

BYTE_ENCODING = 0
UTF_8_ENCODING = 1

FILE_TYPE = 0
DIR_TYPE = 1
SWAP_TYPE = 2

# TODO: could use fsdecode and fsencode rather than actual utf-8 and byte encoding / decoding


class Node():

    def __init__(self, name, path, parent, file_type, attr, open_count):
        self.set_name(name)
        self.path = path
        self.parent = parent
        self.type = file_type
        self.attr = attr

        # Creating, opening, closing and removing a file, will result in open_count
        self.open_count = open_count

        # Attribute that will skip node at readdir call.
        self.invisible = False

        # TODO: Currently not implemented, because unlink and rmdir try to remove the node at the end.
        # If unlink or rmdir -> node needs to exist but ls mustn't show the item
        self.locked = False

    def set_name(self, name):
        if type(name) is str:
            name = name.encode("utf-8")
        self.name = name

    def get_name(self, encoding=BYTE_ENCODING):
        if encoding == BYTE_ENCODING:
            return self.name
        else:
            return self.name.decode("utf-8")

    def set_path(self, path):
        self.path = path

    def get_path(self):
        return self.path

    def get_full_path(self):
        return self.path + self.get_name(encoding=UTF_8_ENCODING)

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
            "parent": self.parent,
            "type": self.type,
            "invisible": self.invisible,
            "open_count": self.open_count,
            "lock": self.locked
        }

    def __repr__(self):
        return "Node(name: {0}, path: {1}, type: {2}, invisible: {3}, open_count: {4}, lock: {5})".format(
            self.name, self.path, self.type, self.invisible, self.open_count, self.locked)


class File(Node):

    def __init__(self, name, path, parent=0, data="", attr=None, unlink=False, open_count=0):
        super().__init__(name, path, parent, FILE_TYPE,
                         attr=attr, open_count=open_count)
        self.set_data(data)
        if self.get_name(encoding=UTF_8_ENCODING).endswith(".swp"):
            self.set_type(SWAP_TYPE)

    def set_data(self, data):
        if data is None:
            data = ""
        if type(data) is str:
            data = data.encode("utf-8")
        self.data = data

    def get_data(self, encoding=BYTE_ENCODING):
        if encoding == BYTE_ENCODING:
            return self.data
        else:
            return self.data.decode("utf-8")

    def get_data_size(self, encoding=UTF_8_ENCODING):
        return len(self.get_data(encoding=encoding))

    def to_dict(self):
        return {
            **super().to_dict(),
            "data": self.data
        }

    def __repr__(self):
        return "File(name: {0}, ".format(self.name) +\
            "path: {0}, ".format(self.path) +\
            "parent: {0}, ".format(self.parent) +\
            "attr: {0}, ".format(self.attr) +\
            "type: {0}, ".format(self.type) +\
            "data: {0}, ".format(self.data) +\
            "open_count: {0}, ".format(self.open_count) +\
            "invisible: {0}, ".format(self.invisible) +\
            "lock: {0})".format(self.locked)


class Directory(Node):

    def __init__(self, name, path, parent=0, attr=None, unlink=False, root=False, open_count=0):
        super().__init__(name, path, parent, DIR_TYPE,
                         attr=attr, open_count=open_count)
        self.root = root

    def is_root(self):
        return self.root

    def get_full_path(self):
        if self.is_root():
            return self.path + os.sep
        return self.path + self.get_name(encoding=UTF_8_ENCODING)

    def to_dict(self):
        return {
            **super().to_dict()
        }

    def __repr__(self):
        return "Directory(name: {0}, ".format(self.name) +\
            "path: {0}, ".format(self.path) +\
            "parent: {0}, ".format(self.parent) +\
            "attr: {0}, ".format(self.attr) +\
            "type: {0}, ".format(self.type) +\
            "root: {0}, ".format(self.root) +\
            "open_count: {0}, ".format(self.open_count) +\
            "invisible: {0}, ".format(self.invisible) +\
            "lock: {0})".format(self.locked)


class EntryAttributes(pyfuse3.EntryAttributes):

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return "EntryAttributes(st_ino: {0})".format(self.st_ino)
