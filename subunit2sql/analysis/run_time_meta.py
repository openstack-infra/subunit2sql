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
import pandas as pd

from subunit2sql.db import api

CONF = cfg.CONF
matplotlib.style.use('ggplot')


def set_cli_opts(parser):
    parser.add_argument('metadata_key',
                        help="The run_metadata key to group the runs by")


def generate_series():
    session = api.get_session()
    if CONF.start_date:
        start_date = datetime.datetime.strptime(CONF.start_date, '%Y-%m-%d')
    else:
        start_date = None
    if CONF.stop_date:
        stop_date = datetime.datetime.strptime(CONF.stop_date, '%Y-%m-%d')
    else:
        stop_date = None
    run_times = api.get_run_times_grouped_by_run_metadata_key(
        CONF.command.metadata_key, start_date=start_date,
        stop_date=stop_date, session=session)
    df = pd.DataFrame(dict(
        [(k, pd.Series(v)) for k, v in run_times.iteritems()]))
    if not CONF.title:
        title = "Run aggregate run time grouped by metadata"
    else:
        title = CONF.title
    # NOTE(mtreinish): Decrease label font size for the worst case where we
    # have tons of groups
    matplotlib.rcParams['xtick.labelsize'] = '3'
    plt.figure()
    plt.title(title)
    df.plot(kind='box', rot=90)
    plt.ylabel('Time (sec.)')
    plt.tight_layout()
    plt.savefig(CONF.output, dpi=900)
