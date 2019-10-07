import os

from adapter._adapter import Adapter
from adapter.queries import CreateQuery, UpdateQuery, Types
import utils


class MQTT_Adapter(Adapter):

    def __init__(self, client):
        super().__init__(client)
        self.log = utils.init_logging("adapter.mqtt", debug=True)

    def create(self, topic, msg):
        topics = topic.split("/")
        path = os.path.join(*topics[:-1])
        name = topics[-1]
        CreateQuery(Types.DIRECTORIES, name, path,
                    callback=self.on_create).start()
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
                    CreateQuery(Types.FILE, key, directory, value,
                                callback=self.on_create).start()
            except Exception as e:
                self.log.error(e)

    def read(self, name, path):
        pass

    def update(self, type, name, path, new_name=None, new_path=None, new_data=None):
        pass

    def delete(self, type, name, path):
        pass

    def on_create(self, *args):
        self.log.info("On CreateQuery")
