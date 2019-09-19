'''
This code should run successfully.
https://www.rath.org/pyfuse3-docs/gotchas.html
'''

import os
import pytest

ROOT_DIR = "dir"


def test_file():
    with open(os.path.join(ROOT_DIR, 'file_one'), 'w+') as fh1:
        fh1.write('foo')
        fh1.flush()
        with open(os.path.join(ROOT_DIR, 'file_one'), 'a') as fh2:
            os.unlink(os.path.join(ROOT_DIR, 'file_one'))
            print(os.listdir(ROOT_DIR))
            assert 'file_one' not in os.listdir(ROOT_DIR)
            fh2.write('bar')
        os.close(os.dup(fh1.fileno()))
        fh1.seek(0)
        print(fh1.read())
        fh1.seek(0)
        assert fh1.read() == "foobar"
    os.remove(os.path.join(ROOT_DIR, 'file_one'))


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
