import paho.mqtt.client as mqtt
import pytest
import os

ROOT_DIR = "dir"


def test_init():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.connect("localhost")
    client.loop_start()
    client.publish("topic/test", payload="{\"msg\": \"test\"}")
    client.loop_stop()
    client.disconnect()


def on_connect(client, userdata, flags, rc):
    assert rc == 0


def test_topic():
    assert os.path.isdir(os.path.join(ROOT_DIR, "topic"))
    assert os.path.isdir(os.path.join(ROOT_DIR, "topic", "test"))


def test_msg():
    file_path = os.path.join(ROOT_DIR, "topic", "test", "msg")
    assert os.path.isfile(file_path)
    with open(file_path) as f:
        out = f.read()
        assert out == "test"
