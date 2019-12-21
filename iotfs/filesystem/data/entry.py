# -*- coding: utf-8 -*-

import os

from iotfs.utils._fs_utils import LinkTypes, Encodings


class Entry():

    """
    Entrydict inherits dict functionalities and provides further methods to manipulate entries.

    ...

    Attributes
    ----------
    inode : int
        an inode number
    name : str or bytes
        a string or bytes representation of the name
    path : str
        a path
    parent : int, optional
        a parent inode
    link_type : iotfs.utils._fs_utils.LinkTypes
        a type of link

    """

    def __init__(self, inode, name, path, parent=None, link_type=None):
        """
        Parameters
        ----------
        inode : int
            an inode number
        name : str or bytes
            a string or bytes representation of the name
        path : str
            a path
        parent : int, optional
            a parent inode
        link_type : iotfs.utils._fs_utils.LinkTypes
            a type of link
        """
        self.inode = inode
        self.name = name
        self.path = path
        self.parent = parent
        self.link_type = link_type

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
        """ Returns actual path of the entry. Not just the path that contains this entry.

        """
        if self.path == os.sep:
            return self.path + self.get_name(encoding=Encodings.UTF_8_ENCODING)
        return os.path.join(self.path, self.get_name(encoding=Encodings.UTF_8_ENCODING))

    def __repr__(self):
        return "Entry(inode: {0}, name: {1}, path: {2})".format(self.inode, self.name, self.path)

    def to_dict(self):
        return {
            "inode": self.inode,
            "name": self.name,
            "path": self.path
        }


class SymbolicEntry(Entry):

    """
    SymbolicEntry inherits Entry functionalities and represents a symbolic link.

    ...

    Attributes
    ----------
    inode : int
        an inode number
    name : str or bytes
        a string or bytes representation of the name
    path : str
        a path
    parent : int, optional
        a parent inode
    link_path : str
        a path to the link target

    """

    def __init__(self, inode, name, path, parent=None, link_path=None):
        """
        Parameters
        ----------
        inode : int
            an inode number
        name : str or bytes
            a string or bytes representation of the name
        path : str
            a path
        parent : int, optional
            a parent inode
        link_path : str
            a path to the link target
        """

        super().__init__(inode, name, path, parent=parent, link_type=LinkTypes.SYMBOLIC)
        self.link_path = link_path

    def __repr__(self):
        return "SymbolicEntry(inode: {0}, name: {1}, path: {2}, link path: {3})".format(self.inode, self.name,
                                                                                        self.path, self.link_path)

    def to_dict(self):
        return {
            **super().to_dict(),
            "link_type": self.link_type.name,
            "link_path": self.link_path
        }


class HardlinkEntry(Entry):

    """
    HardlinkEntry inherits Entry functionalities and represents a hard link.

    ...

    Attributes
    ----------
    inode : int
        an inode number
    name : str or bytes
        a string or bytes representation of the name
    path : str
        a path
    parent : int, optional
        a parent inode
    """

    def __init__(self, inode, name, path, parent=None):
        """
        Parameters
        ----------
        inode : int
            an inode number
        name : str or bytes
            a string or bytes representation of the name
        path : str
            a path
        parent : int, optional
            a parent inode
        """
        super().__init__(inode, name, path, parent=parent, link_type=LinkTypes.HARDLINK)

    def __repr__(self):
        return "HardlinkEntry(name: {0}, path: {1})".format(self.name, self.path)

    def to_dict(self):
        return {
            **super().to_dict(),
            "link_type": self.link_type.name
        }
