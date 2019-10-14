import time

from corefs.utils import _logging


class Listener():

    def __init__(self, queue=None, interval=1):
        self.log = _logging.create_logger("Listener")
        self.queue = queue

        # interval currently emitted -> faster processing.
        self.interval = interval

    def setQueue(self, queue):
        self.queue = queue

    # TODO: 22 Readdir calls at the beginning of each session.
    def start(self):
        if self.queue is None:
            raise ValueError("Queue is missing.")
        try:
            while True:
                # time.sleep(self.interval)
                item = self.queue.get()
                self.log.warning(self.queue.qsize())
                self.process(item)
                self.queue.task_done()
        except Exception as e:
            self.log.error(e)

    def process(self, item):
        self.log.info(item)
        self.log.info(item.event.name)
        self.log.info(item.operation.name)
        self.log.info(item.node)
