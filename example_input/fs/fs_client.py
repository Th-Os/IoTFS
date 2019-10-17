import time
import os

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from corefs.input._client import Client
from corefs.input._adapter import Events
from corefs.utils import _logging


class FS_Client(Client):

    def __init__(self, debug=True):
        super().__init__("client.fs", debug)

    def run(self):
        input_path = os.path.abspath(".")
        watched_file = "input.watch"
        fd = os.open(os.path.join(input_path, watched_file),
                     os.O_CREAT | os.O_WRONLY)
        os.close(fd)
        handler = Handler(self, watched_file)
        observer = Observer()
        watch = observer.schedule(handler, input_path)
        self.log.info(watch.path)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    def test(self):
        path = "test"
        name = "file"
        self.notify(Events.CREATE, name, path, content="1+1=1")
        self.log.debug("after CREATE")
        self.notify(Events.UPDATE, name, path, new_content="1+1=2")
        self.log.debug("after UPDATE")
        self.notify(Events.READ, name, path, callback=self.on_read)
        self.log.debug("after READ")
        self.notify(Events.DELETE, name, path)
        self.log.debug("after DELETE")

    def on_read(self, *args):
        with open("output.watch", "w+") as f:
            f.write(args[0])


class Handler(FileSystemEventHandler):

    def __init__(self, client, file):
        self.log = _logging.create_logger("watchdog.handler", True)
        self.file = file
        self.client = client

    def on_modified(self, event):
        self.log.info(event)
        if self.file in event.src_path and os.stat(self.file).st_size > 0:
            with open(self.file, "r") as f:
                command = f.read()
                self.log.info(command)
                file_event = command.split(":")[0]
                parts = command.split(":")[1].split(",")
                dir_path = parts[0]
                name = None
                if len(parts) > 1:
                    name = parts[1]
                content = None
                if len(parts) > 2:
                    content = parts[2]
                self.log.info("Event: %s", file_event)
                if file_event == "create":
                    self.client.notify(
                        Events.CREATE, dir_path, name=name, content=content)
                elif file_event == "update":
                    mode = content.split(">")[0]
                    value = content.split(">")[1]
                    self.log.info(mode)
                    self.log.info(value)
                    if mode == "content":
                        self.client.notify(Events.UPDATE, name,
                                           dir_path, new_content=value)
                    elif mode == "name":
                        self.client.notify(Events.UPDATE, name,
                                           dir_path, new_name=value)
                    elif mode == "path":
                        self.client.notify(Events.UPDATE, name,
                                           dir_path, new_path=value)
                    else:
                        self.log.warning("Undefined mode %s", mode)
                elif file_event == "read":
                    self.client.notify(Events.READ, name, dir_path,
                                       callback=self.client.on_read)
                elif file_event == "delete":
                    self.client.notify(Events.DELETE, name, dir_path)
            os.truncate(self.file, 0)
