from argparse import ArgumentParser
import trio
# import concurrent.futures

import fs
import mqtt
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


async def start(options):
    log = utils.init_logging(debug=options.debug, with_file=False)
    log.info("Starting asynchronously.")
    async with trio.open_nursery() as nursery:
        log.debug("parent: spawning mqtt module")
        nursery.start_soon(mqtt.start, options.mountpoint, options.debug)

        log.debug("parent: spawning fs module")
        nursery.start_soon(fs.start, options.mountpoint,
                           options.debug, options.debug_fuse)

        log.debug("parent: waiting for children to finish...")
        # -- we exit the nursery block here --
    log.info("all done!")


def async_main():
    options = parse_args()
    trio.run(start, options)


def main():
    options = parse_args()
    log = utils.init_logging(debug=options.debug, with_file=False)
    log.info("Starting application.")
    fs.start(options.mountpoint, options.debug, options.debug_fuse)

    '''
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(fs.start, options.mountpoint,
                            options.debug, options.debug_fuse)
            executor.submit(mqtt.start, options.mountpoint, options.debug)

    except (BaseException, Exception) as e:
        log.error(e)
    '''


if __name__ == "__main__":
    main()
