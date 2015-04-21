#!/bin/env python2
# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy
import sys

from oslo_config import cfg

import subunit2sql.analysis.run_time
from subunit2sql import shell

CONF = cfg.CONF

SHELL_OPTS = [
    cfg.StrOpt('title', short='t', help='Optional title to use for the graph '
                                        'output. If one is not specified, the '
                                        'full test_id will be used'),
    cfg.StrOpt('output', short='o', required=True,
               help='Output path to write image file to. The file extension '
                    'will determine the file format.'),
    cfg.StrOpt('start-date', short='d',
               help='Start date for the graph only data from after this date '
                    'will be used. Uses ISO 8601 format: 1914-06-28'),
    cfg.StrOpt('stop-date', short='s',
               help='Stop date for the graph only data from before this date '
                    'will be used. Uses ISO 8601 format: 1914-06-28'),
]


def add_command_parsers(subparsers):
    for name in ['run_time']:
        parser = subparsers.add_parser(name)
        getattr(subunit2sql.analysis, name).set_cli_opts(parser)
        parser.set_defaults(
            func=getattr(subunit2sql.analysis, name).generate_series)

command_opt = cfg.SubCommandOpt('command', title='graph',
                                help='Available graphs',
                                handler=add_command_parsers)


def cli_opts():
    for opt in SHELL_OPTS:
        CONF.register_cli_opt(opt)
    CONF.register_cli_opt(command_opt)


def list_opts():
    opt_list = copy.deepcopy(SHELL_OPTS)
    return [('DEFAULT', opt_list)]


def main():
    cli_opts()
    shell.parse_args(sys.argv)
    CONF.command.func()
    print('Graph saved at: %s' % CONF.output)


if __name__ == "__main__":
    sys.exit(main())
