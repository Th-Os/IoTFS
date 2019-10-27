import os
import time
import logging

INPUT_PATH = "input.watch"
OUTPUT_PATH = "output.watch"
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
ROOT_DIR = os.path.abspath("dir")

"""

def test_init():
    assert os.path.exists(INPUT_PATH)
    LOGGER.debug(ROOT_DIR)


def test_create():
    with open(INPUT_PATH, "w") as f:
        f.write("create:a_dir,a_file")
    time.sleep(2)
    with open(INPUT_PATH, "r") as f:
        assert "" == f.read()
    LOGGER.debug(os.listdir(ROOT_DIR))
    assert os.path.exists(os.path.join(ROOT_DIR, "a_dir"))
    assert os.path.exists(os.path.join(ROOT_DIR, "a_dir", "a_file"))


def test_create_with_content():
    with open(INPUT_PATH, "w") as f:
        f.write("create:a_dir,b_file,content")
    time.sleep(2)
    with open(INPUT_PATH, "r") as f:
        assert "" == f.read()
    LOGGER.debug(os.listdir(ROOT_DIR))
    assert os.path.exists(os.path.join(ROOT_DIR, "a_dir", "b_file"))
    with open(os.path.join(ROOT_DIR, "a_dir", "b_file")) as f:
        out = f.read()
        assert out == "content"
        LOGGER.debug("output: %s", out)


def test_create_multiple_dirs():
    with open(INPUT_PATH, "w") as f:
        f.write("create:a_dir/b_dir")
    time.sleep(2)
    with open(INPUT_PATH, "r") as f:
        assert "" == f.read()
    LOGGER.debug(os.listdir(ROOT_DIR))
    LOGGER.debug(os.listdir(os.path.join(ROOT_DIR, "a_dir")))
    assert os.path.exists(os.path.join(ROOT_DIR, "a_dir", "b_dir"))


def test_update_content():
    with open(INPUT_PATH, "w") as f:
        f.write("update:a_dir,b_file,content>new_content")
    time.sleep(2)
    with open(INPUT_PATH, "r") as f:
        assert "" == f.read()
    with open(os.path.join(ROOT_DIR, "a_dir", "b_file")) as f:
        out = f.read()
        assert out == "new_content"
        LOGGER.debug("output: %s", out)


def test_update_name():
    with open(INPUT_PATH, "w") as f:
        f.write("update:a_dir,a_file,name>z_file")
    time.sleep(2)
    with open(INPUT_PATH, "r") as f:
        assert "" == f.read()
    assert os.path.exists(os.path.join(ROOT_DIR, "a_dir", "z_file"))


def test_update_path():
    with open(INPUT_PATH, "w") as f:
        f.write("update:a_dir,z_file,path>.")
    time.sleep(2)
    with open(INPUT_PATH, "r") as f:
        assert "" == f.read()
    assert os.path.exists(os.path.join(ROOT_DIR, "z_file"))


def test_update_path_multiple():
    with open(INPUT_PATH, "w") as f:
        f.write("update:.,z_file,path>a_dir/b_dir")
    time.sleep(2)
    with open(INPUT_PATH, "r") as f:
        assert "" == f.read()
    assert os.path.exists(os.path.join(ROOT_DIR, "a_dir", "b_dir", "z_file"))


def test_read():
    with open(INPUT_PATH, "w") as f:
        f.write("read:a_dir,b_file")
    time.sleep(2)
    with open(INPUT_PATH, "r") as f:
        assert "" == f.read()
    with open(OUTPUT_PATH, "w+") as f:
        assert "new_content" == f.read()
        f.truncate(0)


'''
def test_delete_a_file():
    with open(INPUT_PATH, "w") as f:
        f.write("delete:a_dir,a_file")
    time.sleep(2)
    with open(INPUT_PATH, "r") as f:
        assert "" == f.read()


def test_delete_multiple_dirs():
    with open(INPUT_PATH, "w") as f:
        f.write("delete:a_dir/b_dir")
    time.sleep(2)
    with open(INPUT_PATH, "r") as f:
        assert "" == f.read()
'''
"""
