import uuid
import os

from corefs.structure._structure import Structure, Element, Data


class ExtendedStructure(Structure):

    def __init__(self):
        super().__init__()


class Node(Element):

    def __init__(self, name, relations=dict(), children=[], values=[], types=[], filters=dict()):
        identifier = str(uuid.uuid4()).replace("-", "_")
        super().__init__(identifier, name)
        self.relations = relations
        self.children = children
        self.values = values
        self.types = types
        self.filters = filters

    def create(self):
        if len(self.relations.keys()) > 0:
            self.__create_relations()
        if len(self.children) > 0:
            self.__create_children()
        if len(self.values) > 0:
            self.__create_values()
        if len(self.types) > 0:
            self.__create_types()
        if len(self.filters.keys()) > 0:
            self.__create_filters()

    def __create_relations(self):
        pass

    def __create_children(self):
        pass

    def __create_values(self):
        pass

    def __create_types(self):
        pass

    def __create_filters(self):
        pass


class Value(Data):

    def __init__(self, name, value, allowed_value):
        super().__init__(name, value)
        self.allowed_value = allowed_value


class Sensor(Node):

    def __init__(self, root, name, sensor_types, sensor_node=None, values=[]):
        super().__init__(root, name)
        self.sensor_types = sensor_types
        self.sensor_node = sensor_node
        self.values = values

    def create(self):
        super().create()
        with open(os.path.join(self.path, "sensor_types"), "w+") as f:
            for sensor_type in self.sensor_types:
                f.write(sensor_type + "\n")
        os.mkdir(os.path.join(self.path, "values"))
        for value in self.values:
            value.create(os.path.join(self.path, "values"))
        os.symlink(self.sensor_node.path, os.path.join(
            self.path, "connected_to"))
        self.create_by_sensor_type()

    def create_by_sensor_type(self):
        by_type = os.path.join(self.root, "by_sensor_type")
        if not os.path.exists(by_type):
            os.mkdir(by_type)
        for sensor_type in self.sensor_types:
            type_dir = os.path.join(by_type, sensor_type)
            if not os.path.exists(type_dir):
                os.mkdir(type_dir)
            os.symlink(self.path, os.path.join(
                type_dir, self.name))

    def update(self, value_name, value_data, allowed_values=None):
        for value in self.values:
            if value.name == value_name:
                value.update(value_data, allowed_values)


class SensorNode(Node):

    def __init__(self, root, name, room=None, ap=None, sensors=[]):
        super().__init__(root, name)
        self.sensors = sensors
        self.room = room
        self.ap = ap

    def create(self):
        super().create()
        os.mkdir(os.path.join(self.path, "sensors"))
        for sensor in self.sensors:
            sensor.sensor_node = self
            sensor.create()
            os.symlink(sensor.path, os.path.join(
                self.path, "sensors", sensor.name))
        os.symlink(self.room.path, os.path.join(self.path, "in_room"))
        os.symlink(self.ap.path, os.path.join(self.path, "connected_to"))


class Room(Node):

    def __init__(self, root, name, building=None, ap=None, nodes=[]):
        super().__init__(root, name)
        self._nodes = nodes
        self.building = building
        self.ap = ap

        for node in self.nodes:
            node.room = self

    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, new_nodes):
        self._nodes = new_nodes
        for node in self._nodes:
            node.room = self
            os.symlink(node.path, os.path.join(self.path, "nodes", node.name))

    def create(self):
        super().create()
        os.mkdir(os.path.join(self.path, "nodes"))
        for node in self._nodes:
            node.room = self
            os.symlink(node.path, os.path.join(self.path, "nodes", node.name))
        os.symlink(self.building.path, os.path.join(self.path, "in_building"))
        os.symlink(self.ap.path, os.path.join(self.path, "has_access_point"))


class AP(Node):

    def __init__(self, root, name, network=None, room=None, nodes=[]):
        super().__init__(root, name)
        self.network = network
        self.room = room
        if self.room is not None:
            self._nodes = self.room.nodes
            self.room.ap = self
        else:
            self._nodes = nodes

        for node in self.nodes:
            node.ap = self

    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, new_nodes):
        self._nodes = new_nodes
        for node in self._nodes:
            node.room = self
            os.symlink(node.path, os.path.join(self.path, "nodes", node.name))

    def create(self):
        super().create()
        os.mkdir(os.path.join(self.path, "nodes"))
        for node in self._nodes:
            node.ap = self
            node.create()
            os.symlink(node.path, os.path.join(self.path, "nodes", node.name))
        os.symlink(self.network.path, os.path.join(self.path, "connected_to"))
        os.symlink(self.room.path, os.path.join(self.path, "in_room"))


class Building(Node):

    def __init__(self, root, name, network=None, rooms=[], nodes=[]):
        super().__init__(root, name)
        self.nodes = nodes
        self.network = network
        self.rooms = rooms

        for room in self.rooms:
            room.building = self

    def create(self):
        super().create()
        os.mkdir(os.path.join(self.path, "rooms"))
        for room in self.rooms:
            room.building = self
            room.create()
            os.symlink(room.path, os.path.join(self.path, "rooms", room.name))

        os.symlink(self.network.path, os.path.join(self.path, "has_network"))

        self.create_by_building()

    def create_by_building(self):
        by_building = os.path.join(self.root, "by_building")
        if not os.path.exists(by_building):
            os.mkdir(by_building)
        os.symlink(self.path, os.path.join(by_building, self.name))


class Network(Node):

    def __init__(self, root, name, building=None, aps=[]):
        super().__init__(root, name)
        self.building = building
        self.aps = aps

    def create(self):
        super().create()
        os.mkdir(os.path.join(self.path, "access points"))
        for ap in self.aps:
            ap.network = self
            ap.create()
            os.symlink(ap.path, os.path.join(
                self.path, "access points", ap.name))
        self.building.network = self
        self.building.create()
        os.symlink(self.building.path, os.path.join(self.path, "in_building"))
        self.create_by_network()

    def create_by_network(self):
        by_network = os.path.join(self.root, "by_network")
        if not os.path.exists(by_network):
            os.mkdir(by_network)
        os.symlink(self.path, os.path.join(self.root, "by_network", self.name))
