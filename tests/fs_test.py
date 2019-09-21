'''
This code should run successfully.
https://www.rath.org/pyfuse3-docs/gotchas.html
'''

import os
import pytest
import logging

ROOT_DIR = "dir"
LOGGER = logging.getLogger(__name__)


def test_file():
    # test_file: FileNotFoundError when executing a second time. Why?
    file_path = os.path.join(ROOT_DIR, 'file_one')
    assert os.path.exists(file_path) is False
    with open(file_path, 'w+') as fh1:
        LOGGER.info(os.stat(file_path))
        fh1.write('foo')
        fh1.flush()
        LOGGER.info(os.stat(file_path))
        with open(file_path, 'a') as fh2:
            os.unlink(file_path)
            LOGGER.info(os.stat(file_path))
            assert 'file_one' not in os.listdir(ROOT_DIR)
            fh2.write('bar')
        LOGGER.info(os.stat(file_path))
        os.close(os.dup(fh1.fileno()))
        LOGGER.info(os.stat(file_path))
        fh1.seek(0)
        assert fh1.read() == "foobar"
    LOGGER.info(os.stat(file_path))
    assert os.path.exists(file_path) is False
    # os.remove(file_path)


def test_file_abs():
    file_path = os.path.abspath(os.path.join(ROOT_DIR, "file_one"))
    assert os.path.exists(file_path) is False
    with open(file_path, 'w+') as fh1:
        fh1.write('foo')
        fh1.flush()
        with open(file_path, 'a') as fh2:
            os.unlink(file_path)
            assert 'file_one' not in os.listdir(ROOT_DIR)
            fh2.write('bar')
        os.close(os.dup(fh1.fileno()))
        fh1.seek(0)
        assert fh1.read() == "foobar"
    assert os.path.exists(file_path) is False
    # os.remove(file_path)


'''
def test_dir():
    os.makedirs(os.path.join(ROOT_DIR, "dir_one"), exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, "dir_two", "dir_three"), exist_ok=True)

    assert os.path.isdir(os.path.join(ROOT_DIR, "dir_one"))
    assert os.path.isdir(os.path.join(ROOT_DIR, "dir_two"))
    assert os.path.isdir(os.path.join(ROOT_DIR, "dir_two", "dir_three"))

    os.rmdir(os.path.join(ROOT_DIR, "dir_one"))
    os.removedirs(os.path.join(ROOT_DIR, "dir_two"))

    list_dir = os.listdir(ROOT_DIR)
    assert 'dir_one' not in list_dir
    assert os.path.isdir(os.path.join(ROOT_DIR, "dir_one")) is False
    assert 'dir_two' not in list_dir
    assert os.path.isdir(os.path.join(ROOT_DIR, "dir_two")) is False
    assert os.path.isdir(os.path.join(
        ROOT_DIR, "dir_two", "dir_three")) is False
'''
