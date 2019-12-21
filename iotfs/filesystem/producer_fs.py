# -*- coding: utf-8 -*-

from iotfs.listener.objects import CreateObject, ReadObject, RemoveObject, RenameObject, WriteObject, Operations

from iotfs.filesystem.fs import FileSystem

from iotfs.utils._fs_utils import Types
from iotfs.utils import _logging


class ProducerFileSystem(FileSystem):

    """
    ProducerFileSystem is the base class for every filesystem that uses the *iotfs.listener.Listener*.
    It will produce messages through a messege queue, which the listener listens to.
    Therefore, a developer can listen for file system events.

    ...

    Attributes
    ----------
    mount_point : str
        path of mountpoint
    queue : queue.Queue
        message queue for listening module
    debug : bool, optional
        this defines whether the logging output should include the debug level

    """

    def __init__(self, mount_point, queue=None, debug=False):
        """
        Parameters
        ----------
        mount_point : str
            a mounting point for the filesystem.
        queue : queue.Queue
            message queue for listening module
        debug : bool, optional
            this defines whether the logging output should include the debug level
        """

        self.logger = _logging.create_logger("producer")
        super().__init__(mount_point, debug)
        self.queue = queue

    def setQueue(self, queue):
        self.queue = queue

    async def create(self, parent_inode, name, mode, flags, ctx):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        result = await super().create(parent_inode, name, mode, flags, ctx)
        inode = result[0]
        node = self.data.nodes[inode]
        entry = self.data.get_entry_by_parent_name(parent_inode, name)

        self.queue.put(CreateObject(
            Operations.CREATE_FILE, {"node": node.to_dict(), "entry": entry.to_dict()}))
        return result

    async def mknod(self, parent_inode, name, mode, rdev, ctx):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        result = await super().mknod(parent_inode, name, mode, rdev, ctx)
        node = self.data.nodes[result.st_ino]
        entry = self.data.get_entry_by_parent_name(parent_inode, name)

        self.queue.put(CreateObject(
            Operations.CREATE_FILE, {"node": node.to_dict(), "entry": entry.to_dict()}))
        return result

    async def mkdir(self, parent_inode, name, mode, ctx):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        result = await super().mkdir(parent_inode, name, mode, ctx)
        node = self.data.nodes[result.st_ino]
        entry = self.data.get_entry_by_parent_name(parent_inode, name)

        self.queue.put(CreateObject(
            Operations.CREATE_DIR, {"node": node.to_dict(), "entry": entry.to_dict()}))
        return result

    async def read(self, inode, off, size):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        result = await super().read(inode, off, size)
        node = self.data.nodes[inode]
        entry = self.data.get_entry(inode)

        self.queue.put(ReadObject(
            Operations.READ_FILE, {"node": node.to_dict(), "entry": entry.to_dict()}, result))
        return result

    async def readdir(self, inode, start_id, token):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        await super().readdir(inode, start_id, token)
        result = self.data.get_children(inode)
        node = self.data.nodes[inode]
        entry = self.data.get_entry(inode)

        self.queue.put(ReadObject(
            Operations.READ_DIR, {"node": node.to_dict(), "entry": entry.to_dict()}, result))

    async def write(self, inode, off, buf):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        result = await super().write(inode, off, buf)
        node = self.data.nodes[inode]
        entry = self.data.get_entry(inode)

        self.queue.put(WriteObject(
            Operations.WRITE_FILE, {"node": node.to_dict(), "entry": entry.to_dict()}, result))
        return result

    async def rename(self, parent_inode_old, name_old, parent_inode_new, name_new, flags, ctx):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        await super().rename(parent_inode_old, name_old, parent_inode_new, name_new, flags, ctx)
        entry = self.data.get_entry_by_parent_name(parent_inode_new, name_new)
        node = self.data.nodes[entry.inode]
        operation = None
        renamed_node = None
        if node.type == Types.FILE:
            operation = Operations.RENAME_FILE
        else:
            operation = Operations.RENAME_DIR
        renamed_node = {"node": node.to_dict(), "entry": entry.to_dict()}

        self.queue.put(RenameObject(
            operation, renamed_node, {"node": self.data.nodes[parent_inode_new].to_dict(), "entry":
                                      self.data.get_entry(parent_inode_new).to_dict()}, name_new))

    async def unlink(self, parent_inode, name, ctx):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        entry = self.data.get_entry_by_parent_name(parent_inode, name)
        node = self.data.nodes[entry.inode]
        removed_file = {"node": node.to_dict(), "entry": entry.to_dict()}
        await super().unlink(parent_inode, name, ctx)

        self.queue.put(RemoveObject(Operations.REMOVE_FILE,
                                    removed_file))

    async def rmdir(self, parent_inode, name, ctx):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        entry = self.data.get_entry_by_parent_name(parent_inode, name)
        node = self.data.nodes[entry.inode]
        removed_dir = {"node": node.to_dict(), "entry": entry.to_dict()}
        await super().rmdir(parent_inode, name, ctx)

        self.queue.put(RemoveObject(Operations.REMOVE_DIR,
                                    removed_dir))
