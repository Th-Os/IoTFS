from corefs.utils import _logging


class Client():

    def __init__(self, name, debug=False):
        self.name = name
        self.log = _logging.create_logger(self.__class__.__name__, debug)
        self.log.info("Init %s", name)
        self.observers = dict()

    def run(self):
        raise NotImplementedError(
            "Method \"run\" of class " + self.__class__.__name__ + " not implemented.")

    def register(self, event, callback):
        if event not in self.observers:
            self.observers[event] = []
        self.observers[event].append(callback)

    def deregister(self, event, callback):
        if event in self.observers:
            callbacks = self.observers[event]
            for cb in callbacks:
                if cb == callback:
                    self.observers[event].remove(callback)

    def notify(self, event, *args, **kwargs):
        self.log.debug("Event ({0}) with {1}".format(event.name, args))
        if event in self.observers:
            for cb in self.observers[event]:
                cb(*args, **kwargs)
