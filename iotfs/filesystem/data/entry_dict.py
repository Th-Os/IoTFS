# -*- coding: utf-8 -*-

from iotfs.utils import _logging


class EntryDict(dict):

    """
    Entrydict inherits dict functionalities and provides further methods to manipulate entries.

    ...

    Attributes
    ----------
    logger : logging.logger
        an already initialized logger instance

    """

    def __init__(self, logger=None):
        """
        Parameters
        ----------
        logger : logging.logger
            an already initialized logger instance
        """

        super().__init__()
        if logger is not None:
            self.log = logger
        else:
            self.log = _logging.create_logger("EntryDict", debug=True)

    def move(self, entry, old_path, new_path):
        """ Exchanges path of entry. It won't move an entry between inodes.

            However: The path indicates a change of parent.
        """
        self.log.debug("Move {0} from {1} to {2}".format(
            entry, old_path, new_path))
        for idx in range(len(self[old_path])):
            self.log.debug(idx)
            if self[old_path][idx] == entry:
                self.log.debug(entry)
                del self[old_path][idx]
                break
        self[new_path].append(entry)
        return self[new_path][-1]
