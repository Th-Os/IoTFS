import os
import pyfuse3

BYTE_ENCODING = 0
UTF_8_ENCODING = 1

FILE_TYPE = 0
DIR_TYPE = 1
SWAP_TYPE = 2

# TODO: could use fsdecode and fsencode rather than actual utf-8 and byte encoding / decoding


class Node():

    def __init__(self, name, path, parent, file_type, attr, unlink, open_count):
        self.set_name(name)
        self.path = path
        self.parent = parent
        self.type = file_type
        self.attr = attr
        self.unlink = unlink

        # Creating, opening, closing and removing a file, will result in open_count
        self.open_count = open_count

        # If rm or rmdir -> node needs to exist but ls mustn't show the item
        self.invisible = False

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

    def is_unlink(self):
        if self.unlink is None:
            return False
        return self.unlink

    def set_unlink(self, unlink=True):
        self.unlink = unlink

    def inc_open_count(self, amount=1):
        self.open_count += amount

    def dec_open_count(self, amount=1):
        self.open_count -= amount

    def get_open_count(self):
        return self.open_count

    def set_visible(self):
        self.invisible = False

    def set_invisible(self):
        self.invisible = True

    def to_dict(self):
        return {
            "name": self.name,
            "path": self.path,
            "parent": self.parent,
            "type": self.type,
            "unlink": self.unlink,
            "open_count": self.open_count,
            "invisible": self.invisible
        }

    def __repr__(self):
        return "Node(name: {0}, path: {1}, type: {2}, unlink: {3}, open_count: {4}, invisible: {5})".format(
            self.name, self.path, self.type, self.unlink, self.open_count, self.invisible)


class File(Node):

    def __init__(self, name, path, parent=0, data="", attr=None, unlink=False, open_count=0):
        super().__init__(name, path, parent, FILE_TYPE,
                         attr=attr, unlink=unlink, open_count=open_count)
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
            "unlink: {0}, ".format(self.unlink) +\
            "open_count: {0}, ".format(self.open_count) +\
            "invisible: {0}) ".format(self.invisible)


class Directory(Node):

    def __init__(self, name, path, parent=0, attr=None, unlink=False, root=False, open_count=0):
        super().__init__(name, path, parent, DIR_TYPE,
                         attr=attr, unlink=unlink, open_count=open_count)
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
            "unlink: {0}, ".format(self.unlink) +\
            "open_count: {0}, ".format(self.open_count) +\
            "invisible: {0}, ".format(self.invisible)


class EntryAttributes(pyfuse3.EntryAttributes):

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return "EntryAttributes(st_ino: {0})".format(self.st_ino)
