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
import matplotlib.dates as dates
import matplotlib.pyplot as plt
from oslo_config import cfg
import pandas as pd

from subunit2sql.analysis import utils
from subunit2sql.db import api

CONF = cfg.CONF

matplotlib.style.use('ggplot')


def set_cli_opts(parser):
    parser.add_argument('test_id', nargs='?',
                        help='Test id to extract time series for. This '
                             'previously took a UUID from the tests.id '
                             'column, however this will no longer work. It '
                             'only works with a value from tests.test_id.')


def generate_series():
    session = api.get_session()
    test_id = api.get_id_from_test_id(CONF.command.test_id, session)
    if not test_id:
        print("The test_id %s was not found in the database" %
              CONF.command.test_id)
        exit(2)
    run_times = api.get_test_run_time_series(test_id, session)
    if not run_times:
        print("There was no data found in the database")
        exit(3)
    if not CONF.title:
        test = api.get_test_by_id(test_id, session)
    session.close()
    ts = pd.Series(run_times)
    ts = utils.filter_dates(ts)
    if ts.count() == 0:
        print("No data available. Check your query and try again.")
        exit(-1)
    mean = pd.rolling_mean(ts, 20)
    rolling_std = pd.rolling_std(ts, 20)
    plt.figure()
    if not CONF.title:
        plt.title(test.test_id)
    else:
        plt.title(CONF.title)
    plt.ylabel('Time (sec.)')

    # format x-axis with dates
    fig, ax = plt.subplots(1)
    fig.autofmt_xdate()
    xfmt = dates.DateFormatter("%b %d %Y")
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(xfmt)

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
