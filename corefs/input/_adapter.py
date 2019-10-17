from enum import Enum

from corefs.utils import _logging


class Adapter():

    def __init__(self, client, debug=False):
        self.log = _logging.create_logger(self.__class__.__name__, debug)
        self.client = client

    def start(self):
        self.client.register(Events.CREATE, self.create)
        self.client.register(Events.READ, self.read)
        self.client.register(Events.UPDATE, self.update)
        self.client.register(Events.DELETE, self.delete)
        self.client.run()

    def create(self, *args):
        raise NotImplementedError("Didn't implement create behavior.")

    def read(self, *args):
        raise NotImplementedError("Didn't implement read behavior.")

    def update(self, *args):
        raise NotImplementedError("Didn't implement update behavior.")

    def delete(self, *args):
        raise NotImplementedError("Didn't implement delete behavior.")


class Events(Enum):

    CREATE = 0
    READ = 1
    UPDATE = 2
    DELETE = 3
