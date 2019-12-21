# -*- coding: utf-8 -*-

import os
import time
import stat

from iotfs.utils._fs_utils import Encodings, Types


class Node():

    """
    This Node object is an abstraction for the underlying functions
    files (File) and directories (Directory) use.

    ...

    Attributes
    ----------
    mode : int
        an integer representation of a node mode containing type of node and permissions
    parent : int
        represents parent inode
    node_type : iotfs.utils._fs_utils.Types
        a type of node (file or directory)
    open_count : int
        starting open_count, which will be incremented, when file is opened

    """

    def __init__(self, mode, parent, node_type, open_count):
        """
        Parameters
        ----------
        mode : int
            an integer representation of a node mode containing type of node and permissions
        parent : int
            represents parent inode
        node_type : iotfs.utils._fs_utils.Types
            a type of node (file or directory)
        open_count : int
            starting open_count, which will be incremented, when file is opened
        """

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

    """
    This LockedNode object is used as underlying base for LockedFile and LockedNode.
    Purpose of this Locked* objects is to have an object without functionality to be passed to the listener.

    ...

    Attributes
    ----------
    node : iotfs.filesystem.data.node
        a node object that will be used to fill attributes
    entry : iotfs.filesyste.data.entry
        a entry object that will be used to fille attributes

    """

    def __init__(self, node, entry):
        """
        Parameters
        ----------
        node : iotfs.filesystem.data.node
            a node object that will be used to fill attributes
        entry : iotfs.filesyste.data.entry
            a entry object that will be used to fille attributes
        """

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

    """
    This File object is a representation of a file containing necessary functions to get and set data.
    ...

    Attributes
    ----------
    mode : int
        an integer representation of a node mode containing type of node and permissions
    parent : int, optional
        represents parent inode
    data : str, optional
        string of data saved in an file
    unlink : boolean, optional
        this specifies whether a file should be deleted
    open_count : int, optional
        starting open_count, which will be incremented, when file is opened
    is_link : boolean, optional
        this specifies whether the object is a link to another file

    """

    def __init__(self, mode, parent=None, data="", unlink=False, open_count=0, is_link=False):
        """
        Parameters
        ----------
        mode : int
            an integer representation of a node mode containing type of node and permissions
        parent : int, optional
            represents parent inode
        data : str, optional
            string of data saved in an file
        unlink : boolean, optional
            this specifies whether a file should be deleted
        open_count : int, optional
            starting open_count, which will be incremented, when file is opened
        """
        super().__init__(mode, parent, Types.FILE, open_count=open_count)
        self.data = data
        if not is_link:
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
        return "File(mode: {0}, ".format(oct(self.mode)) +\
            "data: {0}, ".format(self.get_data(encoding=Encodings.UTF_8_ENCODING)) +\
            "open_count: {0}, ".format(self.open_count) +\
            "invisible: {0}, ".format(self.invisible) +\
            "lock: {0})".format(self.locked)


class Directory(Node):

    """
    This Directory object is a representation of a directory containing
    setting the dir mode and allowing to set as root.
    ...

    Attributes
    ----------
    mode : int
        an integer representation of a node mode containing type of node and permissions
    parent : int, optional
        represents parent inode
    data : str, optional
        string of data saved in an file
    unlink : boolean, optional
        this specifies whether a file should be deleted
    open_count : int, optional
        starting open_count, which will be incremented, when file is opened
    root : boolean, optional
        sets the directory to root, if True
    is_link : boolean, optional
        this specifies whether the object is a link to another file

    """

    def __init__(self, mode, parent=None, unlink=False, root=False, open_count=0, is_link=False):
        """
        Parameters
        ----------
        mode : int
            an integer representation of a node mode containing type of node and permissions
        parent : int, optional
            represents parent inode
        data : str, optional
            string of data saved in an file
        unlink : boolean, optional
            this specifies whether a file should be deleted
        open_count : int, optional
            starting open_count, which will be incremented, when file is opened
        root : boolean, optional
            sets the directory to root, if True
        is_link : boolean, optional
            this specifies whether the object is a link to another file
        """
        super().__init__(mode, parent, Types.DIR, open_count=open_count)
        self.root = root
        if not is_link:
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
