import argparse
import logging
import os
import sys

import gevent
import gevent.queue
from gevent.pywsgi import WSGIServer
from gevent import monkey

from castervoice import watcher
from castervoice.core import Controller
from castervoice.web import app as web_app


VERBOSITY_LOG_LEVEL = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG
}

DEFAULT_CONFIG_DIR = "config"


def default_plugin_state_dir(config_dir):
    return f"{config_dir}/plugins.state"


def get_parser():
    parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--config-dir', '-c', default=DEFAULT_CONFIG_DIR,
                        help='Configuration directory.')

    parser.add_argument('--develop', '-d', action='store_true',
                        help='Development mode. In development mode plugins '
                             'are reloaded if any of the plugin\'s files are '
                             'altered.')

    parser.add_argument('--plugin-state-dir',
                        help='Plugin state directory. By default this is a '
                             'subdirectory within `config_dir`.')

    parser.add_argument('--verbose', '-v', action='count',
                        default=0, help=f'Verbose logging (max level:\
                                          {len(VERBOSITY_LOG_LEVEL)}).')

    return parser


def verify_parsed_args(args):
    max_verbose = len(VERBOSITY_LOG_LEVEL) - 1
    if args.verbose > max_verbose:
        raise ValueError("Maximum verbosity level is: -" + 'v'*max_verbose)

    return args


def get_args():
    args = get_parser().parse_args()

    # If the user did not specify plugin_state_dir we
    # set it to the default
    if not args.plugin_state_dir:
        args.plugin_state_dir = default_plugin_state_dir(args.config_dir)

    try:
        return verify_parsed_args(args)
    except ValueError as error:
        print("Failed parsing arguments: ",
              error)
        sys.exit(1)


def main():
    """TODO: Docstring for main.

    :argv: TODO
    :returns: TODO

    """

    args = get_args()

    logging.basicConfig(level=VERBOSITY_LOG_LEVEL[args.verbose])

    try:
        controller = Controller(config_dir=os.path.abspath(args.config_dir),
                                plugin_state_dir=args.plugin_state_dir,
                                dev_mode=args.develop)
    # pylint: disable=broad-except
    except Exception as error:
        logging.getLogger().error("Controller failed with: %s", error)
        if args.verbose >= 2:
            logging.getLogger().exception(error)
        sys.exit(1)

    gevent.spawn(controller.listen, watcher.on_begin,
                 watcher.on_recognition, watcher.on_failure)

    if args.verbose > 0:
        gevent.spawn(watcher.log)

    monkey.patch_all(subprocess=False, ssl=False)
    http_server = WSGIServer(('', 23423), web_app)
    http_server.serve_forever()


if __name__ == "__main__":
    main()
