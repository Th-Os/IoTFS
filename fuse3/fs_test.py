'''
This code should run successfully.
https://www.rath.org/pyfuse3-docs/gotchas.html
'''

import os
import pytest


def test_file():
    with open('dir/file_one', 'w+') as fh1:
        fh1.write('foo')
        fh1.flush()
        with open('dir/file_one', 'a') as fh2:
            os.unlink('dir/file_one')
            print(os.listdir('dir'))
            assert 'file_one' not in os.listdir('dir')
            fh2.write('bar')
        os.close(os.dup(fh1.fileno()))
        fh1.seek(0)
        print(fh1.read())
        fh1.seek(0)
        assert fh1.read() == "foobar"
    os.remove('dir/file_one')


def test_dir():
    os.makedirs("./dir/dir_one", exist_ok=True)
    os.makedirs("./dir/dir_two/dir_three", exist_ok=True)

    assert os.path.isdir("./dir/dir_one")
    assert os.path.isdir("./dir/dir_two")
    assert os.path.isdir("./dir/dir_two/dir_three")

    os.removedirs("./dir/dir_one")
    os.removedirs("./dir/dir_two")

    assert os.path.isdir("./dir/dir_one") is False
    assert os.path.isdir("./dir/dir_two") is False
    assert os.path.isdir("./dir/dir_two/dir_three") is False
