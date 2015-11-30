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

import copy
import datetime
import sys

from oslo_config import cfg
import subunit
from subunit import iso8601

from subunit2sql.db import api
from subunit2sql import shell

STATUS_CODES = frozenset([
    'exists',
    'fail',
    'skip',
    'success',
    'uxsuccess',
    'xfail',
])

CONF = cfg.CONF

SHELL_OPTS = [
    cfg.StrOpt('run_id', positional=True,
               help='Run id to use for creating a subunit stream'),
    cfg.StrOpt('out_path', short='o', default=None,
               help='Path to write the subunit stream output, if none '
                    'is specified STDOUT will be used'),
    cfg.BoolOpt('average', short='a', default=False,
                help='Generate a subunit stream for all the rows in the tests '
                     'table using the average run_time for the duration.')
]


def cli_opts():
    for opt in SHELL_OPTS:
        cfg.CONF.register_cli_opt(opt)


def convert_datetime(timestamp):
    tz_timestamp = timestamp.replace(tzinfo=iso8601.UTC)
    return tz_timestamp


def write_test(output, start_time, stop_time, status, test_id, metadatas):
    write_status = output.status
    kwargs = {}
    if 'tags' in metadatas:
        tags = metadatas['tags']
        kwargs['test_tags'] = tags.split(',')
    if 'attrs' in metadatas:
        test_id = test_id + '[' + metadatas['attrs'] + ']'
    start_time = convert_datetime(start_time)
    kwargs['timestamp'] = start_time
    kwargs['test_id'] = test_id
    write_status(**kwargs)
    if status in STATUS_CODES:
        kwargs['test_status'] = status
        kwargs['timestamp'] = convert_datetime(stop_time)
    write_status(**kwargs)


def sql2subunit(run_id, output=sys.stdout):
    session = api.get_session()
    test_runs = api.get_tests_run_dicts_from_run_id(run_id, session)
    session.close()
    output = subunit.v2.StreamResultToBytes(output)
    output.startTestRun()
    for test_id in test_runs:
        test = test_runs[test_id]
        write_test(output, test['start_time'], test['stop_time'],
                   test['status'], test_id, test['metadata'])
    output.stopTestRun()


def avg_sql2subunit(output=sys.stdout):
    session = api.get_session()
    tests = api.get_all_tests(session=session)
    session.close()
    output = subunit.v2.StreamResultToBytes(output)
    output.startTestRun()
    for test in tests:
        if not test.run_time:
            continue
        start_time = datetime.datetime.now()
        stop_time = start_time + datetime.timedelta(0, test.run_time)
        write_test(output, start_time, stop_time, 'success', test.test_id, [])
    output.stopTestRun()


def list_opts():
    opt_list = copy.deepcopy(SHELL_OPTS)
    return [('DEFAULT', opt_list)]


def main():
    cli_opts()
    shell.parse_args(sys.argv)
    if not CONF.run_id and not CONF.average:
        print('You must specify either a run_id or generate an average run'
              ' stream')
        return 1
    if CONF.run_id and CONF.average:
        print('You can either generate a stream for a run_id or an average run'
              ' stream, but not both.')
        return 1
    if CONF.out_path:
        fd = open(CONF.out_path, 'w')
    else:
        fd = sys.stdout
    if not CONF.average:
        sql2subunit(CONF.run_id, fd)
    else:
        avg_sql2subunit(fd)
    if CONF.out_path:
        fd.close()

if __name__ == "__main__":
    sys.exit(main())
