import os
import stat

from utils import _logging


class Types():

    FILE = 0
    DIRECTORY = 1
    DIRECTORIES = 2


class Query():

    # TODO: Query should allow queueing
    # TODO: Query should be extended with permissions
    def __init__(self, node_type, name, path, callback):
        self.log = _logging.create_logger("Query", True)
        if "MOUNT_POINT" not in os.environ:
            raise LookupError("No \"MOUNT_POINT\" in environment variables.")
        mount_point = os.environ["MOUNT_POINT"]

        self.type = node_type
        self.name = name
        self.path = os.path.join(mount_point, path)
        self.callback = callback

    def start(self):
        pass

    def run_callback(self, *args):
        if self.callback is not None:
            self.callback(*args)


class QueryQueue():

    def __init__(self):
        self.queue = []

    def add(self, item):
        assert isinstance(item, Query)
        self.queue.append(item)

    def startAll(self):
        for item in self.queue:
            item.start()


class CreateQuery(Query):

    def __init__(self, node_type, name, path, data=None, callback=None):
        super().__init__(node_type, name, path, callback)
        self.log = _logging.create_logger(self.__class__.__name__, True)
        self.data = data

    def start(self):
        super().start()
        full_path = os.path.join(self.path, self.name)
        if self.type == Types.FILE:
            self.log.debug("Create file with path: %s", full_path)
            fd = os.open(full_path, os.O_CREAT | os.O_WRONLY, stat.S_IRWXO)
            assert os.path.exists(full_path) is True
            if self.data is not None:
                os.write(fd, self.data.encode("utf-8"))
            os.close(fd)
        elif self.type == Types.DIRECTORY:
            self.log.debug("Create dir with path: %s", full_path)
            os.mkdir(full_path)
        elif self.type == Types.DIRECTORIES:
            self.log.debug("Create dirs with path: %s", full_path)
            os.makedirs(full_path, exist_ok=True)
        else:
            raise NotImplementedError(self.type)
        self.run_callback()


class ReadQuery(Query):

    # reading file and reading directory (results in list)
    def __init__(self, node_type, name, path, callback=None):
        super().__init__(node_type, name, path, callback)

    def start(self):
        super().start()
        result = None
        full_path = os.path.join(self.path, self.name)
        if self.type == Types.DIRECTORY:
            result = os.listdir(full_path)
        elif self.type == Types.FILE:
            with open(full_path, "r") as f:
                result = f.read()
        else:
            raise NotImplementedError(self.type)
        self.run_callback(result)


class UpdateQuery(Query):

    def __init__(self, node_type, name, path, new_name=None, new_path=None, new_data=None, callback=None):
        super().__init__(node_type, name, path, callback)

        # TODO: check if and what changes
        self.new_name = new_name
        self.new_path = new_path
        self.new_data = new_data

    def start(self):
        super().start()
        full_path = os.path.join(self.path, self.name)

        # TODO: Test this bevavior
        if self.new_name is not None:
            os.rename(full_path, os.path.join(self.path, self.new_name))
        elif self.new_path is not None:
            os.rename(full_path, os.path.join(self.new_path, self.name))
        elif self.new_data is not None:
            fd = os.open(full_path, os.O_WRONLY |
                         os.O_TRUNC, stat.S_IRWXO)
            os.write(fd, self.new_data.encode("utf-8"))
            os.close(fd)
        self.run_callback()


class DeleteQuery(Query):

    def __init__(self, node_type, name, path, callback=None):
        super().__init__(node_type, name, path, callback)

    def start(self):
        super().start()
        full_path = os.path.join(self.path, self.name)
        if self.type == Types.DIRECTORY:
            os.rmdir(full_path)
        elif self.type == Types.DIRECTORIES:
            # TODO: Test if this works
            os.removedirs(full_path)
        elif self.type == Types.FILE:
            os.remove(full_path)
        else:
            raise NotImplementedError(self.type)
        self.run_callback()
