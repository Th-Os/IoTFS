import os
import stat

from corefs.utils import _logging


class Types():

    FILE = 0
    DIRECTORY = 1
    DIRECTORIES = 2


class Query():

    def __init__(self, node_type, name, path, callback, debug):
        self.log = _logging.create_logger(self.__class__.__name__, debug)
        if "MOUNT_POINT" not in os.environ:
            raise LookupError("No \"MOUNT_POINT\" in environment variables.")
        mount_point = os.environ["MOUNT_POINT"]

        self.type = node_type
        self.name = name
        self.path = mount_point if path == "" else os.path.join(
            mount_point, path)
        self.callback = callback

    def start(self):
        raise NotImplementedError("Method \"start\" is not implemented.")

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

    def __init__(self, node_type, name, path="", permissions=0o754, data=None, callback=None, debug=False):
        super().__init__(node_type, name, path, callback, debug)
        self.data = data
        self.permissions = permissions

    def start(self):
        full_path = os.path.join(self.path, self.name)
        self.log.debug("start %s", self.type)
        if self.type == Types.FILE:
            self.log.info("Create file with path: %s", full_path)
            assert os.path.exists(full_path) is False
            fd = os.open(full_path, os.O_CREAT | os.O_WRONLY, self.permissions)
            assert os.path.exists(full_path) is True
            if self.data is not None:
                os.write(fd, self.data.encode("utf-8"))
            os.close(fd)
        elif self.type == Types.DIRECTORY:
            self.log.info("Create dir with path: %s", full_path)
            if not os.path.exists(full_path):
                os.mkdir(full_path, self.permissions)
            else:
                self.log.warning("Directory already exists.")
        elif self.type == Types.DIRECTORIES:
            self.log.info("Create dirs with path: %s", full_path)
            os.makedirs(full_path, self.permissions, exist_ok=True)
        else:
            raise NotImplementedError(self.type)
        self.run_callback()


class ReadQuery(Query):

    # reading file and reading directory (results in list)
    def __init__(self, node_type, name, path="", callback=None, debug=False):
        super().__init__(node_type, name, path, callback, debug)

    def start(self):
        result = None
        full_path = os.path.join(self.path, self.name)
        if self.type == Types.DIRECTORY:
            result = os.listdir(full_path)
        elif self.type == Types.FILE:
            fd = os.open(full_path, os.O_RDONLY)
            _stat = os.stat(full_path)
            size = _stat.st_size
            self.log.info(oct(_stat.st_mode))
            data_bytes = os.read(fd, size)
            os.close(fd)
            data = os.fsdecode(data_bytes)
        else:
            raise NotImplementedError(self.type)
        self.run_callback(data)


class UpdateQuery(Query):

    def __init__(self, node_type, name, path="", new_name=None, new_path=None, new_data=None, callback=None, debug=True):
        super().__init__(node_type, name, path, callback, debug)

        self.new_name = new_name
        self.new_path = new_path
        self.new_data = new_data

    def start(self):
        full_path = os.path.join(self.path, self.name)
        try:
            if self.new_name is not None:
                self.log.debug("Update name from %s to %s",
                               self.name, self.new_name)
                os.rename(full_path, os.path.join(self.path, self.new_name))
            elif self.new_path is not None:
                self.log.debug("Update path from %s to %s",
                               self.path, self.new_path)
                os.rename(full_path, os.path.join(self.new_path, self.name))
            elif self.new_data is not None:
                fd = os.open(full_path, os.O_RDWR)
                _stat = os.fstat(fd)
                output = os.read(fd, _stat.st_size)
                data = os.fsdecode(output)
                if data != self.new_data:
                    self.log.debug("Update data of %s from %s to %s",
                                   self.name, data, self.new_data)

                    # Accepted answer: https://stackoverflow.com/questions/17126037/how-to-delete-only-the-content-of-file-in-python/17126137#17126137
                    # When using ftruncate then \00 (NULL) characters will be added.
                    # Trying to get rid of them with os.lseek
                    os.ftruncate(fd, 0)
                    os.lseek(fd, 0, os.SEEK_SET)

                    os.write(fd, self.new_data.encode("utf-8"))
                else:
                    self.log.warning(
                        "Same data in %s. Didn't update file.", self.name)
                os.close(fd)
        except Exception as e:
            self.log.error(e)
        self.run_callback()


class DeleteQuery(Query):

    def __init__(self, node_type, name, path="", callback=None, debug=False):
        super().__init__(node_type, name, path, callback, debug)

    def start(self):
        full_path = os.path.join(self.path, self.name)
        if self.type == Types.DIRECTORY:
            os.rmdir(full_path)
        elif self.type == Types.DIRECTORIES:
            # TODO: Test if this works
            os.removedirs(full_path)
        elif self.type == Types.FILE:
            os.unlink(full_path)
        else:
            raise NotImplementedError(self.type)
        self.run_callback()
