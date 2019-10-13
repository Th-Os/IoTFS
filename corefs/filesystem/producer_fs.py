from enum import Enum

from corefs.filesystem.fs import FileSystem
from corefs.filesystem.node import LockedFile, LockedDirectory, Types
from corefs.utils import _logging

# TODO: Is a check for queue needed? Maybe as decorator


class ProducerFilesystem(FileSystem):

    def __init__(self, mount_point, queue=None, debug=False):
        self.logger = _logging.create_logger("producer")
        super().__init__(mount_point, debug)
        self.queue = queue

    def setQueue(self, queue):
        self.queue = queue

    async def create(self, parent_inode, name, mode, flags, ctx):
        result = await super().create(parent_inode, name, mode, flags, ctx)
        self.queue.put(CreateObject(
            Operations.CREATE_FILE, LockedFile(self.nodes[result[0]])))
        return result

    async def mknod(self, parent_inode, name, mode, rdev, ctx):
        result = await super().mknod(parent_inode, name, mode, rdev, ctx)
        self.queue.put(CreateObject(
            Operations.CREATE_FILE, LockedFile(self.nodes[result.st_ino])))
        return result

    async def mkdir(self, parent_inode, name, mode, ctx):
        result = await super().mkdir(parent_inode, name, mode, ctx)
        self.queue.put(CreateObject(
            Operations.CREATE_DIR, LockedDirectory(self.nodes[result.st_ino])))
        return result

    async def read(self, inode, off, size):
        result = await super().read(inode, off, size)
        self.queue.put(ReadObject(
            Operations.READ_FILE, LockedFile(self.nodes[inode]), result))
        return result

    async def readdir(self, inode, start_id, token):
        await super().readdir(inode, start_id, token)
        result = self.__get_children(inode)
        self.queue.put(ReadObject(
            Operations.READ_DIR, LockedDirectory(self.nodes[inode]), result))

    async def write(self, inode, off, buf):
        result = await super().write(inode, off, buf)
        self.queue.put(WriteObject(
            Operations.WRITE_FILE, LockedFile(self.nodes[inode]), result))
        return result

    async def rename(self, parent_inode_old, name_old, parent_inode_new, name_new, flags, ctx):
        await super().rename(parent_inode_old, name_old, parent_inode_new, name_new, flags, ctx)
        node = self.__get_node_by_name(name_new)
        operation = None
        if node.get_type() == Types.FILE:
            operation = Operations.RENAME_FILE
            node = LockedFile(node)
        else:
            operation = Operations.RENAME_DIR
            node = LockedDirectory(node)
        self.queue.put(RenameObject(
            operation, node, LockedDirectory(self.nodes[parent_inode_new]), name_new))

    async def unlink(self, parent_inode, name, ctx):
        removed_file = LockedFile(self.__get_node_by_name(name))
        await super().unlink(parent_inode, name, ctx)
        self.queue.put(RemoveObject(Operations.REMOVE_FILE,
                                    removed_file))

    async def rmdir(self, parent_inode, name, ctx):
        removed_dir = LockedDirectory(self.__get_node_by_name(name))
        await super().rmdir(parent_inode, name, ctx)
        self.queue.put(RemoveObject(Operations.REMOVE_DIR,
                                    removed_dir))

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

    def __get_node_by_name(self, name):
        return super()._FileSystem__get_node_by_name(name)


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
