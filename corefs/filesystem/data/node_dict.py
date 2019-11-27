from corefs.utils import _logging


class NodeDict(dict):

    def __init__(self, logger=None):
        super().__init__()
        if logger is not None:
            self.log = logger
        else:
            self.log = _logging.create_logger("NodeDict", debug=True)
