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

from oslo.config import cfg
import pandas as pd

from subunit2sql.analysis import utils
from subunit2sql.db import api

CONF = cfg.CONF


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
    if not CONF.title:
        plot = ts.plot().set_title(test.test_id)
    else:
        plot = ts.plot().set_title(CONF.title)
    plot = pd.rolling_mean(ts, 50).plot()
    fig = plot.get_figure()
    plot.set_ylabel('Time (sec.)')
    fig.savefig(CONF.output)
    return ts
