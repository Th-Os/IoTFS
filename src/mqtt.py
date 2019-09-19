import paho.mqtt.client as mqtt
import os
import json

import utils


class MQTT(mqtt.Client):

    def __init__(self, entry_point, debug):
        super().__init__("Listener")
        self.log = utils.init_logging(self.__class__.__name__, debug=debug)
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

        # This could be related to the IOCTL error
        os.makedirs(os.path.abspath(directory), exist_ok=True)

        payload = json.loads(payload)

        self.log.debug(
            "going to open files (%d) and write in them.", len(payload.items()))

        for key, value in payload.items():
            self.log.info("Key: %s, value: %s", key, value)
            try:
                # This results in IOCTL NOT IMPLEMENTED ERROR -> System freezes
                self.log.debug("will open: %s", str(
                    os.path.join(os.path.abspath(directory), key)))
                if os.path.isfile(os.path.join(os.path.abspath(directory), key)):
                    with open(os.path.join(os.path.abspath(directory), key), 'w') as f:
                        self.log.debug("Will write %s to %s", value, f)
                        size = f.write(value)
                        self.log.debug("Wrote %d characters", size)
                else:
                    self.log.debug("File doesn't exist. Creating file.")
                    with open(os.path.join(os.path.abspath(directory), key), 'x') as f:
                        self.log.debug("Will write %s to %s", value, f)
                        size = f.write(value)
                        self.log.debug("Wrote %d characters", size)
            except Exception as e:
                self.log.error(e.with_traceback().msg)

    def run(self):
        self.connect("localhost", 1883, 60)
        self.subscribe([("#", 0), ("$SYS/#", 0)])
        self.loop_forever()


async def start_async(entry_point, debug=False):
    MQTT(entry_point, debug).run()


def start(entry_point, debug=False):
    MQTT(entry_point, debug).run()
