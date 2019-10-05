from argparse import ArgumentParser
import concurrent.futures
import os

from filesystem.fs import FileSystemStarter
from filesystem.standard_fs import StandardFileSystem
from adapter.mqtt.mqtt_adapter import MQTT_Adapter
from adapter.mqtt.mqtt_client import MQTT_Client
import utils


def parse_args():
    '''Parse command line'''

    parser = ArgumentParser()

    parser.add_argument('mountpoint', type=str,
                        help='Where to mount the file system')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debugging output')
    parser.add_argument('--debug-fuse', action='store_true', default=False,
                        help='Enable FUSE debugging output')
    return parser.parse_args()


def main():
    options = parse_args()
    log = utils.init_logging(debug=options.debug, with_file=False)
    log.info("Starting application.")
    os.environ["MOUNT_POINT"] = os.path.abspath(options.mountpoint)
    fs = StandardFileSystem(options.mountpoint, options.debug)
    mqtt = MQTT_Client(options.mountpoint, options.debug)

    try:
        if not os.path.isdir(options.mountpoint):
            os.mkdir(options.mountpoint)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(FileSystemStarter(fs).start)
            executor.submit(MQTT_Adapter(mqtt).start)

    except (BaseException, Exception) as e:
        log.error(e)


if __name__ == "__main__":
    main()
