import os
import time
import logging

import paho.mqtt.client as mqtt


LOGGER = logging.getLogger(__name__)
ROOT_DIR = "dir"


def test_init():
    LOGGER.info("test_init start")
    client = mqtt.Client()
    client.on_connect = on_connect
    assert client.connect("localhost") == 0
    client.loop_start()
    client.publish("topic/test", payload="{\"msg\": \"test\"}")
    client.loop_stop()
    assert client.disconnect() == 0
    LOGGER.info("test_init end")


def on_connect(client, userdata, flags, rc):
    assert rc == 0


def test_topic():
    time.sleep(2)
    LOGGER.info("test_topic start")
    LOGGER.info(os.listdir(ROOT_DIR))
    LOGGER.info("Path: %s", os.path.join(ROOT_DIR, "topic"))
    assert os.path.isdir(os.path.join(ROOT_DIR, "topic"))
    LOGGER.info(os.listdir(os.path.join(ROOT_DIR, "topic")))
    assert os.path.isdir(os.path.join(ROOT_DIR, "topic", "test"))
    LOGGER.info("test_topic end")


def test_msg():
    time.sleep(2)
    LOGGER.info("test_msg start")
    file_path = os.path.join(ROOT_DIR, "topic", "test", "msg")
    assert os.path.exists(file_path)
    with open(file_path, "r") as f:
        out = f.read()
        assert out == "test"
        LOGGER.info("output: %s", out)
    LOGGER.info("test_msg end")


def test_finish():
    time.sleep(3)
    os.unlink(os.path.join(ROOT_DIR, "topic", "test", "msg"))
    os.removedirs(os.path.join(ROOT_DIR, "topic"))
