import json

from corefs.utils._fs_utils import Types, Encodings, LinkTypes, ROOT_INODE, STANDARD_MODE, LINK_MODE
from corefs.utils import _logging
from corefs.filesystem.data.data import Data


class Parser():

    def __init__(self):
        self.log = _logging.create_logger("Parser", debug=True)

    def parse(self, structure, data=Data()):
        obj = json.load(structure)

        nodes = obj.get("nodes", [])
        data = self.__create_root(obj.get("settings", {}), data)
        data = self.__create_nodes(nodes, obj.get("root_structure", []), data)
        data = self.__create_filters(nodes, obj.get("filters", []), data)

        return data

    def __create_root(self, settings, data):
        root_name = settings.get("root", "")
        data.add_entry(root_name, ROOT_INODE, node_type=Types.DIR)

    def __create_nodes(self, nodes, root_structure, data):
        for node in nodes:
            self.log.info(node.name)
            # data.add_entry()
        return data

    def __create_filters(self, nodes, filter, data):
        return data
