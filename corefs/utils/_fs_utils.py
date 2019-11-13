from enum import Enum


class Encodings(Enum):
    BYTE_ENCODING = 0  # filesystem encoding
    UTF_8_ENCODING = 1


class Types(Enum):
    FILE = 0
    DIR = 1
    SWAP = 2


class LinkTypes(Enum):
    HARDLINK = 0
    SYMBOLIC = 1


ROOT_INODE = 1
STANDARD_MODE = 0o766
