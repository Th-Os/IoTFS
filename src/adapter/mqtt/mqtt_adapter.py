from adapter._adapter import Adapter
from adapter.mqtt.mqtt_client import MQTT


class MQTTAdapter(Adapter):

    def __init__(self, entry_point, debug=False):
        super().__init__()
        self.client = MQTT(entry_point, debug)

    def create(self, type, name, path, data=None):
        pass

    def read(self, name, path):
        pass

    def update(self, type, name, path, new_name=None, new_path=None, new_data=None):
        pass

    def delete(self, type, name, path):
        pass
