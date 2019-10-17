import os

from corefs.input._adapter import Adapter
from corefs.input.queries import CreateQuery, UpdateQuery, Types

from corefs.utils import _logging


class MQTT_Adapter(Adapter):

    def __init__(self, client):
        super().__init__(client)
        self.log = _logging.create_logger("mqtt.adapter", True)

    def create(self, topic, msg):
        topics = topic.split("/")
        path = os.path.join(*topics[:-1])
        name = topics[-1]
        CreateQuery(Types.DIRECTORIES, name, path).start()
        directory = os.path.join(*topics)
        for key, value in msg.items():
            self.log.debug("Key: %s, value: %s", key, value)

            try:

                file_path = os.path.join(os.path.abspath(directory), key)
                self.log.debug("Path of File: %s", file_path)

                if os.path.isfile(file_path):
                    self.log.debug("File does exist. Update file.")
                    UpdateQuery(Types.FILE, key, directory,
                                new_data=value).start()
                else:
                    self.log.debug("File doesn't exist. Creating file.")
                    self.log.debug("With content: %s", value)
                    CreateQuery(Types.FILE, key, directory, data=value).start()
            except Exception as e:
                self.log.error(e)

    def read(self, name, path):
        pass

    def update(self, type, name, path, new_name=None, new_path=None, new_data=None):
        pass

    def delete(self, type, name, path):
        pass
