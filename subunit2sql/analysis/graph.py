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
import stevedore

import subunit2sql.analysis.agg_count
import subunit2sql.analysis.dailycount
import subunit2sql.analysis.failures
import subunit2sql.analysis.run_failure_rate
import subunit2sql.analysis.run_time
import subunit2sql.analysis.run_time_meta
from subunit2sql import shell

CONF = cfg.CONF
CONF.import_opt('verbose', 'subunit2sql.db.api')

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


def get_plugin_list():
    plugin_list = stevedore.ExtensionManager(
        'subunit2sql.graph.plugin',
        invoke_on_load=True,
        propagate_map_exceptions=True)
    return plugin_list


def add_command_parsers(subparsers):
    graph_commands = {}
    # Put commands from in-tree commands on init list
    for command in ['failures', 'run_time', 'agg_count', 'dailycount',
                    'run_failure_rate', 'run_time_meta']:
        graph_commands[command] = getattr(subunit2sql.analysis, command)

    # Load any installed out of tree commands on the init list
    for plugin in get_plugin_list():
        graph_commands[plugin.name] = plugin.plugin

    # Init all commands from graph_commands
    for name in graph_commands:
        parser = subparsers.add_parser(name)
        graph_commands[name].set_cli_opts(parser)
        parser.set_defaults(
            func=graph_commands[name].generate_series)

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
