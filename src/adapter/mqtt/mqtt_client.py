import paho.mqtt.client as mqtt
import os
import json

from adapter._client import Client
from adapter._adapter import Events


class MQTT_Client(mqtt.Client, Client):

    def __init__(self, entry_point, debug):
        mqtt.Client.__init__(self, "Listener")
        Client.__init__(self, "client.mQTT")
        self.log.info("Starting Client \"%s\"",
                      self.__class__.__name__)
        self.entry = os.path.join(".", entry_point)

    def on_connect(self, client, userdata, flags, rc):
        self.log.info("Connected with result code %s.", str(rc))

    def on_subscribe(self, mqttc, obj, mid, granted_qos):
        self.log.info("Subscribed: %s, Qos: %s", str(mid), str(granted_qos))

    def on_publish(self, mqttc, obj, mid):
        # self.log.info("mid: %s", str(mid))
        pass

    def on_log(self, mqttc, obj, level, string):
        # self.log.debug(string)
        pass

    def on_message(self, client, userdata, msg):
        # omitting system messages -> needs to be done in dev
        if "$SYS" in msg.topic:
            return
        payload = msg.payload.decode("utf-8")

        self.log.info("New message in topic: %s", msg.topic)
        self.log.debug("With payload: %s", payload)

        # https://stackoverflow.com/questions/14826888/python-os-path-join-on-a-list
        path = os.path.join(*msg.topic.split("/"))
        directory = os.path.join(self.entry, path)
        self.log.debug("Using directory: %s", directory)
        self.log.debug("Abs path: %s", os.path.abspath(directory))

        os.makedirs(os.path.abspath(directory), exist_ok=True)

        payload = json.loads(payload)

        self.notify(Events.CREATE, msg.topic, payload)

    def run(self):
        self.connect("localhost", 1883, 60)
        self.subscribe([("#", 0), ("$SYS/#", 0)])
        self.loop_forever()
