from filesystem.fs import FileSystem


class StandardFileSystem(FileSystem):

    def __init__(self, mount_point, debug=False):
        super().__init__(mount_point, debug)
