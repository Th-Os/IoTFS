import os
import stat


class Types():

    FILE = 0
    DIRECTORY = 1
    DIRECTORIES = 2


class Query():

    # TODO: Query should be extended with permissions
    def __init__(self, node_type, name, path, callback):
        assert "MOUNT_POINT" in os.environ
        mount_point = os.environ["MOUNT_POINT"]

        self.type = node_type
        self.name = name
        self.path = os.path.join(mount_point, path)
        self.callback = callback

    def start(self):
        pass


class CreateQuery(Query):

    def __init__(self, node_type, name, path, data=None, callback=None):
        super().__init__(node_type, name, path, callback)
        self.data = data

    def start(self):
        full_path = os.path.join(self.path, self.name)
        if self.type == Types.FILE:
            fd = os.open(full_path, os.O_CREAT | os.O_WRONLY, stat.S_IRWXO)
            assert os.path.exists(full_path) is True
            if self.data is not None:
                os.write(fd, self.data.encode("utf-8"))
            os.close(fd)
        elif self.type == Types.DIRECTORY:
            os.mkdir(full_path)
        elif self.type == Types.DIRECTORIES:
            os.makedirs(full_path, exist_ok=True)
        else:
            pass  # TODO: Do something ... Maybe errors?
        if self.callback is not None:
            self.callback()


class ReadQuery(Query):

    # reading file and reading directory (results in list)
    def __init__(self, node_type, name, path, callback=None):
        super().__init__(node_type, name, path, callback)


class UpdateQuery(Query):

    def __init__(self, node_type, name, path, new_name=None, new_path=None, new_data=None, callback=None):
        super().__init__(node_type, name, path, callback)

        # TODO: check if and what changes
        self.new_name = new_name
        self.new_path = new_path
        self.new_data = new_data

    def start(self):
        full_path = os.path.join(self.path, self.name)

        if self.new_name is not None:
            pass
        elif self.new_path is not None:
            pass
        elif self.new_data is not None:
            fd = os.open(full_path, os.O_WRONLY |
                         os.O_TRUNC, stat.S_IRWXO)
            assert os.path.exists(full_path) is True
            os.write(fd, self.new_data.encode("utf-8"))
            os.close(fd)
        if self.callback is not None:
            self.callback()


class DeleteQuery(Query):

    def __init__(self, node_type, name, path, callback=None):
        super().__init__(node_type, name, path, callback)
