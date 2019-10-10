import time

from utils import _logging


class Listener():

    def __init__(self, queue, interval=1):
        self.log = _logging.create_logger("Listener")
        self.queue = queue
        self.interval = interval

    # TODO: 22 Readdir calls at the beginning of each session.
    def start(self):
        try:
            while True:
                time.sleep(self.interval)
                item = self.queue.get()
                self.log.warning(self.queue.qsize())

                self.log.info(item)
                self.log.info(item.event.name)
                self.log.info(item.operation.name)
                self.log.info(item.node)
                self.queue.task_done()
                self.log.warning(self.queue.empty())
        except Exception as e:
            self.log.error(e)
