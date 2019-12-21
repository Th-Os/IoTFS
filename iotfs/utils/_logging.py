# -*- coding: utf-8 -*-

import logging
from sys import stdout
import os

LOGGER_LIST = []


def create_logger(name="iotfs", debug=False, with_file=True):
    """ Creates a logger.

    """

    formatter = logging.Formatter('[%(name)s | %(threadName)s | %(asctime)s.%(msecs)03d] %(levelname)s: '
                                  '%(message)s', datefmt="%Y-%m-%d %H:%M:%S")

    logger = logging.getLogger(
        name) if name == "iotfs" else logging.getLogger("iotfs." + name)

    if logger.name in LOGGER_LIST:
        return logger

    if with_file:
        if os.path.isdir("logs") is False:
            os.mkdir("logs")
        file_path = os.path.join("logs", logger.name + ".log")
        if os.path.exists(file_path):
            os.unlink(file_path)
        fh = logging.FileHandler(file_path, "w+")
    sh = logging.StreamHandler(stream=stdout)

    if with_file:
        fh.setFormatter(formatter)
    sh.setFormatter(formatter)

    if len(logger.handlers) > 0:
        logger.handlers = []

    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if with_file:
        logger.addHandler(fh)
    logger.addHandler(sh)

    # duplicate logs:
    # https://stackoverflow.com/questions/19561058/duplicate-output-in-simple-python-logging-configuration/19561320
    logger.propagate = False

    LOGGER_LIST.append(logger.name)
    logger.info("Initialize Logger: %s", logger.name)

    return logger
