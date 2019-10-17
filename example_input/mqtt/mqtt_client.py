import paho.mqtt.client as mqtt
import os
import json

from corefs.input._client import Client
from corefs.input._adapter import Events


class MQTT_Client(mqtt.Client, Client):

    def __init__(self, debug=True):
        mqtt.Client.__init__(self, "Listener")
        Client.__init__(self, "client.mqtt", debug)
        self.log.info("Starting Client \"%s\"",
                      self.__class__.__name__)

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

        payload = json.loads(payload)

        self.notify(Events.CREATE, msg.topic, payload)

    def run(self):
        self.connect("localhost", 1883, 60)
        self.subscribe([("#", 0), ("$SYS/#", 0)])
        self.loop_forever()
