import logging
from sys import stdout
import os


def create_logger(name="corefs", debug=False, with_file=True):
    formatter = logging.Formatter('[%(name)s | %(threadName)s | %(asctime)s.%(msecs)03d] %(levelname)s: '
                                  '%(message)s', datefmt="%Y-%m-%d %H:%M:%S")

    logger = logging.getLogger(
        name) if name == "corefs" else logging.getLogger("corefs." + name)

    if with_file:
        if os.path.isdir("logs") is False:
            os.mkdir("logs")
        fh = logging.FileHandler(os.path.join(
            "logs", logger.name + ".log"), "w+")
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

    logger.info("Initialize Logger: %s", logger.name)

    return logger
