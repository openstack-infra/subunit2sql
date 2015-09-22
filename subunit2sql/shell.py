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

import copy
import sys

from oslo_config import cfg
from oslo_db import options
from pbr import version

from subunit2sql.db import api
from subunit2sql import exceptions
from subunit2sql import read_subunit as subunit

CONF = cfg.CONF
CONF.import_opt('verbose', 'subunit2sql.db.api')

SHELL_OPTS = [
    cfg.MultiStrOpt('subunit_files', positional=True,
                    help='list of subunit files to put into the database'),
    cfg.DictOpt('run_meta', short='r', default=None,
                help='Dict of metadata about the run(s)'),
    cfg.StrOpt('artifacts', short='a', default=None,
               help='Location of run artifacts'),
    cfg.BoolOpt('store_attachments', short='s', default=False,
                help='Store attachments from subunit streams in the DB'),
    cfg.StrOpt('run_id', short='i', default=None,
               help='Run id to use for the specified subunit stream, can only'
                    ' be used if a single stream is provided'),
    cfg.StrOpt('attr_regex', default='\[(.*)\]',
               help='The regex to use to extract the comma separated list of '
                    'test attributes from the test_id'),
]

_version_ = version.VersionInfo('subunit2sql').version_string()


def cli_opts():
    for opt in SHELL_OPTS:
        CONF.register_cli_opt(opt)


def list_opts():
    """Return a list of oslo.config options available.

    The purpose of this is to allow tools like the Oslo sample config file
    generator to discover the options exposed to users.
    """
    return [('DEFAULT', copy.deepcopy(SHELL_OPTS))]


def parse_args(argv, default_config_files=None):
    cfg.CONF.register_cli_opts(options.database_opts, group='database')
    cfg.CONF(argv[1:], project='subunit2sql', version=_version_,
             default_config_files=default_config_files)


def running_avg(test, values, result):
    count = test.success
    avg_prev = test.run_time
    curr_runtime = subunit.get_duration(result['start_time'],
                                        result['end_time'])
    if isinstance(avg_prev, float):
        # Using a smoothed moving avg to limit the affect of a single outlier
        new_avg = ((count * avg_prev) + curr_runtime) / (count + 1)
        values['run_time'] = new_avg
    else:
        values['run_time'] = curr_runtime
    return values


def increment_counts(test, results):
    test_values = {'run_count': test.run_count + 1}
    status = results.get('status')
    if status == 'success':
        test_values['success'] = test.success + 1
        test_values = running_avg(test, test_values, results)
    elif status == 'fail':
        test_values['failure'] = test.failure + 1
    elif status == 'skip':
        test_values = {}
    else:
        msg = "Unknown test status %s" % status
        raise exceptions.UnknownStatus(msg)
    return test_values


def get_run_totals(results):
    success = len([x for x in results if results[x]['status'] == 'success'])
    fails = len([x for x in results if results[x]['status'] == 'fail'])
    skips = len([x for x in results if results[x]['status'] == 'skip'])
    totals = {
        'success': success,
        'fails': fails,
        'skips': skips,
    }
    return totals


def process_results(results):
    session = api.get_session()
    run_time = results.pop('run_time')
    totals = get_run_totals(results)
    db_run = api.create_run(totals['skips'], totals['fails'],
                            totals['success'], run_time, CONF.artifacts,
                            id=CONF.run_id, session=session)
    if CONF.run_meta:
        api.add_run_metadata(CONF.run_meta, db_run.id, session)
    for test in results:
        db_test = api.get_test_by_test_id(test, session)
        if not db_test:
            if results[test]['status'] == 'success':
                success = 1
                fails = 0
            elif results[test]['status'] == 'fail':
                fails = 1
                success = 0
            else:
                fails = 0
                success = 0
            run_time = subunit.get_duration(results[test]['start_time'],
                                            results[test]['end_time'])
            db_test = api.create_test(test, (success + fails), success,
                                      fails, run_time,
                                      session)
        else:
            test_values = increment_counts(db_test, results[test])
            # If skipped nothing to update
            if test_values:
                api.update_test(test_values, db_test.id, session)
        test_run = api.create_test_run(db_test.id, db_run.id,
                                       results[test]['status'],
                                       results[test]['start_time'],
                                       results[test]['end_time'],
                                       session)
        if results[test]['metadata']:
            api.add_test_run_metadata(results[test]['metadata'], test_run.id,
                                      session)
        if results[test]['attachments']:
            api.add_test_run_attachments(results[test]['attachment'],
                                         test_run.id, session)
    session.close()


def main():
    cli_opts()
    parse_args(sys.argv)
    if CONF.subunit_files:
        if len(CONF.subunit_files) > 1 and CONF.run_id:
            print("You can not specify a run id for adding more than 1 stream")
            return 3
        streams = [subunit.ReadSubunit(open(s, 'r'),
                                       attachments=CONF.store_attachments,
                                       attr_regex=CONF.attr_regex)
                   for s in CONF.subunit_files]
    else:
        streams = [subunit.ReadSubunit(sys.stdin,
                                       attachments=CONF.store_attachments,
                                       attr_regex=CONF.attr_regex)]
    for stream in streams:
        process_results(stream.get_results())


if __name__ == "__main__":
    sys.exit(main())
