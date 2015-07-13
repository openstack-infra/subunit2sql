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

import matplotlib
import matplotlib.pyplot as plt
from oslo_config import cfg
import pandas as pd

from subunit2sql.analysis import utils
from subunit2sql.db import api

CONF = cfg.CONF

matplotlib.style.use('ggplot')


def set_cli_opts(parser):
    pass


def generate_series():
    session = api.get_session()
    test_starts = api.get_test_run_series(session)
    session.close()
    ts = pd.Series(test_starts).resample('D', how='sum')
    daily_count = utils.filter_dates(ts)
    mean = pd.rolling_mean(daily_count, 10)
    rolling_std = pd.rolling_std(daily_count, 10)
    plt.figure()
    title = CONF.title or 'Number of tests run'
    plt.title(title)
    plt.ylabel('Number of tests')
    plt.plot(daily_count.index, daily_count, 'k', label='Daily Test Count')
    plt.plot(mean.index, mean, 'b', label='Avg. Daily Test Count')
    upper_std_dev = mean + 2 * rolling_std
    lower_std_dev = mean - 2 * rolling_std
    # Set negative numbers to 0
    lower_std_dev[lower_std_dev < 0] = 0
    plt.fill_between(rolling_std.index, lower_std_dev, upper_std_dev,
                     color='b', alpha=0.2, label='std dev')
    plt.legend()
    plt.savefig(CONF.output)
