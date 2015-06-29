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

import matplotlib
import matplotlib.pyplot as plt
from oslo_config import cfg
import pandas as pd

from subunit2sql.analysis import utils
from subunit2sql.db import api

CONF = cfg.CONF

matplotlib.style.use('ggplot')


def set_cli_opts(parser):
    parser.add_argument('test_id', nargs='?',
                        help='Test id to extract time series for')


def generate_series():
    test_id = CONF.command.test_id
    session = api.get_session()
    run_times = api.get_test_run_time_series(test_id, session)
    if not CONF.title:
        test = api.get_test_by_id(test_id, session)
    session.close()
    ts = pd.Series(run_times)
    ts = utils.filter_dates(ts)
    mean = pd.rolling_mean(ts, 20)
    rolling_std = pd.rolling_std(ts, 20)
    plt.figure()
    if not CONF.title:
        plt.title(test.test_id)
    else:
        plt.title(CONF.title)
    plt.ylabel('Time (sec.)')
    plt.plot(ts.index, ts, 'k', label='Run Time')
    plt.plot(mean.index, mean, 'b', label='Avg. Run Time')
    upper_std_dev = mean + 2 * rolling_std
    lower_std_dev = mean - 2 * rolling_std
    # Set negative numbers to 0
    lower_std_dev[lower_std_dev < 0] = 0
    plt.fill_between(rolling_std.index, upper_std_dev,
                     lower_std_dev, color='b', alpha=0.2,
                     label='std dev')
    plt.legend()
    plt.savefig(CONF.output, dpi=900)
    return ts
