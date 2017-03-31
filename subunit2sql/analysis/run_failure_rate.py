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

import datetime

import matplotlib
import matplotlib.pyplot as plt
from oslo_config import cfg
from subunit2sql.db import api

CONF = cfg.CONF
matplotlib.style.use('ggplot')


def set_cli_opts(parser):
    parser.add_argument('metadata_key',
                        help="The run_metadata key to group the runs by")
    parser.add_argument('--filter_list', '-f',
                        help='A comma seperated list of values to use')


def generate_series():
    session = api.get_session()
    if CONF.command.filter_list:
        filter_list = CONF.command.filter_list.split(',')
    else:
        filter_list = []
    if CONF.start_date:
        start_date = datetime.datetime.strptime(CONF.start_date, '%Y-%m-%d')
    else:
        start_date = None
    if CONF.stop_date:
        stop_date = datetime.datetime.strptime(CONF.stop_date, '%Y-%m-%d')
    else:
        stop_date = None

    run_status = api.get_runs_by_status_grouped_by_run_metadata(
        CONF.command.metadata_key, start_date=start_date,
        stop_date=stop_date, session=session)

    perc_data = {}
    for key in run_status:
        if key not in filter_list:
            continue
        if run_status[key].get('pass'):
            pass_num = float(run_status[key]['pass'])
        else:
            pass_num = 0.0
        if run_status[key].get('fail'):
            fail_num = float(run_status[key]['fail'])
        else:
            fail_num = 0.0
        fail_rate = float(fail_num / (pass_num + fail_num) * 100)
        if fail_rate > 0.0:
            perc_data[key] = fail_rate
    if not CONF.title:
        title = "Run aggregate failure rate grouped by metadata"
    else:
        title = CONF.title
    plt.figure()
    plt.title(title)
    plt.barh(range(len(perc_data)), perc_data.values(), align='center')
    locs, labels = plt.yticks(range(len(perc_data)), list(perc_data.keys()))
    plt.xlabel('Failure Percentage')
    plt.tight_layout()
    plt.savefig(CONF.output, dpi=900)
