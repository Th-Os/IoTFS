import os
import stat
import logging

ROOT_DIR = "dir"
LOGGER = logging.getLogger(__name__)


def test_file():
    '''
    This code should run successfully.
    https://www.rath.org/pyfuse3-docs/gotchas.html
    '''
    file_path = os.path.join(ROOT_DIR, 'file_one')
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


def test_file_std():
    file_path = os.path.join(ROOT_DIR, 'file_three')
    fd = os.open(file_path, os.O_RDWR | os.O_CREAT)
    assert os.path.exists(file_path) is True
    os.write(fd, b"bla")
    os.close(fd)
    fd = os.open(file_path, os.O_RDWR | os.O_CREAT)
    size = os.fstat(fd).st_size
    out = os.read(fd, size)
    assert out == b"bla"
    os.close(fd)
    os.unlink(file_path)
    assert os.path.exists(file_path) is False


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


def test_stat():
    file_path = os.path.join(ROOT_DIR, 'file_four')
    fd = os.open(file_path, os.O_CREAT)
    os.close(fd)
    assert os.path.exists(file_path) is True
    _stat = os.stat(file_path)
    assert type(_stat) == os.stat_result
    _statvfs = os.statvfs(file_path)
    assert type(_statvfs) == os.statvfs_result
    os.unlink(file_path)
    assert os.path.exists(file_path) is False


def test_mode():
    file_path = os.path.join(ROOT_DIR, 'file_five')
    fd = os.open(file_path, os.O_CREAT)
    os.close(fd)
    assert os.path.exists(file_path) is True
    _stat = os.stat(file_path)
    LOGGER.info(stat.S_IWRITE)
    LOGGER.info(_stat.st_mode)
    os.chmod(file_path, stat.S_IWRITE)
    LOGGER.info(_stat.st_mode)
