# -*- coding: utf-8 -*-

from enum import Enum


class Events(Enum):

    """
    Events is a enum for every event type that occures.

    """

    CREATE = 1
    READ = 2
    WRITE = 3
    RENAME = 4
    REMOVE = 5


class Operations(Enum):

    """
    All operations that can be listened to exist in this enumeration.

    """

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

    """
    The Listener will recieve ListenerObjetcts. This is the base class of these.

    ...

    Attributes
    ----------
    event : corefs.listener.objects.Events
        an event type
    operation : corefs.listener.objects.Operations
        an filesystem operation
    obj : corefs.listener.objects.ListenerObject
        a instance of a ListenerObject.

    """

    def __init__(self, event, operation, obj):
        """
        Parameters
        ----------
        event : corefs.listener.objects.Events
            an event type
        operation : corefs.listener.objects.Operations
            an filesystem operation
        obj : corefs.listener.objects.ListenerObject
            a instance of a ListenerObject.
        """

        self.event = event
        self.operation = operation
        self.obj = obj


class CreateObject(ListenerObject):

    """
    A CreateObject holds information, when a file or a directory is created.

    ...

    Attributes
    ----------
    event : corefs.listener.objects.Events
        an event type
    operation : corefs.listener.objects.Operations
        an filesystem operation
    obj : corefs.listener.objects.CreateObject
        a instance of a CreateObject.

    """

    def __init__(self, operation, obj):
        """
        Parameters
        ----------
        event : corefs.listener.objects.Events
            an event type
        operation : corefs.listener.objects.Operations
            an filesystem operation
        obj : corefs.listener.objects.CreateObject
            a instance of a CreateObject.
        """

        super().__init__(Events.CREATE, operation, obj)


class ReadObject(ListenerObject):

    """
    A ReadObject holds information, when a file or a directory is read.

    ...

    Attributes
    ----------
    event : corefs.listener.objects.Events
        an event type
    operation : corefs.listener.objects.Operations
        an filesystem operation
    obj : corefs.listener.objects.ReadObject
        a instance of a ReadObject.

    """

    def __init__(self, operation, obj, data):
        """
        Parameters
        ----------
        event : corefs.listener.objects.Events
            an event type
        operation : corefs.listener.objects.Operations
            an filesystem operation
        obj : corefs.listener.objects.ReadObject
            a instance of a ReadObject.
        """

        super().__init__(Events.READ, operation, obj)
        self.data = data


class WriteObject(ListenerObject):

    """
    A WriteObject holds information, when a file is written.

    ...

    Attributes
    ----------
    event : corefs.listener.objects.Events
        an event type
    operation : corefs.listener.objects.Operations
        an filesystem operation
    obj : corefs.listener.objects.WriteObject
        a instance of a WriteObject.

    """

    def __init__(self, operation, obj, buffer_length):
        """
        Parameters
        ----------
        event : corefs.listener.objects.Events
            an event type
        operation : corefs.listener.objects.Operations
            an filesystem operation
        obj : corefs.listener.objects.WriteObject
            a instance of a WriteObject.
        """

        super().__init__(Events.WRITE, operation, obj)
        self.buffer_length = buffer_length


class RenameObject(ListenerObject):

    """
    A RenameObject holds information, when a file or directory is renamed.

    ...

    Attributes
    ----------
    event : corefs.listener.objects.Events
        an event type
    operation : corefs.listener.objects.Operations
        an filesystem operation
    obj : corefs.listener.objects.RenameObject
        a instance of a RenameObject.

    """

    def __init__(self, operation, obj, new_dir, new_name):
        """
        Parameters
        ----------
        event : corefs.listener.objects.Events
            an event type
        operation : corefs.listener.objects.Operations
            an filesystem operation
        obj : corefs.listener.objects.RenameObject
            a instance of a RenameObject.
        """

        super().__init__(Events.RENAME, operation, obj)
        self.new_dir = new_dir
        self.new_name = new_name


class RemoveObject(ListenerObject):

    """
    A RemoveObject holds information, when a file or directory is removed.

    ...

    Attributes
    ----------
    event : corefs.listener.objects.Events
        an event type
    operation : corefs.listener.objects.Operations
        an filesystem operation
    obj : corefs.listener.objects.RemoveObject
        a instance of a RemoveObject.

    """

    def __init__(self, operation, obj):
        """
        Parameters
        ----------
        event : corefs.listener.objects.Events
            an event type
        operation : corefs.listener.objects.Operations
            an filesystem operation
        obj : corefs.listener.objects.RemoveObject
            a instance of a RemoveObject.
        """

        super().__init__(Events.REMOVE, operation, obj)
