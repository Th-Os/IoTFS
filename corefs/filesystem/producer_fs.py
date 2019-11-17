from enum import Enum

from corefs.filesystem.fs import FileSystem
from corefs.filesystem.node import LockedFile, LockedDirectory

from corefs.utils._fs_utils import Types
from corefs.utils import _logging


class ProducerFileSystem(FileSystem):

    def __init__(self, mount_point, structure_json=None, queue=None, debug=False):
        self.logger = _logging.create_logger("producer")
        super().__init__(mount_point, structure_json, debug)
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
            Operations.CREATE_FILE, LockedFile(node, entry)))
        return result

    async def mknod(self, parent_inode, name, mode, rdev, ctx):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        result = await super().mknod(parent_inode, name, mode, rdev, ctx)
        node = self.data.nodes[result.st_ino]
        entry = self.data.get_entry_by_parent_name(parent_inode, name)

        self.queue.put(CreateObject(
            Operations.CREATE_FILE, LockedFile(node, entry)))
        return result

    async def mkdir(self, parent_inode, name, mode, ctx):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        result = await super().mkdir(parent_inode, name, mode, ctx)
        node = self.data.nodes[result.st_ino]
        entry = self.data.get_entry_by_parent_name(parent_inode, name)

        self.queue.put(CreateObject(
            Operations.CREATE_DIR, LockedDirectory(node, entry)))
        return result

    async def read(self, inode, off, size):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        result = await super().read(inode, off, size)
        node = self.data.nodes[inode]
        entry = self.data.get_entry(inode)

        self.queue.put(ReadObject(
            Operations.READ_FILE, LockedFile(node, entry), result))
        return result

    async def readdir(self, inode, start_id, token):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        await super().readdir(inode, start_id, token)
        result = self.data.get_children(inode)
        node = self.data.nodes[inode]
        entry = self.data.get_entry(inode)

        self.queue.put(ReadObject(
            Operations.READ_DIR, LockedDirectory(node, entry), result))

    async def write(self, inode, off, buf):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        result = await super().write(inode, off, buf)
        node = self.data.nodes[inode]
        entry = self.data.get_entry(inode)

        self.queue.put(WriteObject(
            Operations.WRITE_FILE, LockedFile(node, entry), result))
        return result

    async def rename(self, parent_inode_old, name_old, parent_inode_new, name_new, flags, ctx):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        await super().rename(parent_inode_old, name_old, parent_inode_new, name_new, flags, ctx)
        entry = self.data.get_entry_by_parent_name(parent_inode_new, name_new)
        node = self.data.nodes[entry.inode]
        operation = None
        renamed_node = None
        if node.get_type() == Types.FILE:
            operation = Operations.RENAME_FILE
            renamed_node = LockedFile(node, entry)
        else:
            operation = Operations.RENAME_DIR
            renamed_node = LockedDirectory(node, entry)

        self.queue.put(RenameObject(
            operation, renamed_node, LockedDirectory(self.data.nodes[parent_inode_new], self.data.get_entry(parent_inode_new)), name_new))

    async def unlink(self, parent_inode, name, ctx):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        entry = self.data.get_entry_by_parent_name(parent_inode, name)
        node = self.data.nodes[entry.inode]
        removed_file = LockedFile(node, entry)
        await super().unlink(parent_inode, name, ctx)

        self.queue.put(RemoveObject(Operations.REMOVE_FILE,
                                    removed_file))

    async def rmdir(self, parent_inode, name, ctx):
        if self.queue is None:
            raise ValueError("Queue is not provided.")
        entry = self.data.get_entry_by_parent_name(parent_inode, name)
        node = self.data.nodes[entry.inode]
        removed_dir = LockedDirectory(node, entry)
        await super().rmdir(parent_inode, name, ctx)

        self.queue.put(RemoveObject(Operations.REMOVE_DIR,
                                    removed_dir))

    # TODO: Refactor if needed.
    def __get_children(self, inode):
        inodes = super()._FileSystem__get_children(inode)
        result = []
        for inode in inodes:
            node = self.nodes[inode]
            if node.get_type() == Types.FILE:
                result.append(LockedFile(node))
            else:
                result.append(LockedDirectory(node))
        return result


class Events(Enum):
    CREATE = 1
    READ = 2
    WRITE = 3
    RENAME = 4
    REMOVE = 5


class Operations(Enum):

    CREATE_FILE = 1
    CREATE_DIR = 2

    READ_FILE = 3
    READ_DIR = 4

    WRITE_FILE = 5

    RENAME_FILE = 6
    RENAME_DIR = 7

    REMOVE_FILE = 8
    REMOVE_DIR = 9


class Result():

    def __init__(self, inode, node_type, name, path, data=None):
        self.inode = inode
        self.type = node_type
        self.name = name
        self.path = path
        self.data = data


class ProducerObject():

    def __init__(self, event, operation, node):
        self.event = event
        self.operation = operation
        self.node = node


class CreateObject(ProducerObject):

    def __init__(self, operation, node):
        super().__init__(Events.CREATE, operation, node)


class ReadObject(ProducerObject):

    def __init__(self, operation, node, data):
        super().__init__(Events.READ, operation, node)
        self.data = data


class WriteObject(ProducerObject):

    def __init__(self, operation, node, buffer_length):
        super().__init__(Events.WRITE, operation, node)
        self.buffer_length = buffer_length


class RenameObject(ProducerObject):

    def __init__(self, operation, node, new_dir, new_name):
        super().__init__(Events.RENAME, operation, node)
        self.new_dir = new_dir
        self.new_name = new_name


class RemoveObject(ProducerObject):

    def __init__(self, operation, node):
        super().__init__(Events.REMOVE, operation, node)
