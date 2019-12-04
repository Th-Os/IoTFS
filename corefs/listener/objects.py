# -*- coding: utf-8 -*-

from enum import Enum


class Events(Enum):
    CREATE = 1
    READ = 2
    WRITE = 3
    RENAME = 4
    REMOVE = 5


class Operations(Enum):

    CREATE_FILE = 1
    CREATE_DIR = 2

    READ_FILE = 3
    READ_DIR = 4

    WRITE_FILE = 5

    RENAME_FILE = 6
    RENAME_DIR = 7

    REMOVE_FILE = 8
    REMOVE_DIR = 9


class ListenerObject():

    def __init__(self, event, operation, obj):
        self.event = event
        self.operation = operation
        self.obj = obj


class CreateObject(ListenerObject):

    def __init__(self, operation, obj):
        super().__init__(Events.CREATE, operation, obj)


class ReadObject(ListenerObject):

    def __init__(self, operation, obj, data):
        super().__init__(Events.READ, operation, obj)
        self.data = data


class WriteObject(ListenerObject):

    def __init__(self, operation, obj, buffer_length):
        super().__init__(Events.WRITE, operation, obj)
        self.buffer_length = buffer_length


class RenameObject(ListenerObject):

    def __init__(self, operation, obj, new_dir, new_name):
        super().__init__(Events.RENAME, operation, obj)
        self.new_dir = new_dir
        self.new_name = new_name


class RemoveObject(ListenerObject):

    def __init__(self, operation, obj):
        super().__init__(Events.REMOVE, operation, obj)
