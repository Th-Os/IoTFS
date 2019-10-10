from filesystem.fs import FileSystem


class StandardFileSystem(FileSystem):

    def __init__(self, mount_point, debug=False):
        super(StandardFileSystem, self).__init__(mount_point, debug)
        self.log.error("HELLO STANDARDFS")

    async def open(self, inode, flags, ctx):
        self.log.warning("hello open call")
        self.log.error("opened inode %d", inode)
        return super().open(inode, flags, ctx)

    async def create(self, parent_inode, name, mode, flags, ctx):
        self.log.warning("hello create call")
        value = await super().create(parent_inode, name, mode, flags, ctx)
        self.log.error("created %s", name)
        self.log.error("value: %d", value)
        return value

    async def opendir(self, inode, ctx):
        self.log.warning("hello opendir call!!!")
        return await super().opendir(inode, ctx)
