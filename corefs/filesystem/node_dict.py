import os

from corefs.filesystem.node import Node, File, Directory, Types, Encodings
from corefs.utils import _logging

# TODO test and refactor

ROOT_INODE = 1


class NodeDict(dict):

    def __init__(self, logger=None):
        super().__init__()
        if logger is not None:
            self.log = logger
        else:
            self.log = _logging.create_logger("NodeDict", debug=True)

    def add_inode(self, name, parent_inode, node_type=Types.FILE, data="", mode=7777):
        path = self[parent_inode].get_full_path()
        self.log.info('__add_inode with path %s and name %s', path, name)
        if path[-1] != os.path.sep:
            path += os.path.sep
            self.log.debug("new path: %s", path)
        inode = list(self.keys())[-1] + 1

        # With hardlinks, one inode may map to multiple paths.
        if inode not in self and inode is not ROOT_INODE:
            self.log.debug("Found no inode")
            self.log.debug(
                "Create: inode %d, with path: %s, and name: %s", inode, path, name)
            if node_type == Types.FILE or node_type == Types.SWAP:
                self[inode] = File(
                    name, path, mode=mode, parent=parent_inode, data=data)
            else:
                self[inode] = Directory(
                    name, path, mode=mode, parent=parent_inode)
            self[inode].inc_open_count()
            self.log.debug(self)
        return inode

    def try_remove_inode(self, inode):
        self.log.info("Trying to remove inode %d.", inode)
        try:
            if self[inode].get_open_count() <= 1:
                self.log.debug("Removed inode %d", inode)
                del self[inode]
            else:
                self.log.debug("Didn't remove inode %d", inode)
        except KeyError:
            self.log.warning("Inode %d doesn't exist.", inode)

    def try_decrease_op_count(self, inode):
        self.log.warning("Trying to decrease op count of %d.", inode)
        try:
            self[inode].dec_open_count()
            if self[inode].get_open_count() == 0:
                self[inode].lock()
            self.log.warning("New op count: %d",
                             self[inode].get_open_count())
        except KeyError:
            self.log.error("No inode with key %d.", inode)
        except Exception as e:
            self.log.error(e)

    def try_increase_op_count(self, inode):
        self.log.warning("Trying to increase op count of %d.", inode)
        try:
            self[inode].inc_open_count()
        except KeyError:
            self.warning("Inode %d does not exist.", inode)
        except Exception as e:
            self.log.error(e)

    def get_children(self, inode):
        if type(self[inode]) is not Directory:
            self.log.error("Inode %d is no directory.")
            raise NotADirectoryError("Inode %d is no directory.")
        return [idx for idx in self if self[idx].get_parent() == inode]

    def get_node_by_name(self, name, array=None):
        if array is None:
            array = self
        name = os.fsdecode(name)
        self.log.info("get node by name: %s", name)
        for idx in array:
            self.log.debug(idx)
            self.log.debug("check %s vs %s", self[idx].get_name(
                encoding=Encodings.UTF_8_ENCODING), name)
            if self[idx].get_name(encoding=Encodings.UTF_8_ENCODING) == name:
                return self[idx]
            self.log.debug("failed")
        # nano for new file -> results in didnt find any
        # TODO: What behavior would be appropriate for no found node?
        self.log.error("didn't find any")
        return None

    def get_index_by_name(self, name):
        self.log.info("get node by name: %s", name)
        for idx in self:
            if self[idx].get_name(Encodings.BYTE_ENCODING) == name:
                return idx
        raise Exception("Found no node for name %s", name)
