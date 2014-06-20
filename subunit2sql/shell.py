# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

from oslo.config import cfg
from oslo.db import options

from subunit2sql.db import api
from subunit2sql import exceptions
from subunit2sql import read_subunit as subunit

shell_opts = [
    cfg.StrOpt('state_path', default='$pybasedir',
               help='Top level dir for maintaining subunit2sql state'),
    cfg.MultiStrOpt('subunit_files', positional=True),
    cfg.DictOpt('run_meta', short='r', default=None,
                help='Dict of metadata about the run(s)'),
]

CONF = cfg.CONF
for opt in shell_opts:
    CONF.register_cli_opt(opt)


def state_path_def(*args):
    """Return an uninterpolated path relative to $state_path."""
    return os.path.join('$state_path', *args)


_DEFAULT_SQL_CONNECTION = 'sqlite:///' + state_path_def('subunit2sql.sqlite')


def parse_args(argv, default_config_files=None):
    options.set_defaults(CONF, connection=_DEFAULT_SQL_CONNECTION,
                         sqlite_db='subunit2sql.sqlite')
    cfg.CONF(argv[1:], project='subunit2sql',
             default_config_files=default_config_files)


def running_avg(test, values, result):
    count = test.success
    avg_prev = test.run_time
    curr_runtime = float(subunit.get_duration(result['start_time'],
                                              result['end_time']).strip('s'))
    if isinstance(avg_prev, float):
        # Using a smoothed moving avg to limit the affect of a single outlier
        new_avg = ((count * avg_prev) + curr_runtime) / (count + 1)
        values['run_time'] = new_avg
    else:
        values['run_time'] = curr_runtime
    return values


def increment_counts(run, test, results, session=None):
    test_values = {'run_count': test.run_count + 1}
    run_values = {}
    status = results.get('status')
    run = api.get_run_by_id(run.id, session)
    if status == 'success':
        test_values['success'] = test.success + 1
        run_values['passes'] = run.passes + 1
    elif status == 'fail':
        test_values['failure'] = test.failure + 1
        run_values['fails'] = run.fails + 1
    elif status == 'skip':
        test_values = {}
        run_values['skips'] = run.skips + 1
    else:
        msg = "Unknown test status %s" % status
        raise exceptions.UnknownStatus(msg)
    test_values = running_avg(test, test_values, results)
    if test_values:
        api.update_test(test_values, test.id)
    api.update_run(run_values, run.id)


def process_results(results):
    session = api.get_session()
    db_run = api.create_run(run_time=results.pop('run_time'))
    if CONF.run_meta:
        api.add_run_metadata(CONF.run_meta, db_run.id, session)
    for test in results:
        db_test = api.get_test_by_test_id(test, session)
        if not db_test:
            db_test = api.create_test(test)
        increment_counts(db_run, db_test, results[test], session)
        api.create_test_run(db_test.id, db_run.id, results[test]['status'],
                            results[test]['start_time'],
                            results[test]['end_time'])


def main():
    parse_args(sys.argv)
    if CONF.subunit_files:
        streams = [subunit.ReadSubunit(open(s, 'r')) for s in
                   CONF.subunit_files]
    else:
        streams = [subunit.ReadSubunit(sys.stdin)]
    for stream in streams:
        process_results(stream.get_results())


if __name__ == "__main__":
    sys.exit(main())
