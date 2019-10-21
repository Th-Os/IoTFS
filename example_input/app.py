from argparse import ArgumentParser


from corefs.core import CoreFS
from corefs.filesystem.standard_fs import StandardFileSystem

from mqtt.mqtt_client import MQTT_Client
from mqtt.mqtt_adapter import MQTT_Adapter

from fs.fs_client import FS_Client
from fs.fs_adapter import FS_Adapter


def parse_args():
    '''Parse command line'''

    parser = ArgumentParser()

    parser.add_argument('mountpoint', type=str,
                        help='Where to mount the file system')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debugging output')
    return parser.parse_args()


def main():
    options = parse_args()

    fs = StandardFileSystem(options.mountpoint, debug=options.debug)

    mqtt = MQTT_Client(options.debug)
    fs_client = FS_Client(options.debug)
    adapters = [MQTT_Adapter(mqtt), FS_Adapter(fs_client)]

    CoreFS(fs, adapters=adapters, debug=options.debug)


if __name__ == "__main__":
    main()
