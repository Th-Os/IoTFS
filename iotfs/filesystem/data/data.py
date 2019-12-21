# -*- coding: utf-8 -*-

import os

from iotfs.filesystem.data.node import File, Directory
from iotfs.filesystem.data.entry import Entry, SymbolicEntry, HardlinkEntry

from iotfs.filesystem.data.entry_dict import EntryDict

from iotfs.utils._fs_utils import Types, Encodings, LinkTypes, ROOT_INODE, STANDARD_MODE, LINK_MODE
from iotfs.utils import _logging


class Data():

    """
    This Data class holds every entry and node.
    It provides methods to create, search, get and manipulate these two.

    ...

    Attributes
    ----------
    logger : logging.logger
        an already initialized logger instance

    """

    def __init__(self, logger=None):
        """
        Parameters
        ----------
        logger : logging.logger
            an already initialized logger instance
        """

        super().__init__()
        if logger is not None:
            self.log = logger
        else:
            self.log = _logging.create_logger("Data", debug=True)
        self.entries = EntryDict(logger=self.log)
        self.nodes = dict()
        self.inode_entries_map = dict()
        self.inode_unique_count = 0

    def add_entry(self, name, parent_inode, node_type=Types.FILE, data="", mode=STANDARD_MODE):
        """ Adds a new entry and a new node.

        """
        parent_entry = self.get_entry(parent_inode)
        path = parent_entry.get_full_path()
        entry = None
        try:
            inode = self.__add_inode(parent_inode, node_type, data, mode)
            self.log.debug(
                "Create entry: inode %d, with path: %s, and name: %s", inode, path, name)
            entry = Entry(inode, name, path, parent=parent_entry)
        except Exception as e:
            raise e
        if path not in self.entries:
            self.entries[path] = []
        self.entries[path].append(entry)
        self.inode_entries_map[inode].append(entry)
        return entry

    def add_link_entry(self, name, parent_inode, link_type, mode=STANDARD_MODE, link_path=None, target_inode=None):
        """ Adds a new linkentry that is either a hard or a symbolic link
            and a node depending on the existance of target_inode.

        """
        parent_entry = self.get_entry(parent_inode)
        self.log.debug(parent_entry)
        path = parent_entry.get_full_path()
        self.log.debug(path)

        entry = None
        if link_type == LinkTypes.SYMBOLIC:
            '''
                - has its own inode
                - no data in file
                - points to another entry
                - can point to file in another fs or even directories
            '''
            if link_path is None:
                raise NotImplementedError("Path to link is not given.")
            self.log.debug(
                "Add symbolic link to %s with name %s", name, link_path)
            link_path = os.fsdecode(link_path)
            if os.sep in link_path:
                parts = link_path.split(os.sep)
                source_path = os.sep + os.path.join(*parts[:-1])
                source_name = parts[-1]
            else:
                source_path = os.sep
                source_name = link_path
            self.log.debug(source_path)
            self.log.debug(source_name)
            source_entry = self.get_entry_by_name_path(
                source_name, source_path)
            if source_entry is None:
                raise Exception("No source entry found in current filesystem.")

            inode = self.__add_inode(
                parent_inode, node_type=self.nodes[source_entry.inode].type, mode=LINK_MODE, is_link=True)
            entry = SymbolicEntry(
                inode, name, path, parent=parent_entry, link_path=link_path)
            self.log.debug(entry)
            self.log.debug(self.nodes[inode])
        elif link_type == LinkTypes.HARDLINK:
            '''
                - data in file
                - another representation of a file linked to same inode
                - can only point to file in filesystem
            '''
            if target_inode is None:
                raise NotImplementedError("Target inode is not given.")
            self.log.debug(
                "Add hard link to inode %d with name %s", target_inode, name)
            inode = target_inode
            entry = HardlinkEntry(
                inode, name, path, parent=parent_entry)
        else:
            raise NotImplementedError(
                "Type of link not implemented: {}".format(link_type))

        self.inode_entries_map[inode].append(entry)
        return entry

    def add_root_entry(self, name, mode=STANDARD_MODE):
        """ Adding the root entry. Only one should exist.

        """
        if ROOT_INODE in self.nodes:
            self.log.error("Root entry already added.")
            return
        self.log.debug("Adding root entry.")
        if os.sep in name:
            parts = name.rsplit(os.sep, 1)
            name = parts[-1]
            path = parts[0]
            if path[0] != os.sep:
                path = os.sep + path
        else:
            path = os.sep
        self.log.debug(name)
        self.log.debug(path)
        self.nodes[ROOT_INODE] = Directory(mode, root=True)
        entry = Entry(ROOT_INODE, name, path, Types.DIR)
        self.entries[path] = [entry]
        self.inode_entries_map[ROOT_INODE] = [entry]
        self.inode_unique_count += 1

    def __add_inode(self, parent_inode, node_type=Types.FILE, data="", mode=STANDARD_MODE, is_link=False):
        """ Adding an inode.

        """
        if len(self.nodes) == 0:
            self.log.error("No root inode in nodes?")
            inode = 2
        else:
            self.inode_unique_count += 1
            inode = self.inode_unique_count

        self.log.debug("Create inode %d: %s", inode, node_type.name)

        if node_type == Types.FILE or node_type == Types.SWAP:
            self.nodes[inode] = File(mode, parent=parent_inode, data=data, is_link=is_link)
        elif node_type == Types.DIR:
            self.nodes[inode] = Directory(mode, parent=parent_inode, is_link=is_link)
        elif node_type == Types.LINK:
            # This is a symlink. Can link to another filesystem too.
            raise NotImplementedError("Symlink")
        else:
            raise Exception("Found no node_type called: {0}".format(node_type))
        self.nodes[inode].inc_open_count()
        self.inode_entries_map[inode] = []
        return inode

    def get_symbolic_target(self, entry):
        """ Getting the target of a pointer by a SymbolicEntry.

        """
        if type(entry) == SymbolicEntry:
            parts = entry.link_path.split(os.sep)
            name = parts[-1]
            path = os.path.join(*parts[:-1])
            if entry.link_path[0] == os.sep:
                path = os.sep + path
            result = self.get_entry_by_name_path(name, path)
            self.log.debug(result)
            return result
        return None

    def get_entries_of_inode(self, inode, link_type=None):
        """ Get all entries of an inode. Can deliver link type specific entries too.

        """
        self.log.debug(
            "Get entries of inode {0} and linktype {1}".format(inode, link_type))
        if link_type is None:
            return self.inode_entries_map[inode]
        elif link_type == LinkTypes.SYMBOLIC:
            return [entry for entry in self.inode_entries_map[inode] if entry.link_type is not None and
                    entry.link_type == LinkTypes.SYMBOLIC]
        elif link_type == LinkTypes.HARDLINK:
            return [entry for entry in self.inode_entries_map[inode] if entry.link_type is not None and
                    entry.link_type == LinkTypes.HARDLINK]
        else:
            raise Exception("Unknown linktype: {}".format(link_type))

    def get_entry_by_name_path(self, name, path):
        self.log.debug(
            "Get entry by name {0} and path {1}".format(name, path))
        if path in self.entries:
            for entry in self.entries[path]:
                if entry.get_name(Encodings.UTF_8_ENCODING) == name and entry.path == path:
                    self.log.debug(entry)
                    return entry
        self.log.warning(
            "No entry found for name: %s and path: %s", name, path)
        return None

    def get_entry_by_parent_name(self, parent_inode, name):
        """ Search for entry by parent_inode and the childs entry name.

        """
        entries = self.get_children(parent_inode)
        for entry in entries:
            if entry.name == name:
                return entry
        return None

    def get_entry(self, inode):
        """ Get the normal Entry of an inode. If there is none, return the Symbolic one.

        """
        self.log.debug("Get entry of inode %d", inode)
        filtered_entries = [entry for entry in self.inode_entries_map[inode]
                            if entry.link_type is None]
        if len(filtered_entries) == 0:
            self.log.warning("No entries retrieved. Check for SymbolicEntry.")
            symbolic_entries = [entry for entry in self.inode_entries_map[inode]
                                if entry.link_type is LinkTypes.SYMBOLIC]
            if len(symbolic_entries) == 1:
                return symbolic_entries[0]
            else:
                self.log.warning(
                    "Got these symbolic entries: {}".format(symbolic_entries))
                raise Exception(
                    "Inode must have a normal or at least a symbolic entry.")
        if len(filtered_entries) > 1:
            raise Exception("Inode mustn't have more than 1 normal entry.")
        return filtered_entries[0]

    def get_children(self, inode):
        """ Get all children of an inode and return their entries.

        """
        if type(self.nodes[inode]) is not Directory:
            self.log.error("Inode %d is no directory.", inode)
            raise NotADirectoryError("Inode {} is no directory.".format(inode))
        if inode == ROOT_INODE:
            entry = self.get_entry(inode)
            # Root inode has no parent.
            if entry.parent is None:
                self.log.debug("Is root.")
                return [entry]
        inode_children = [
            idx for idx in self.nodes if self.nodes[idx].parent == inode]
        entries = []
        for child in inode_children:
            items = self.inode_entries_map[child]
            if len(items) == 0:
                self.log.warning("Inode %d has no entries.", child)
            else:
                entries.extend(items)
        return entries

    def get_link_entry(self, inode, link_type):
        """ Get the LinkEntry of a inode by link_type.

        """
        try:
            entries = self.inode_entries_map[inode]
            for entry in entries:
                if entry.link_type == link_type:
                    return entry
        except KeyError:
            self.log.error("Inode {} not found".format(inode))
        return None

    def remove_entries(self, inode, entries):
        """ Remove all provided entries of an inode.

        """
        self.log.debug(
            "Remove entries: {0} of inode: {1}".format(entries, inode))
        for path in self.entries:
            for idx in range(len(self.entries[path])):
                try:
                    if self.entries[path][idx] in entries:
                        del self.entries[path][idx]
                        idx -= 1
                except IndexError:
                    self.log.debug("Last item was deleted.")

    def try_remove_inode(self, inode):
        """ Trying to remove an inode.

        First it will check, whether the provided inode is ROOT_INODE.
        When that is true it will return nothing immidiatly.
        After that it checks, if the open count of the provided inode is smaller than one.
        If that is the case, it will delete all entries of this inode
        and then itself.

        """
        self.log.info("Trying to remove inode %d.", inode)
        if inode == ROOT_INODE:
            return
        try:
            self.log.debug("Open count: %d", self.nodes[inode].open_count)
            if self.nodes[inode].open_count < 1:
                entries = self.inode_entries_map[inode]
                self.remove_entries(inode, entries)
                del self.nodes[inode]
                del self.inode_entries_map[inode]
            else:
                self.log.debug("Didn't remove inode %d", inode)
        except KeyError:
            self.log.warning("Inode %d doesn't exist.", inode)

    def try_decrease_op_count(self, inode):
        """ Trying to decrease open count.

        First decreases open count. Then it will lock the inode on certain conditions.
        The locked inode will definitly removed.

        Fails, when inode does not exist.

        """
        self.log.debug("Trying to decrease op count of %d.", inode)
        if inode == ROOT_INODE:
            return
        try:
            self.nodes[inode].dec_open_count()
            if self.nodes[inode].is_invisible() and self.nodes[inode].open_count == 0:
                self.nodes[inode].lock()
            if self.nodes[inode].open_count < 0:
                self.nodes[inode].lock()
            self.log.debug("New op count: %d",
                           self.nodes[inode].open_count)
        except KeyError:
            self.log.error("No inode with key %d.", inode)
        except Exception as e:
            self.log.error(e)

    def try_increase_op_count(self, inode):
        """ Trying to increase open count of provided inode.

        Fails, when inode does not exist.

        """
        self.log.debug("Trying to increase op count of %d.", inode)
        if inode == ROOT_INODE:
            return
        try:
            self.nodes[inode].inc_open_count()
            self.log.debug("Increased open count to %d.",
                           self.nodes[inode].open_count)
        except KeyError:
            self.warning("Inode %d does not exist.", inode)
        except Exception as e:
            self.log.error(e)
