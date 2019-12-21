# -*- coding: utf-8 -*-

from enum import Enum


class Encodings(Enum):
    """ Differs between BYTE and UTF_8 encoding.

    """

    BYTE_ENCODING = 0  # filesystem encoding
    UTF_8_ENCODING = 1


class Types(Enum):
    """ Differs between FILE, DIR, SWAP types.

    """

    FILE = 0
    DIR = 1
    SWAP = 2


class LinkTypes(Enum):
    """ Differs between HARDLINK and SYMBOLIC links.

    """

    HARDLINK = 0
    SYMBOLIC = 1


# Root inode is 1 on every start up.
ROOT_INODE = 1

# Standard mode is rwx-rw-rw
STANDARD_MODE = 0o766

# Special link mode.
LINK_MODE = 41471
