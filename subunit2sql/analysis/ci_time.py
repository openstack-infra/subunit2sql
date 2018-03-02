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

import operator

from dateutil import parser as date_parser
import matplotlib.pyplot as plt
import numpy
from oslo_config import cfg

from subunit2sql.db import api

CONF = cfg.CONF


def set_cli_opts(parser):
    parser.add_argument('key', nargs='?',
                        help='The run metadata key to aggregate the run times'
                             ' on.')
    parser.add_argument('--num', default=10, type=int,
                        help='The number of results to show. If 0 is set all '
                             'results will be shown')


def generate_series():
    session = api.get_session()
    start_date = None
    stop_date = None
    if CONF.start_date:
        start_date = date_parser.parse(CONF.start_date)
    if CONF.stop_date:
        stop_date = date_parser.parse(CONF.stop_date)
    ci_time = {}
    ci_time_temp = {}
    project_run_times = api.get_run_times_grouped_by_run_metadata_key(
        CONF.command.key, start_date=start_date, stop_date=stop_date,
        session=session)
    for project in project_run_times:
        ci_time_temp[project] = numpy.sum(project_run_times[project])
    sorted_times = sorted(ci_time_temp.items(), key=operator.itemgetter(1),
                          reverse=True)
    if CONF.command.num:
        sorted_times = sorted_times[:CONF.command.num]
    for project, time in sorted_times:
        ci_time[project] = time

    title = CONF.title or 'Aggregate Run Time grouped by %s' % CONF.command.key
    session.close()
    plt.bar(range(len(ci_time)), ci_time.values(), align='center', width=.1)
    plt.xticks(range(len(ci_time)), ci_time.keys(), rotation=90, fontsize=8)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(CONF.output, dpi=900)
