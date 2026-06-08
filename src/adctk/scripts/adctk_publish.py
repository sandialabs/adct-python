# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#

import argparse
import json

from adctk.http_publisher import HttpPublisher
from adctk.builder import Builder
import adctk.factory

from adctk.log import logger, setup_file_handler, setup_stream_handler


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("app_name", type=str,
                        help="Name of application (posts to collection of this name)")
    parser.add_argument("--app-data", dest="app_data", type=str, default=None,
                        help="Path to app data file containing json")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=False,
                        help="don't actually post")
    parser.add_argument("--logger-filepath", dest="logger_filepath", default="", type=str,
                        help="Directory pointing to path where log file will be written " + \
                              "only directory path is accepted at this time")
    parser.add_argument("--logger-stream", dest="logger_stream", action="store_true", default=False,
                        help="Enable stream output to stdout")
    return parser.parse_args()


def setup_builder(app_name):
    return Builder.BasicBuilder(app_name)


def setup_publisher():
    return HttpPublisher()


def get_data_section_from_file(filepath) -> Builder:
    data = None
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print("The file was not found.")
    except json.JSONDecodeError:
        print("Failed to decode JSON. Check if the file is correctly formatted.")
    b = adctk.factory.Factory.get_builder()
    b.add_json_string(json.dumps(data, skipkeys=True))
    # done-cbb: maybe iterate the keys in data and add them so that data is typed in json result.
    # but if user wanted that, they wouldn't be calling us with a json blob.
    return b

def main() -> int:
    args = get_args()

    if args.logger_stream:
        setup_stream_handler()

    if args.logger_filepath:
        setup_file_handler(args.logger_filepath)

    builder = setup_builder(args.app_name)

    if args.app_data:
        section = get_data_section_from_file(args.app_data)
        builder.add_section(section)

    if args.dry_run:
        logger.info("Exiting because dry_run was supplied")
        return 0

    publisher = setup_publisher()
    ret = publisher.publish(builder)
    print(ret)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
