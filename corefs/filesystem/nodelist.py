from corefs.filesystem.node import Node

# TODO implement further and evaluate use.


class NodeList():

    def __init__(self):
        self.list = dict()

    def add(self, index, item):
        if isinstance(item, Node):
            if index in self.list:
                raise(IndexError("Index " + str(index) + " does already exist."))
            self.list[index](item)
        else:
            raise(TypeError("Item is not of type Node but " + str(type(item))))
