'''
This code should run successfully.
https://www.rath.org/pyfuse3-docs/gotchas.html
'''

import os

with open('dir/file_one', 'w+') as fh1:
    fh1.write('foo')
    fh1.flush()
    with open('dir/file_one', 'a') as fh2:
        os.unlink('dir/file_one')
        assert 'file_one' not in os.listdir('dir')
        fh2.write('bar')
    os.close(os.dup(fh1.fileno()))
    fh1.seek(0)
    print(fh1.read())
    assert fh1.read() == 'foobar'
