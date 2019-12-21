# -*- coding: utf-8 -*-

import time

from iotfs.utils import _logging


class Listener():

    """
    Listener is a class that provides functionality to listen to the filesystem.
    It will check the queue and starts a processing step that needs to be implemented by a developer.

    ...

    Attributes
    ----------
    queue : queue.Queue
        a message queue from the file system
    interval : int, optional
        defines the time until a new processing takes place.

    """

    def __init__(self, queue=None, interval=0):
        """
        Parameters
        ----------
        queue : queue.Queue
            a message queue from the file system
        interval : int, optional
            defines the time until a new processing takes place.
        """
        self.log = _logging.create_logger("Listener")
        self.queue = queue
        self.interval = interval

    def setQueue(self, queue):
        self.queue = queue

    def start(self):
        if self.queue is None:
            raise ValueError("Queue is missing.")
        try:
            while True:
                if self.interval > 0:
                    time.sleep(self.interval)
                item = self.queue.get()
                self.process(item)
                self.queue.task_done()
        except Exception as e:
            self.log.error(e)

    def process(self, item):
        self.log.info(item)
        self.log.info(item.event.name)
        self.log.info(item.operation.name)
        self.log.info(item.node)
