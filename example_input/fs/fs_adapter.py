import os

from corefs.input._adapter import Adapter
from corefs.input.queries import CreateQuery, ReadQuery, UpdateQuery, DeleteQuery, Types

from corefs.utils import _logging


class FS_Adapter(Adapter):

    def __init__(self, client):
        super().__init__(client, True)
        self.log.info("Init Adapter with " + client.__class__.__name__)

    def create(self, path, name=None, content=None):
        # if we assume that path doesn't end with sep
        if path.count(os.sep) > 0:
            self.log.debug("create multiple directories")
            last_idx = path.rfind(os.sep)
            dir_name = path[last_idx+1:]
            dir_path = path[:last_idx]
            self.log.debug(dir_name)
            self.log.debug(dir_path)
            CreateQuery(Types.DIRECTORIES, dir_name, dir_path).start()
        else:
            self.log.debug("create one directory in root dir")
            CreateQuery(Types.DIRECTORY, path, "").start()
        if name is not None:
            CreateQuery(Types.FILE, name, path, data=content).start()

    def read(self, name, path, callback=None):
        self.log.debug("start read")
        if callback is not None:
            ReadQuery(Types.FILE, name, path, callback=callback).start()
        self.log.debug("end read")

    def update(self, name, path, new_name=None, new_path=None, new_content=None):
        self.log.debug("start update")
        if new_content is not None:
            UpdateQuery(Types.FILE, name, path, new_data=new_content).start()
        if new_name is not None:
            UpdateQuery(Types.FILE, name, path, new_name=new_name).start()
        if new_path is not None:
            UpdateQuery(Types.FILE, name, path, new_path=new_path).start()
        self.log.debug("end update")

    def delete(self, name, path):
        DeleteQuery(Types.FILE, name, path)
        if path.count(os.sep) > 0:
            DeleteQuery(Types.DIRECTORIES, path, "")
        else:
            DeleteQuery(Types.DIRECTORY, path, "")
