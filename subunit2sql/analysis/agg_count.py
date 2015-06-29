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

from subunit2sql.db import api

CONF = cfg.CONF


def set_cli_opts(parser):
    parser.add_argument('test_ids', nargs='*',
                        help='Test ids to graph counts for, if none are '
                             'specified all tests will be used')
    parser.add_argument('--no-success-graph', action='store_true',
                        help='Do not graph successes'),
    parser.add_argument('--skip-graph', action='store_true',
                        help='Also graph skips')


def generate_series():
    session = api.get_session()
    test_dict = {}
    if not CONF.start_date and not CONF.stop_date:
        tests = api.get_all_tests(session)
        for test in tests:
            if CONF.command.test_ids:
                if test.test_id in CONF.command.test_ids:
                    test_dict[test.test_id] = {
                        'success': int(test.success),
                        'failure': int(test.failure),
                    }
            else:
                test_dict[test.test_id] = {
                    'success': int(test.success),
                    'failure': int(test.failure),
                }
    else:
        if CONF.command.test_ids:
            ids = [api.get_id_from_test_id(x) for x in CONF.command.test_ids]
        else:
            ids = api.get_ids_for_all_tests(session)
        for test in ids:
            test_dict[test] = api.get_test_counts_in_date_range(
                test, CONF.start_date, CONF.stop_date, session)
    if CONF.command.no_success_graph:
        for test in test_dict:
            test_dict[test].pop('success')
    if CONF.command.skip_graph:
        for test in test_dict:
            if not test_dict[test].get('skips'):
                test_id = api.get_id_from_test_id(test)
                test_dict[test]['skips'] = api.get_skip_counts(test_id)
    session.close()
    if not CONF.title:
        title = "Test status counts"
    else:
        title = CONF.title
    df = pd.DataFrame.from_dict(test_dict, orient='index')
    plot = df.plot(kind='barh', stacked=True).set_title(title)
    fig = plot.get_figure()
    fig.savefig(CONF.output)
