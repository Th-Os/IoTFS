import os

BYTE_ENCODING = 0
UTF_8_ENCODING = 1

FILE_TYPE = 0
DIR_TYPE = 1
SWAP_TYPE = 2


class Node():

    def __init__(self, name, path, file_type, attr, unlink):
        self.set_name(name)
        self.path = path
        self.type = file_type
        self.attr = attr
        self.unlink = unlink

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

    def set_unlink(self, unlink):
        self.unlink = unlink

    def to_dict(self):
        return {
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "unlink": self.unlink
        }

    def __repr__(self):
        return "Node(name: {0}, path: {1}, type: {2}, unlink: {3})".format(self.name, self.path, self.type, self.unlink)


class File(Node):

    def __init__(self, name, path, data="", attr=None, unlink=False):
        super().__init__(name, path, FILE_TYPE, attr=attr, unlink=unlink)
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
        return "File(name: {0}, path: {1}, type: {2}, data: {3}, unlink: {4})".format(self.name, self.path, self.type, self.data, self.unlink)


class Directory(Node):

    def __init__(self, name, path, attr=None, unlink=False, root=False):
        super().__init__(name, path, DIR_TYPE, attr=attr, unlink=unlink)
        self.root = root

    def is_root(self):
        return self.root

    def get_full_path(self):
        if self.is_root():
            return self.path + os.sep
        return self.path + self.get_name(encoding=UTF_8_ENCODING)

    def __repr__(self):
        return "Directory(name: {0}, path: {1}, type: {2}, unlink: {3}, root: {4})".format(self.name, self.path, self.type, self.unlink, self.root)
