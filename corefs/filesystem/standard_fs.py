from corefs.filesystem.fs import FileSystem


class StandardFileSystem(FileSystem):

    def __init__(self, mount_point, structure_json=None, debug=False):
        super().__init__(mount_point, structure_json, debug)
