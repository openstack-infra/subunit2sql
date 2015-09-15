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

from oslo_config import cfg
import pandas as pd

from subunit2sql.analysis import utils
from subunit2sql.db import api

CONF = cfg.CONF


def set_cli_opts(parser):
    parser.add_argument('test_id', nargs='?',
                        help='Test id to extract time series for'),
    parser.add_argument('--success-graph', action='store_true',
                        help='Also graph successes'),
    parser.add_argument('--skip-graph', action='store_true',
                        help='Also graph skips')


def generate_series():
    test_id = CONF.command.test_id
    session = api.get_session()
    test_statuses = api.get_test_status_time_series(test_id, session)
    if not CONF.title:
        test = api.get_test_by_id(test_id, session)
    session.close()
    ts = pd.Series(test_statuses)
    ts = utils.filter_dates(ts)
    run_count = len(ts)
    if run_count == 0:
        print("Query returned no data.")
        exit(-1)
    failures = ts[ts.isin(['fail', 'unxsuccess'])]
    successes = ts[ts.isin(['success', 'xfail'])]
    skips = ts[ts.isin(['skip'])]
    fail_count = len(failures)
    success_count = len(successes)
    skip_count = len(skips)
    fail_group = failures.groupby(failures.index.date).agg(len)
    success_group = successes.groupby(successes.index.date).agg(len)
    skip_group = skips.groupby(skips.index.date).agg(len)
    if not CONF.title:
        plot = fail_group.plot().set_title(test.test_id)
    else:
        plot = fail_group.plot().set_title(CONF.title)
    if CONF.command.success_graph:
        if success_count:
            success_group.plot()
    if CONF.command.skip_graph:
        if skip_count:
            skip_group.plot()

    def percent(count, total):
        count = float(count)
        total = float(total)
        return (count / total) * 100.0

    print('Fail Percentage: %.4f%%' % percent(fail_count, run_count))
    print('Success Percentage: %.4f%%' % percent(success_count, run_count))
    print('Skip Percentage: %.4f%%' % percent(skip_count, run_count))
    fig = plot.get_figure()
    fig.savefig(CONF.output)
    return ts
