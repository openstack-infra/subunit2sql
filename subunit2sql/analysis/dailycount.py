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
import matplotlib.dates as dates
import matplotlib.pyplot as plt
from oslo_config import cfg
import pandas as pd

from subunit2sql.db import api

CONF = cfg.CONF

matplotlib.style.use('ggplot')


def set_cli_opts(parser):
    pass


def generate_series():
    if CONF.start_date:
        start_date = datetime.datetime.strptime(CONF.start_date, '%Y-%m-%d')
    else:
        start_date = None
    if CONF.stop_date:
        stop_date = datetime.datetime.strptime(CONF.stop_date, '%Y-%m-%d')
    else:
        stop_date = None
    session = api.get_session()
    test_starts = api.get_test_run_series(start_date=start_date,
                                          stop_date=stop_date,
                                          session=session)
    session.close()
    ts = pd.Series(test_starts)
    daily_count = ts.resample('D').sum()
    mean = daily_count.rolling(window=10, center=False).mean()
    rolling_std = daily_count.rolling(window=10, center=False).std()
    plt.figure()
    title = CONF.title or 'Number of Tests run Daily'
    plt.title(title)
    plt.ylabel('Number of tests')
    fig, ax = plt.subplots(1)
    fig.autofmt_xdate()
    plt.title(title)
    plt.ylabel('Number of tests')
    xfmt = dates.DateFormatter("%b %d %Y")
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(xfmt)

    plt.plot(daily_count.index[10:], daily_count[10:], 'k',
             label='Daily Test Count')
    plt.plot(mean.index[10:], mean[10:], 'b', label='Avg. Daily Test Count')
    upper_std_dev = mean + 2 * rolling_std
    lower_std_dev = mean - 2 * rolling_std
    # Set negative numbers to 0
    lower_std_dev[lower_std_dev < 0] = 0
    plt.fill_between(rolling_std.index[10:], lower_std_dev[10:],
                     upper_std_dev[10:],
                     color='b', alpha=0.2, label='Std Dev')
    plt.legend()
    plt.savefig(CONF.output, dpi=900)
