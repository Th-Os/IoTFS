import paho.mqtt.client as mqtt
import pytest
import os

ROOT_DIR = "dir"


class MQTT_Test():

    def test_init(self):
        client = mqtt.Client()
        client.connect("localhost")
        client.loop_start()
        client.publish("topic/test", payload="{\"msg\": \"test\"}")
        client.loop_stop()
        client.disconnect()

    def test_topic(self):
        assert os.path.isdir(os.path.join(ROOT_DIR, "topic"))
        assert os.path.isdir(os.path.join(ROOT_DIR, "topic", "test"))

    def test_msg(self):
        file_path = os.path.join(ROOT_DIR, "topic", "test", "msg")
        assert os.path.isfile(file_path)
        with open(file_path) as f:
            out = f.read()
            assert out == "test"
