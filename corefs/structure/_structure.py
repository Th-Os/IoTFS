# reads in schema file and orders items.


class Structure():

    def __init__(self):
        pass


class Data():

    def __init__(self, name, value=None):
        self.name = name
        self.value = value


class Element():

    def __init__(self, id, name):
        self.id = id
        self.name = name
