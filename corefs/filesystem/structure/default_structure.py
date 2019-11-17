import uuid

from corefs.structure._structure import Structure, Element, Data

# DefaultStructure should contain name files of parents and childs as folders in parent


class DefaultStructure(Structure):

    def __init__(self):
        super().__init__()


class Node(Element):

    def __init__(self, name):
        identifier = str(uuid.uuid4()).replace("-", "_")
        super().__init__(identifier, name)


class Value(Data):

    def __init__(self, name, value, allowed_value):
        super().__init__(name, value)
        self.allowed_value = allowed_value
