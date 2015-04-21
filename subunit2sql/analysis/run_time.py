#!/bin/env python2
# Copyright 2014 Hewlett-Packard Development Company, L.P.
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

from oslo.config import cfg
import pandas as pd

from subunit2sql.analysis import utils
from subunit2sql.db import api
from subunit2sql import shell

CONF = cfg.CONF

SHELL_OPTS = [
    cfg.StrOpt('test_id', positional=True, required=True,
               help='Test id to extract time series for'),
    cfg.StrOpt('title', short='t', help='Optional title to use for the graph '
                                        'output. If one is not specified, the '
                                        'full test_id will be used'),
    cfg.StrOpt('output', short='o', required=True,
               help='Output path to write image file to. The file extension '
                    'will determine the file format.'),
    cfg.StrOpt('start-date', short='d',
               help='Start date for the graph only data from after this date '
                    'will be used. Uses ISO8601 format: 1914-06-28'),
    cfg.StrOpt('stop-date', short='s',
               help='Stop date for the graph only data from before this date '
                    'will be used. Uses ISO8601 format: 1914-06-28'),
]


def cli_opts():
    for opt in SHELL_OPTS:
        CONF.register_cli_opt(opt)


def list_opts():
    opt_list = copy.deepcopy(SHELL_OPTS)
    return [('DEFAULT', opt_list)]


def generate_series(test_id):
    session = api.get_session()
    run_times = api.get_test_run_time_series(test_id, session)
    if not CONF.title:
        test = api.get_test_by_id(test_id, session)
    session.close()
    ts = pd.Series(run_times)
    ts = utils.filter_dates(ts)
    if not CONF.title:
        plot = ts.plot().set_title(test.test_id)
    else:
        plot = ts.plot().set_title(CONF.title)
    plot = pd.rolling_mean(ts, 50).plot()
    fig = plot.get_figure()
    plot.set_ylabel('Time (sec.)')
    fig.savefig(CONF.output)
    return ts


def main():
    cli_opts()
    shell.parse_args(sys.argv)
    generate_series(CONF.test_id)
    print('Graph saved at: %s' % CONF.output)

if __name__ == "__main__":
    sys.exit(main())
