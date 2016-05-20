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
import types

from six import moves
import testscenarios

from subunit2sql.db import api
from subunit2sql.db import models
from subunit2sql.tests import base
from subunit2sql.tests import db_test_utils
from subunit2sql.tests import subunit2sql_fixtures as fixtures

load_tests = testscenarios.load_tests_apply_scenarios


class TestDatabaseAPI(base.TestCase):

    scenarios = [
        ('mysql', {'dialect': 'mysql'}),
        ('postgresql', {'dialect': 'postgres'}),
        ('sqlite', {'dialect': 'sqlite'})
    ]

    def setUp(self):
        super(TestDatabaseAPI, self).setUp()
        self.useFixture(fixtures.LockFixture(self.dialect))
        if not db_test_utils.is_backend_avail(self.dialect):
            raise self.skipTest('%s is not available' % self.dialect)
        if self.dialect == 'mysql':
            self.useFixture(fixtures.MySQLConfFixture())
        elif self.dialect == 'postgres':
            self.useFixture(fixtures.PostgresConfFixture())
        elif self.dialect == 'sqlite':
            self.useFixture(fixtures.SqliteConfFixture())
        self.useFixture(fixtures.Database())

    def test_create_test(self):
        api.create_test('1234')
        res = api.get_all_tests()
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].test_id, '1234')

    def test_create_test_and_get_by_test_id(self):
        create_res = api.create_test('fake_test', 2, 1, 1, 1.2)
        res = api.get_test_by_test_id('fake_test')
        self.assertEqual(res.id, create_res.id)
        self.assertEqual(res.test_id, 'fake_test')
        self.assertEqual(res.run_time, 1.2)
        self.assertEqual(res.run_count, 2)

    def test_get_test_by_test_id_invalid_id(self):
        res = api.get_test_by_test_id('fake_test')
        self.assertIsNone(res)

    def test_create_run_and_list(self):
        res = api.create_run()
        self.assertIsNotNone(res)
        all_runs = api.get_all_runs()
        self.assertEqual(len(all_runs), 1)
        self.assertEqual(res.id, all_runs[0].id)

    def test_update_run_and_list(self):
        res = api.create_run()
        dt = datetime.datetime.utcnow()
        # NOTE(masayukig): The DateTime column in some DB envs can't store a
        # microseconds resolution value. So this removes the microseconds value
        # here.
        dt = dt.replace(microsecond=0)
        dt_dummy = dt - datetime.timedelta(days=1)
        res_dummy = api.create_run(run_at=dt_dummy)

        values = {'skips': 98, 'fails': 97, 'passes': 96, 'run_time': 1.123,
                  'artifacts': 'fake_url', 'run_at': dt}
        updated_res = api.update_run(values, res.id)
        all_runs = api.get_all_runs()
        self.assertEqual(len(all_runs), 2)
        for run in all_runs:
            if run.id == res.id:
                self.assertEqual(updated_res.id, run.id)
                for key in values:
                    self.assertEqual(values[key], run[key])
                    self.assertEqual(run[key], updated_res[key])
            elif run.id == res_dummy.id:
                self.assertNotEqual(updated_res.id, run.id)
                for key in values:
                    if key == 'run_at':
                        continue
                    self.assertNotEqual(values[key], run[key])
                    self.assertNotEqual(run[key], updated_res[key])
            else:
                self.fail('an unexpected run(%s) was found' % run.id)

    def test_get_test_runs_dicts_with_no_meta(self):
        run = api.create_run()
        test_a = api.create_test('fake_test')
        start_time = datetime.datetime.utcnow()
        stop_time = datetime.datetime.utcnow()
        api.create_test_run(test_a.id, run.id, 'success',
                            start_time, stop_time)
        test_run_dict = api.get_tests_run_dicts_from_run_id(run.uuid)
        self.assertEqual(1, len(test_run_dict))
        self.assertIn('fake_test', test_run_dict)
        self.assertEqual(test_run_dict['fake_test']['status'], 'success')
        self.assertEqual(test_run_dict['fake_test']['start_time'], start_time)
        self.assertEqual(test_run_dict['fake_test']['stop_time'], stop_time)
        self.assertNotIn('metadata', test_run_dict['fake_test'])

    def test_get_test_runs_dicts_with_no_stop_time(self):
        run = api.create_run()
        test_a = api.create_test('fake_test')
        start_time = datetime.datetime.utcnow()
        stop_time = None
        api.create_test_run(test_a.id, run.id, 'success',
                            start_time, stop_time)
        test_run_dict = api.get_tests_run_dicts_from_run_id(run.uuid)
        self.assertEqual(1, len(test_run_dict))
        self.assertIn('fake_test', test_run_dict)
        self.assertEqual(test_run_dict['fake_test']['status'], 'success')
        self.assertEqual(test_run_dict['fake_test']['start_time'], start_time)
        self.assertEqual(test_run_dict['fake_test']['stop_time'], stop_time)

    def test_get_test_runs_dicts_with_no_start_time(self):
        run = api.create_run()
        test_a = api.create_test('fake_test')
        stop_time = datetime.datetime.utcnow()
        start_time = None
        api.create_test_run(test_a.id, run.id, 'success',
                            start_time, stop_time)
        test_run_dict = api.get_tests_run_dicts_from_run_id(run.uuid)
        self.assertEqual(1, len(test_run_dict))
        self.assertIn('fake_test', test_run_dict)
        self.assertEqual(test_run_dict['fake_test']['status'], 'success')
        self.assertEqual(test_run_dict['fake_test']['start_time'], start_time)
        self.assertEqual(test_run_dict['fake_test']['stop_time'], stop_time)

    def test_get_test_runs_dicts_with_no_start_or_stop_time(self):
        run = api.create_run()
        test_a = api.create_test('fake_test')
        stop_time = None
        start_time = None
        api.create_test_run(test_a.id, run.id, 'success',
                            start_time, stop_time)
        test_run_dict = api.get_tests_run_dicts_from_run_id(run.uuid)
        self.assertEqual(1, len(test_run_dict))
        self.assertIn('fake_test', test_run_dict)
        self.assertEqual(test_run_dict['fake_test']['status'], 'success')
        self.assertEqual(test_run_dict['fake_test']['start_time'], start_time)
        self.assertEqual(test_run_dict['fake_test']['stop_time'], stop_time)

    def test_get_test_runs_dicts_with_meta(self):
        run = api.create_run()
        test_a = api.create_test('fake_test')
        test_run = api.create_test_run(test_a.id, run.id, 'success',
                                       datetime.datetime.utcnow(),
                                       datetime.datetime.utcnow())
        run_meta = {
            'key_a': 'value_b',
            'key_b': 'value_a',
            'attrs': 'test,smoke,notatest',
        }
        api.add_test_run_metadata(run_meta, test_run.id)
        test_run_dict = api.get_tests_run_dicts_from_run_id(run.uuid)
        self.assertEqual(3, len(test_run_dict['fake_test']['metadata']))
        for meta in run_meta:
            self.assertIn(meta, test_run_dict['fake_test']['metadata'])
            self.assertEqual(run_meta[meta],
                             test_run_dict['fake_test']['metadata'][meta])

    def test_create_test_run_and_list(self):
        run = api.create_run()
        test = api.create_test('fake_test')
        test_run = api.create_test_run(test.id, run.id, 'fail')
        self.assertIsNotNone(test_run)
        all_test_runs = api.get_all_test_runs()
        self.assertEqual(len(all_test_runs), 1)
        self.assertEqual(test_run.id, all_test_runs[0].id)

    def test_get_test_runs_dicts_from_run_id_are_in_chrono_order(self):
        run = api.create_run()
        test_a = api.create_test('fake_test')
        test_b = api.create_test('fake_test_2')
        test_c = api.create_test('fake_test_3')
        api.create_test_run(test_a.id, run.id, 'success',
                            datetime.datetime.utcnow())
        api.create_test_run(test_b.id, run.id, 'success',
                            datetime.datetime(1914, 6, 28, 10, 45, 0))
        api.create_test_run(test_c.id, run.id, 'success',
                            datetime.datetime(2014, 8, 26, 20, 00, 00))
        test_run_dicts = api.get_tests_run_dicts_from_run_id(run.uuid)
        self.assertEqual(len(test_run_dicts), 3)
        prev = None
        for test_run in test_run_dicts:
            if prev == None:
                prev = test_run
                continue
            self.assertTrue(test_run_dicts[test_run]['start_time'] >
                            test_run_dicts[prev]['start_time'])
            prev = test_run

    def test_get_test_run_duration(self):
        start_time = datetime.datetime.utcnow()
        stop_time = start_time + datetime.timedelta(minutes=3)
        run = api.create_run()
        test_a = api.create_test('fake_test')
        test_run = api.create_test_run(test_a.id, run.id, 'success',
                                       start_time, stop_time)
        dur = api.get_test_run_duration(test_run.id)
        self.assertEqual(180.0, dur)

    def test_get_id_from_test_id(self):
        test_a = api.create_test('fake_test')
        id_value = api.get_id_from_test_id('fake_test')
        self.assertEqual(test_a.id, id_value)

    def test_get_test_runs_by_run_id(self):
        run_b = api.create_run()
        run_a = api.create_run()
        run_c = api.create_run()
        test_a = api.create_test('fake_test')
        testrun_a = api.create_test_run(test_a.id, run_a.id, 'success',
                                        datetime.datetime.utcnow())
        testrun_b = api.create_test_run(test_a.id, run_b.id, 'success',
                                        datetime.datetime.utcnow())
        testrun_c = api.create_test_run(test_a.id, run_c.id, 'success',
                                        datetime.datetime.utcnow())
        test_runs_a = api.get_test_runs_by_run_id(run_a.uuid)
        test_runs_b = api.get_test_runs_by_run_id(run_b.uuid)
        test_runs_c = api.get_test_runs_by_run_id(run_c.uuid)
        self.assertEqual(len(test_runs_a), 1)
        self.assertEqual(testrun_a.id, test_runs_a[0].id)
        self.assertEqual(testrun_a.status, test_runs_a[0].status)
        self.assertEqual(len(test_runs_b), 1)
        self.assertEqual(testrun_b.id, test_runs_b[0].id)
        self.assertEqual(testrun_b.status, test_runs_b[0].status)
        self.assertEqual(len(test_runs_c), 1)
        self.assertEqual(testrun_c.id, test_runs_c[0].id)
        self.assertEqual(testrun_c.status, test_runs_c[0].status)

    def test_get_runs_by_status_grouped_by_run_metadata(self):
        # Generating 20 runs:
        # 10 with no failures
        # 10 with 10 failures
        # 7 in 2010/2011 each, 6 in 2012
        # 10 in projecta/projectb each
        for i in moves.range(20):
            if i % 2 == 1:
                fails = 10
            else:
                fails = 0
            year = 2010 + (i % 3)
            run_at = datetime.datetime(year, 1, i + 1, 12, 0, 0)
            run = api.create_run(fails=fails, passes=10, run_at=run_at)
            self.assertIsNotNone(run)
            if i < 10:
                project = 'projecta'
            else:
                project = 'projectb'
            meta_dict = {'project': project}
            api.add_run_metadata(meta_dict, run.id)
        result = api.get_runs_by_status_grouped_by_run_metadata(
            'project', start_date='2012-01-01', stop_date='2012-12-31')
        # There should be two projects
        self.assertEqual(2, len(result.keys()))
        self.assertTrue('projecta' in result)
        self.assertTrue('projectb' in result)
        # There should be passes and failures
        self.assertEqual(2, len(result['projecta'].keys()))
        self.assertTrue('pass' in result['projecta'])
        self.assertTrue('fail' in result['projecta'])
        self.assertEqual(2, len(result['projectb'].keys()))
        self.assertTrue('pass' in result['projectb'])
        self.assertTrue('fail' in result['projectb'])

        self.assertEqual(2, result['projecta']['pass'])
        self.assertEqual(1, result['projecta']['fail'])
        self.assertEqual(1, result['projectb']['pass'])
        self.assertEqual(2, result['projectb']['fail'])

    def test_get_time_series_runs_by_key_value(self):
        runs = []
        run_at = datetime.datetime.utcnow()
        for run_num in moves.range(15):
            run = api.create_run(run_num, run_num + 1, run_num + 2, 3,
                                 run_at=run_at)
            runs.append(run)
            run_meta = {'test_key': 'fun', 'non_test': 'value-%s' % run_num}
            if run_num >= 3:
                run_meta = {'test_key': 'no-fun',
                            'non_test': 'value-%s' % run_num}
            api.add_run_metadata(run_meta, run.id)
        runs_time_series = api.get_time_series_runs_by_key_value('test_key',
                                                                 'fun')
        self.assertEqual(1, len(runs_time_series))
        timestamp = list(runs_time_series.keys())[0]
        self.assertEqual(3, len(runs_time_series[timestamp]))
        for run_num in moves.range(3):
            run_dict = {
                'skip': run_num,
                'fail': run_num + 1,
                'pass': run_num + 2,
                'id': runs[run_num].uuid,
                'run_time': 3.0,
                'metadata': {
                    u'test_key': u'fun',
                    u'non_test': u'value-%s' % run_num
                }
            }
            self.assertIn(run_dict, runs_time_series[timestamp])
        for run_num in moves.range(3, 14):
            missing_run_dict = {
                'skip': run_num,
                'fail': run_num + 1,
                'pass': run_num + 2,
                'id': runs[run_num].id,
                'run_time': 3.0,
                'metadata': {
                    u'test_key': u'fun',
                    u'non_test': u'value-%s' % run_num
                }
            }
            self.assertNotIn(missing_run_dict, runs_time_series[timestamp])

    def test_get_test_runs_test_test_id(self):
        run = api.create_run()
        test_a = api.create_test('fake_test')
        test_b = api.create_test('less_fake_test')
        api.create_test_run(test_a.id, run.id, 'success')
        api.create_test_run(test_b.id, run.id, 'success')
        res = api.get_test_runs_by_test_test_id('less_fake_test')
        self.assertEqual(1, len(res))
        self.assertEqual(test_b.id, res[0].test_id)
        self.assertEqual(run.id, res[0].run_id)

    def test_get_test_runs_test_test_id_with_run_metadata(self):
        run_a = api.create_run()
        run_b = api.create_run()
        api.add_run_metadata({'a_key': 'a_value'}, run_a.id)
        api.add_run_metadata({'b_key': 'b_value'}, run_b.id)
        test_a = api.create_test('fake_test')
        test_b = api.create_test('less_fake_test')
        api.create_test_run(test_a.id, run_a.id, 'success')
        api.create_test_run(test_a.id, run_b.id, 'success')
        api.create_test_run(test_b.id, run_a.id, 'success')
        api.create_test_run(test_b.id, run_b.id, 'success')
        res = api.get_test_runs_by_test_test_id('less_fake_test', key='a_key',
                                                value='a_value')
        self.assertEqual(1, len(res))
        self.assertEqual(test_b.id, res[0].test_id)
        self.assertEqual(run_a.id, res[0].run_id)

    def test_get_all_run_metadata_keys(self):
        run = api.create_run()
        meta_dict = {
            'test_a': 'a',
            'test_a': 'b',
            'test_b': 'a',
            'test_c': 'a',
            'test_d': 'a',
            'test_c': 'b',
        }
        api.add_run_metadata(meta_dict, run.id)
        keys = api.get_all_run_metadata_keys()
        self.assertEqual(sorted(['test_a', 'test_b', 'test_c', 'test_d']),
                         sorted(keys))

    def test_get_all_test_metadata_keys(self):
        test = api.create_test('fake_test')
        meta_dict = {
            'test_a': 'a',
            'test_a': 'b',
            'test_b': 'a',
            'test_c': 'a',
            'test_d': 'a',
            'test_c': 'b',
        }
        api.add_test_metadata(meta_dict, test.id)
        keys = api.get_all_test_metadata_keys()
        self.assertEqual(sorted(['test_a', 'test_b', 'test_c', 'test_d']),
                         sorted(keys))

    def test_get_all_test_run_metadata_keys(self):
        run = api.create_run()
        test = api.create_test('fake_test')
        test_run = api.create_test_run(test.id, run.id, 'skip')
        meta_dict = {
            'test_a': 'a',
            'test_a': 'b',
            'test_b': 'a',
            'test_c': 'a',
            'test_d': 'a',
            'test_c': 'b',
        }
        api.add_test_run_metadata(meta_dict, test_run.id)
        keys = api.get_all_test_run_metadata_keys()
        self.assertEqual(sorted(['test_a', 'test_b', 'test_c', 'test_d']),
                         sorted(keys))

    def test_get_test_run_series(self):
        timestamp_a = datetime.datetime.utcnow()
        timestamp_b = timestamp_a + datetime.timedelta(minutes=2)
        api.create_run(passes=5, run_at=timestamp_a)
        api.create_run(fails=2, run_at=timestamp_b)
        result = api.get_test_run_series(key=None, value=None)
        self.assertEqual(2, len(result.keys()))
        self.assertIn(timestamp_a.replace(microsecond=0),
                      [x.replace(microsecond=0) for x in list(result.keys())])
        self.assertIn(timestamp_b.replace(microsecond=0),
                      [x.replace(microsecond=0) for x in list(result.keys())])
        for timestamp in result:
            if timestamp.replace(
                microsecond=0) == timestamp_a.replace(microsecond=0):
                self.assertEqual(5, result[timestamp])
            else:
                self.assertEqual(2, result[timestamp])

    def test_get_test_run_series_with_meta(self):
        timestamp_a = datetime.datetime.utcnow()
        timestamp_b = timestamp_a + datetime.timedelta(minutes=2)
        run_a = api.create_run(passes=5, run_at=timestamp_a)
        api.create_run(fails=2, run_at=timestamp_b)
        api.add_run_metadata({'not_a_key': 'not_a_value'}, run_a.id)
        result = api.get_test_run_series(key='not_a_key',
                                         value='not_a_value')
        self.assertEqual(1, len(result.keys()))
        self.assertIn(timestamp_a.replace(microsecond=0),
                      [x.replace(microsecond=0) for x in list(result.keys())])
        self.assertNotIn(timestamp_b.replace(microsecond=0),
                         [x.replace(microsecond=0) for x in list(
                             result.keys())])
        self.assertEqual(5, result[list(result.keys())[0]])

    def test_get_run_times_grouped_by_run_metadata_key(self):
        run_a = api.create_run(run_time=2.2, passes=2)
        run_b = api.create_run(run_time=3.5, passes=3)
        api.add_run_metadata({'key': 'value_a'}, run_a.id)
        api.add_run_metadata({'key': 'value_b'}, run_b.id)
        res = api.get_run_times_grouped_by_run_metadata_key('key')
        expected_res = {'value_a': [2.2], 'value_b': [3.5]}
        self.assertEqual(expected_res, res)

    def test_get_test_run_dict_by_run_meta_key_value(self):
        timestamp_a = datetime.datetime.utcnow()
        timestamp_b = timestamp_a + datetime.timedelta(minutes=2)
        run_a = api.create_run()
        run_b = api.create_run()
        api.add_run_metadata({'key': 'true'}, run_a.id)
        api.add_run_metadata({'key': 'not so true'}, run_b.id)
        test_a = api.create_test('fake_test')
        api.create_test_run(test_a.id, run_a.id, 'success', timestamp_a,
                            timestamp_b)
        api.create_test_run(test_a.id, run_b.id, 'fail', timestamp_a,
                            datetime.datetime.utcnow())
        test_run_dicts = api.get_test_run_dict_by_run_meta_key_value('key',
                                                                     'true')
        self.assertEqual(1, len(test_run_dicts))
        self.assertEqual([{
            'test_id': 'fake_test',
            'status': 'success',
            'start_time': timestamp_a,
            'stop_time': timestamp_b,
        }], test_run_dicts)

    def test_delete_old_runs(self):
        run_a = api.create_run(run_at=datetime.datetime(
            1914, 6, 28, 10, 45, 0))
        run_b = api.create_run()
        api.add_run_metadata({'key': 'value'}, run_b.id)
        api.add_run_metadata({'key': 'not_so_much_a_value'}, run_a.id)
        api.delete_old_runs()
        runs = api.get_all_runs()
        self.assertEqual(1, len(runs))
        self.assertEqual(1, api.get_session().query(
            models.RunMetadata.id).count())
        self.assertEqual(run_b.id, runs[0].id)
        self.assertEqual(1, len(api.get_run_metadata(run_b.uuid)))
        self.assertEqual(0, len(api.get_run_metadata(run_a.uuid)))

    def test_delete_old_test_runs(self):
        run_a = api.create_run()
        run_b = api.create_run()
        test = api.create_test('fake_test')
        test_run_a = api.create_test_run(test.id, run_a.id, 'fail',
                                         start_time=datetime.datetime(
                                             1914, 6, 28, 10, 45, 0))
        test_run_b = api.create_test_run(test.id, run_b.id, 'fail',
                                         start_time=datetime.datetime.utcnow())
        api.add_test_run_metadata({'key': 'value'}, test_run_b.id)
        api.add_test_run_metadata({'key': 'not_so_much_a_value'},
                                  test_run_a.id)
        api.delete_old_test_runs()
        test_runs = api.get_all_test_runs()
        self.assertEqual(1, len(test_runs))
        self.assertEqual(test_run_b.id, test_runs[0].id)
        self.assertEqual(1, len(api.get_test_run_metadata(test_run_b.id)))
        self.assertEqual(0, len(api.get_test_run_metadata(test_run_a.id)))

    def test_get_run_metadata(self):
        run_a = api.create_run()
        run_b = api.create_run()
        api.add_run_metadata({'not_a_key': 'not_a_value'}, run_b.id)
        a_metadata = api.get_run_metadata(run_a.uuid)
        b_metadata = api.get_run_metadata(run_b.uuid)
        self.assertEqual([], a_metadata)
        self.assertEqual(1, len(b_metadata))
        b_metadata = b_metadata[0].to_dict()
        self.assertEqual(run_b.id, b_metadata['run_id'])
        self.assertEqual('not_a_key', b_metadata['key'])
        self.assertEqual('not_a_value', b_metadata['value'])

    def test_get_runs_by_key_value(self):
        api.create_run()
        run_b = api.create_run()
        api.add_run_metadata({'not_a_key': 'not_a_value'}, run_b.id)
        found_runs = api.get_runs_by_key_value('not_a_key', 'not_a_value')
        self.assertEqual(1, len(found_runs))
        self.assertEqual(run_b.id, found_runs[0].id)
        self.assertEqual(run_b.uuid, found_runs[0].uuid)

    def test_get_tests_from_run_id(self):
        run_a = api.create_run()
        run_b = api.create_run()
        test_a = api.create_test('fake_test')
        test_b = api.create_test('fake_test2')
        api.create_test_run(test_a.id, run_a.id, 'fail',
                            start_time=datetime.datetime(1914, 6, 28, 10, 45,
                                                         0))
        api.create_test_run(test_a.id, run_b.id, 'fail',
                            start_time=datetime.datetime.utcnow())
        api.create_test_run(test_b.id, run_a.id, 'success',
                            start_time=datetime.datetime(1914, 6, 28, 10, 45,
                                                         0))
        result = api.get_tests_from_run_id(run_a.id)
        self.assertEqual(2, len(result))
        self.assertIn(test_a.id, [x.id for x in result])
        self.assertIn(test_a.test_id, [x.test_id for x in result])
        self.assertIn(test_b.id, [x.id for x in result])
        self.assertIn(test_b.test_id, [x.test_id for x in result])

    def test_get_all_runs_time_series_by_key(self):
        time_a = datetime.datetime(1914, 6, 28, 10, 45, 0)
        run_a = api.create_run(run_at=time_a)
        run_b = api.create_run()
        time_c = datetime.datetime(1918, 11, 11, 11, 11, 11)
        run_c = api.create_run(run_at=time_c)
        api.add_run_metadata({'not_a_key': 'not_a_value'}, run_b.id)
        api.add_run_metadata({'a_key': 'a_value'}, run_a.id)
        api.add_run_metadata({'a_key': 'c_value'}, run_c.id)
        result = api.get_all_runs_time_series_by_key('a_key')
        self.assertEqual(2, len(result.keys()))
        self.assertIn(time_a.date(), [x.date() for x in result.keys()])
        self.assertIn(time_c.date(), [x.date() for x in result.keys()])

    def test_get_recent_runs_by_key_value_metadata(self):
        run_a = api.create_run()
        run_b = api.create_run()
        run_c = api.create_run()
        api.add_run_metadata({'a_key': 'a_value'}, run_a.id)
        api.add_run_metadata({'a_key': 'a_value'}, run_c.id)
        api.add_run_metadata({'a_key': 'b_value'}, run_b.id)
        result = api.get_recent_runs_by_key_value_metadata('a_key', 'a_value')
        self.assertEqual(2, len(result))
        self.assertIn(run_a.id, [x.id for x in result])
        self.assertNotIn(run_b.id, [x.id for x in result])
        self.assertIn(run_c.id, [x.id for x in result])

    def test_get_recent_runs_by_key_value_metadata_with_start_date(self):
        run_a = api.create_run(run_at=datetime.datetime(
            1914, 6, 28, 10, 45, 0))
        run_b = api.create_run()
        run_c = api.create_run()
        api.add_run_metadata({'a_key': 'a_value'}, run_a.id)
        api.add_run_metadata({'a_key': 'a_value'}, run_c.id)
        api.add_run_metadata({'a_key': 'b_value'}, run_b.id)
        result = api.get_recent_runs_by_key_value_metadata(
            'a_key', 'a_value', start_date=datetime.datetime(
                1918, 11, 11, 11, 11, 11))
        self.assertEqual(1, len(result))
        self.assertNotIn(run_a.id, [x.id for x in result])
        self.assertNotIn(run_b.id, [x.id for x in result])
        self.assertIn(run_c.id, [x.id for x in result])

    def test_get_recent_runs_by_key_value_metadata_one_run(self):
        timestamp = datetime.datetime(1914, 6, 28, 10, 45, 0)
        run_a = api.create_run(run_at=timestamp)
        run_b = api.create_run()
        run_c = api.create_run()
        api.add_run_metadata({'a_key': 'a_value'}, run_a.id)
        api.add_run_metadata({'a_key': 'a_value'}, run_c.id)
        api.add_run_metadata({'a_key': 'b_value'}, run_b.id)
        result = api.get_recent_runs_by_key_value_metadata('a_key', 'a_value',
                                                           num_runs=1)
        self.assertEqual(1, len(result))
        self.assertNotIn(run_a.id, [x.id for x in result])
        self.assertNotIn(run_b.id, [x.id for x in result])
        self.assertIn(run_c.id, [x.id for x in result])

    def test_get_test_runs_by_status_for_run_ids_no_meta(self):
        run_b = api.create_run(artifacts='fake_url')
        run_a = api.create_run()
        run_c = api.create_run()
        test_a = api.create_test('fake_test')
        start_timestamp = datetime.datetime(1914, 6, 28, 10, 45, 0)
        stop_timestamp = datetime.datetime(1914, 6, 28, 10, 50, 0)
        api.create_test_run(test_a.id, run_a.id, 'success',
                            datetime.datetime.utcnow())
        api.create_test_run(test_a.id, run_b.id, 'fail',
                            start_timestamp, stop_timestamp)
        api.create_test_run(test_a.id, run_c.id, 'success',
                            datetime.datetime.utcnow())
        result = api.get_test_runs_by_status_for_run_ids(
            'fail', [run_a.uuid, run_b.uuid, run_c.uuid])
        self.assertEqual(1, len(result))
        self.assertEqual({
            'test_id': u'fake_test',
            'link': u'fake_url',
            'start_time': start_timestamp,
            'stop_time': stop_timestamp,
        }, result[0])

    def test_get_test_runs_by_status_for_run_ids_with_meta(self):
        run_b = api.create_run(artifacts='fake_url')
        run_a = api.create_run()
        run_c = api.create_run()
        test_a = api.create_test('fake_test')
        api.add_run_metadata({'a_key': 'b'}, run_b.id)
        api.add_run_metadata({'a_key': 'a'}, run_a.id)
        api.add_run_metadata({'a_key': 'c'}, run_c.id)
        start_timestamp = datetime.datetime(1914, 6, 28, 10, 45, 0)
        stop_timestamp = datetime.datetime(1914, 6, 28, 10, 50, 0)
        api.create_test_run(test_a.id, run_a.id, 'success',
                            datetime.datetime.utcnow())
        api.create_test_run(test_a.id, run_b.id, 'fail',
                            start_timestamp, stop_timestamp)
        api.create_test_run(test_a.id, run_c.id, 'success',
                            datetime.datetime.utcnow())
        result = api.get_test_runs_by_status_for_run_ids(
            'fail', [run_a.uuid, run_b.uuid, run_c.uuid], key='a_key')
        self.assertEqual(1, len(result))
        self.assertEqual({
            'test_id': u'fake_test',
            'link': u'fake_url',
            'start_time': start_timestamp,
            'stop_time': stop_timestamp,
            'a_key': 'b',
        }, result[0])

    def test_get_test_runs_by_status_for_run_ids_with_run_id(self):
        run_b = api.create_run(artifacts='fake_url')
        run_a = api.create_run()
        run_c = api.create_run()
        test_a = api.create_test('fake_test')
        api.add_run_metadata({'a_key': 'b'}, run_b.id)
        api.add_run_metadata({'a_key': 'a'}, run_a.id)
        api.add_run_metadata({'a_key': 'c'}, run_c.id)
        start_timestamp = datetime.datetime(1914, 6, 28, 10, 45, 0)
        stop_timestamp = datetime.datetime(1914, 6, 28, 10, 50, 0)
        api.create_test_run(test_a.id, run_a.id, 'success',
                            datetime.datetime.utcnow())
        api.create_test_run(test_a.id, run_b.id, 'fail',
                            start_timestamp, stop_timestamp)
        api.create_test_run(test_a.id, run_c.id, 'success',
                            datetime.datetime.utcnow())
        result = api.get_test_runs_by_status_for_run_ids(
            'fail', [run_a.uuid, run_b.uuid, run_c.uuid], key='a_key',
            include_run_id=True)
        self.assertEqual(1, len(result))
        self.assertEqual({
            'test_id': u'fake_test',
            'link': u'fake_url',
            'start_time': start_timestamp,
            'stop_time': stop_timestamp,
            'a_key': 'b',
            'uuid': run_b.uuid,
        }, result[0])

    def test_get_all_runs_time_series_by_key_with_overlap(self):
        time_a = datetime.datetime(1914, 6, 28, 10, 45, 0)
        run_a = api.create_run(run_at=time_a)
        run_b = api.create_run()
        time_c = datetime.datetime(1918, 11, 11, 11, 11, 11)
        run_c = api.create_run(run_at=time_c)
        run_d = api.create_run(run_at=time_a)
        api.add_run_metadata({'not_a_key': 'not_a_value'}, run_b.id)
        api.add_run_metadata({'a_key': 'a_value'}, run_a.id)
        api.add_run_metadata({'a_key': 'c_value'}, run_c.id)
        api.add_run_metadata({'a_key': 'a_value'}, run_d.id)
        result = api.get_all_runs_time_series_by_key('a_key')
        self.assertEqual(2, len(result.keys()))
        self.assertIn(time_a.date(), [x.date() for x in result.keys()])
        self.assertIn(time_c.date(), [x.date() for x in result.keys()])
        self.assertIn(time_a.date(), [x.date() for x in result.keys()])
        self.assertEqual(len(result[time_a]['a_value']), 2)

    def test_get_run_failure_rate_by_key_value_metadata(self):
        run_a = api.create_run(fails=100, passes=0)
        run_b = api.create_run()
        run_c = api.create_run(passes=100, fails=0)
        api.add_run_metadata({'a_key': 'a_value'}, run_a.id)
        api.add_run_metadata({'a_key': 'a_value'}, run_c.id)
        api.add_run_metadata({'a_key': 'b_value'}, run_b.id)
        fail_rate = api.get_run_failure_rate_by_key_value_metadata(
            'a_key', 'a_value')
        self.assertEqual(50, fail_rate)

    def test_get_test_prefixes(self):
        api.create_test('prefix.token.token')
        api.create_test('setUpClass (prefix.token.token)')
        api.create_test('other.token.token')
        api.create_test('justonetoken')

        prefixes = api.get_test_prefixes()
        self.assertEqual(len(prefixes), 3)
        self.assertIn('prefix', prefixes)
        self.assertIn('other', prefixes)
        self.assertIn('justonetoken', prefixes)

    def test_get_tests_by_prefix(self):
        api.create_test('prefix.token.token')
        api.create_test('setUpClass (prefix.token.token)')
        api.create_test('other.token.token')
        api.create_test('justonetoken')

        tests = api.get_tests_by_prefix('prefix')
        self.assertEqual(len(tests), 2)
        self.assertIn('prefix.token.token', [test.test_id for test in tests])
        self.assertIn('setUpClass (prefix.token.token)',
                      [test.test_id for test in tests])

        tests = api.get_tests_by_prefix('other')
        self.assertEqual(len(tests), 1)
        self.assertIn('other.token.token', [test.test_id for test in tests])

        tests = api.get_tests_by_prefix('prefix', limit=1, offset=1)
        self.assertEqual(len(tests), 1)
        self.assertIn('setUpClass (prefix.token.token)',
                      [test.test_id for test in tests])

        tests = api.get_tests_by_prefix('justonetoken')
        self.assertEqual(len(tests), 1)
        self.assertIn('justonetoken', [test.test_id for test in tests])

    def test_update_test(self):
        create_res = api.create_test('fake_test')
        values = {'run_count': 2, 'run_time': 1.2}
        update_res = api.update_test(values, create_res.id)
        res = api.get_test_by_test_id('fake_test')
        self.assertEqual(res.id, update_res.id)
        self.assertEqual(res.test_id, 'fake_test')
        self.assertEqual(res.run_time, 1.2)
        self.assertEqual(res.run_count, 2)

    def test_update_test_run(self):
        run = api.create_run()
        test = api.create_test('fake_test')
        test_run = api.create_test_run(test.id, run.id, 'fail')
        start_time = datetime.datetime.utcnow()
        stop_time = datetime.datetime.utcnow()
        start_time = start_time.replace(microsecond=0)
        stop_time = start_time.replace(microsecond=0)
        values = {'status': 'success', 'start_time': start_time,
                  'stop_time': stop_time}
        update_test_run = api.update_test_run(values, test_run.id)
        all_test_runs = api.get_all_test_runs()
        self.assertEqual(len(all_test_runs), 1)
        self.assertEqual(update_test_run.id, all_test_runs[0].id)
        self.assertEqual(all_test_runs[0].status, 'success')
        self.assertEqual(all_test_runs[0].start_time, start_time)
        self.assertEqual(all_test_runs[0].stop_time, stop_time)

    def test_get_test_run_by_id(self):
        run = api.create_run()
        test = api.create_test('fake_test')
        test_run = api.create_test_run(test.id, run.id, 'fail')
        res = api.get_test_run_by_id(test_run.id)
        self.assertEqual(res.id, test_run.id)
        self.assertEqual(res.status, 'fail')
        self.assertEqual(res.run_id, run.id)

    def test_get_test_by_id(self):
        create_res = api.create_test('fake_test', 2, 1, 1, 1.2)
        res = api.get_test_by_id(create_res.id)
        self.assertEqual(res.id, create_res.id)
        self.assertEqual(res.test_id, 'fake_test')
        self.assertEqual(res.run_time, 1.2)
        self.assertEqual(res.run_count, 2)

    def test_get_run_id_from_uuid(self):
        run = api.create_run()
        run_id = api.get_run_id_from_uuid(run.uuid)
        self.assertEqual(run_id, run.id)

    def test_get_run_by_id(self):
        run = api.create_run()
        res = api.get_run_by_id(run.id)
        self.assertEqual(res.id, run.id)
        self.assertEqual(res.uuid, run.uuid)

    def test_get_test_runs_by_test_id(self):
        run_a = api.create_run()
        run_b = api.create_run()
        run_c = api.create_run()
        test = api.create_test('fake_test')
        api.create_test_run(test.id, run_a.id, 'success')
        api.create_test_run(test.id, run_b.id, 'fail')
        api.create_test_run(test.id, run_c.id, 'success')
        res = api.get_test_runs_by_test_id(test.id)
        self.assertEqual(3, len(res))
        self.assertIn(run_a.id, [x.run_id for x in res])
        self.assertIn(run_b.id, [x.run_id for x in res])
        self.assertIn(run_c.id, [x.run_id for x in res])

    def test_get_test_metadata(self):
        test = api.create_test('fake_test')
        test_meta = {
            'test_a': 'a',
            'test_b': 'b',
            'test_c': 'c',
        }
        api.add_test_metadata(test_meta, test.id)
        test_metadata = api.get_test_metadata(test.id)
        self.assertEqual(3, len(test_metadata))
        for meta in test_metadata:
            self.assertIn(meta.key, test_meta.keys())
            self.assertIn(meta.value, test_meta.values())

    def test_get_recent_failed_runs_by_run_metadata_no_start_date(self):
        run_a = api.create_run(fails=1)
        api.create_run()
        run_c = api.create_run(fails=2)
        api.add_run_metadata({'fake_key': 'fake_value'}, run_a.id)
        api.add_run_metadata({'zeon': 'zaku'}, run_c.id)
        results = api.get_recent_failed_runs_by_run_metadata('zeon', 'zaku')
        self.assertEqual(1, len(results))
        self.assertEqual(run_c.id, results[0].id)

    def test_get_recent_failed_runs_by_run_metadata_with_start_date(self):
        run_a = api.create_run(fails=1)
        api.create_run()
        run_c = api.create_run(fails=2)
        run_d = api.create_run(fails=3,
                               run_at=datetime.datetime(1914, 6, 28,
                                                        10, 45, 0))
        api.add_run_metadata({'fake_key': 'fake_value'}, run_a.id)
        api.add_run_metadata({'zeon': 'zaku'}, run_c.id)
        api.add_run_metadata({'zeon': 'zaku'}, run_d.id)
        results = api.get_recent_failed_runs_by_run_metadata(
            'zeon', 'zaku', start_date=datetime.date(1970, 1, 1))
        self.assertEqual(1, len(results))
        self.assertEqual(run_c.id, results[0].id)

    def test_get_test_run_metadata(self):
        run = api.create_run()
        test = api.create_test('fake_test')
        test_run = api.create_test_run(test.id, run.id, 'success',
                                       datetime.datetime.utcnow(),
                                       datetime.datetime.utcnow())
        run_meta = {
            'key_a': 'value_b',
            'key_b': 'value_a',
        }
        api.add_test_run_metadata(run_meta, test_run.id)
        test_run_metadata = api.get_test_run_metadata(test_run.id)
        self.assertEqual(2, len(test_run_metadata))
        for meta in test_run_metadata:
            self.assertIn(meta.key, run_meta.keys())
            self.assertIn(meta.value, run_meta.values())

    def test_get_all_runs_by_date(self):
        timestamp_a = datetime.datetime.utcnow().replace(microsecond=0)
        timestamp_b = timestamp_a + datetime.timedelta(minutes=10)
        timestamp_c = timestamp_a + datetime.timedelta(minutes=20)
        api.create_run(run_at=timestamp_a)
        api.create_run(run_at=timestamp_b)
        api.create_run(run_at=timestamp_c)
        res = api.get_all_runs_by_date()
        self.assertEqual(3, len(res))
        self.assertIn(timestamp_a, [x.run_at for x in res])
        self.assertIn(timestamp_b, [x.run_at for x in res])
        self.assertIn(timestamp_c, [x.run_at for x in res])
        res = api.get_all_runs_by_date(start_date=timestamp_c)
        self.assertEqual(1, len(res))
        self.assertEqual(timestamp_c, res[0].run_at)
        res = api.get_all_runs_by_date(stop_date=timestamp_a)
        self.assertEqual(1, len(res))
        self.assertEqual(timestamp_a, res[0].run_at)
        res = api.get_all_runs_by_date(start_date=timestamp_a,
                                       stop_date=timestamp_b)
        self.assertEqual(2, len(res))
        self.assertIn(timestamp_a, [x.run_at for x in res])
        self.assertIn(timestamp_b, [x.run_at for x in res])

    def test_get_latest_run(self):
        timestamp_a = datetime.datetime.utcnow().replace(microsecond=0)
        timestamp_b = timestamp_a + datetime.timedelta(minutes=10)
        timestamp_c = timestamp_a + datetime.timedelta(minutes=20)
        api.create_run(run_at=timestamp_a)
        api.create_run(run_at=timestamp_b)
        api.create_run(run_at=timestamp_c)
        res = api.get_latest_run()
        self.assertEqual(timestamp_c, res.run_at)

    def test_get_failing_from_run(self):
        timestamp_a = datetime.datetime.utcnow().replace(microsecond=0)
        timestamp_b = timestamp_a + datetime.timedelta(minutes=10)
        timestamp_c = timestamp_a + datetime.timedelta(minutes=20)
        run_a = api.create_run()
        run_b = api.create_run()
        test_a = api.create_test('fake_test')
        test_b = api.create_test('fake_test2')
        api.create_test_run(test_a.id, run_a.id, 'fail',
                            start_time=timestamp_a)
        api.create_test_run(test_a.id, run_b.id, 'fail',
                            start_time=timestamp_a)
        api.create_test_run(test_b.id, run_b.id, 'fail',
                            start_time=timestamp_b)
        api.create_test_run(test_b.id, run_a.id, 'success',
                            start_time=timestamp_c)
        res = api.get_failing_from_run(run_a.id)
        self.assertEqual(1, len(res))
        self.assertEqual(test_a.id, res[0].test_id)
        self.assertEqual(timestamp_a, res[0].start_time)
        res = api.get_failing_from_run(run_b.id)
        self.assertEqual(2, len(res))
        self.assertEqual('fail', res[0].status)
        self.assertIn(timestamp_a, [x.start_time for x in res])
        self.assertIn(timestamp_b, [x.start_time for x in res])

    def test_get_test_run_time_series(self):
        timestamp_a = datetime.datetime.utcnow().replace(microsecond=0)
        timestamp_b = timestamp_a + datetime.timedelta(minutes=10)
        timestamp_c = timestamp_a + datetime.timedelta(minutes=15)
        run_a = api.create_run()
        run_b = api.create_run()
        test = api.create_test('fake_test')
        api.create_test_run(test.id, run_a.id, 'success',
                            start_time=timestamp_a,
                            end_time=timestamp_b)
        api.create_test_run(test.id, run_b.id, 'success',
                            start_time=timestamp_b,
                            end_time=timestamp_c)
        res = api.get_test_run_time_series(test.id)
        self.assertEqual(res[timestamp_a], 600)
        self.assertEqual(res[timestamp_b], 300)

    def test_get_test_status_time_series(self):
        timestamp_a = datetime.datetime.utcnow().replace(microsecond=0)
        timestamp_b = timestamp_a + datetime.timedelta(minutes=10)
        timestamp_c = timestamp_a + datetime.timedelta(minutes=20)
        run_a = api.create_run()
        run_b = api.create_run()
        test = api.create_test('fake_test')
        api.create_test_run(test.id, run_a.id, 'success',
                            start_time=timestamp_a,
                            end_time=timestamp_b)
        api.create_test_run(test.id, run_b.id, 'fail',
                            start_time=timestamp_b,
                            end_time=timestamp_c)
        res = api.get_test_status_time_series(test.id)
        self.assertEqual(res[timestamp_a], 'success')
        self.assertEqual(res[timestamp_b], 'fail')

    def test_get_recent_failed_runs(self):
        run_a = api.create_run(fails=1)
        api.create_run()
        run_c = api.create_run(fails=2)
        run_d = api.create_run(fails=1)
        res = api.get_recent_failed_runs()
        self.assertEqual(3, len(res))
        self.assertIn(run_a.uuid, res)
        self.assertIn(run_c.uuid, res)
        self.assertIn(run_d.uuid, res)

    def test_get_recent_failed_runs_with_start_date(self):
        api.create_run(fails=1, run_at=datetime.datetime(
            1914, 6, 28, 10, 45, 0))
        api.create_run()
        run_c = api.create_run(fails=2)
        run_d = api.create_run(fails=1)
        res = api.get_recent_failed_runs(start_date=datetime.datetime(
            1918, 11, 11, 11, 11, 11))
        self.assertEqual(2, len(res))
        self.assertIn(run_c.uuid, res)
        self.assertIn(run_d.uuid, res)

    def test_get_recent_successful_runs(self):
        run_a = api.create_run(passes=1)
        run_b = api.create_run()
        run_c = api.create_run(passes=2)
        api.create_run(fails=1)
        res = api.get_recent_successful_runs()
        self.assertEqual(3, len(res))
        self.assertIn(run_a.uuid, res)
        self.assertIn(run_b.uuid, res)
        self.assertIn(run_c.uuid, res)

    def test_get_recent_successful_runs_with_start_date(self):
        api.create_run(passes=1, run_at=datetime.datetime(
            1914, 6, 28, 10, 45, 0))
        run_b = api.create_run()
        run_c = api.create_run(passes=2)
        api.create_run(fails=1)
        res = api.get_recent_successful_runs(start_date=datetime.datetime(
            1918, 11, 11, 11, 11, 11))
        self.assertEqual(2, len(res))
        self.assertIn(run_b.uuid, res)
        self.assertIn(run_c.uuid, res)

    def test_get_test_counts_in_date_range_as_str(self):
        timestamp_str_a = 'Dec 01 2015'
        timestamp_str_b = 'Dec 20 2015'
        timestamp_a = datetime.datetime(2015, 12, 2, 10, 00, 00)
        timestamp_b = timestamp_a + datetime.timedelta(minutes=10)
        timestamp_c = timestamp_a + datetime.timedelta(minutes=20)
        timestamp_d = datetime.datetime(2015, 12, 22, 10, 00, 00)
        run_a = api.create_run()
        run_b = api.create_run()
        run_c = api.create_run()
        run_d = api.create_run()
        test = api.create_test('fake_test')
        api.create_test_run(test.id, run_a.id, 'success',
                            timestamp_a, timestamp_b)
        api.create_test_run(test.id, run_b.id, 'fail',
                            timestamp_a, timestamp_c)
        api.create_test_run(test.id, run_c.id, 'success',
                            timestamp_a, timestamp_d)
        api.create_test_run(test.id, run_d.id, 'skip',
                            timestamp_c, timestamp_d)
        res = api.get_test_counts_in_date_range(test.id,
                                                timestamp_str_a,
                                                timestamp_str_b)
        self.assertEqual(1, res['success'])
        self.assertEqual(1, res['failure'])
        self.assertEqual(0, res['skips'])

    def test_get_test_counts_in_date_range(self):
        timestamp_a = datetime.datetime(2015, 12, 2, 10, 00, 00)
        timestamp_b = timestamp_a + datetime.timedelta(minutes=10)
        timestamp_c = timestamp_a + datetime.timedelta(minutes=20)
        timestamp_d = datetime.datetime(2015, 12, 22, 10, 00, 00)
        timerange_a = datetime.datetime(2015, 12, 1)
        timerange_b = datetime.datetime(2015, 12, 20)
        run_a = api.create_run()
        run_b = api.create_run()
        run_c = api.create_run()
        run_d = api.create_run()
        test = api.create_test('fake_test')
        api.create_test_run(test.id, run_a.id, 'success',
                            timestamp_a, timestamp_b)
        api.create_test_run(test.id, run_b.id, 'fail',
                            timestamp_a, timestamp_c)
        api.create_test_run(test.id, run_c.id, 'success',
                            timestamp_a, timestamp_d)
        api.create_test_run(test.id, run_d.id, 'skip',
                            timestamp_c, timestamp_d)
        res = api.get_test_counts_in_date_range(test.id,
                                                timerange_a,
                                                timerange_b)
        self.assertEqual(1, res['success'])
        self.assertEqual(1, res['failure'])
        self.assertEqual(0, res['skips'])

    def test_get_failing_test_ids_from_runs_by_key_value(self):
        test_a = api.create_test('fake_test')
        test_b = api.create_test('fake_test1')
        test_c = api.create_test('fake_test2')
        test_d = api.create_test('fake_test3')
        run_a = api.create_run()
        run_b = api.create_run()
        run_c = api.create_run()
        api.add_run_metadata({'a_key': 'a_value'}, run_a.id)
        api.add_run_metadata({'a_key': 'a_value'}, run_b.id)
        api.add_run_metadata({'a_key': 'b_value'}, run_c.id)
        api.create_test_run(test_a.id, run_a.id, 'fail')
        api.create_test_run(test_b.id, run_b.id, 'success')
        api.create_test_run(test_c.id, run_b.id, 'fail')
        api.create_test_run(test_d.id, run_c.id, 'fail')
        res = api.get_failing_test_ids_from_runs_by_key_value('a_key',
                                                              'a_value')
        self.assertEqual(2, len(res))
        self.assertIn(test_a.test_id, res)
        self.assertIn(test_c.test_id, res)

    def test_add_test_run_attachments(self):
        test = api.create_test('fake_test')
        run = api.create_run()
        test_run = api.create_test_run(test.id, run.id, 'success')
        attach_dict = {'attach_label': b'attach',
                       'attach_label_a': b'attach_a'}
        res = api.add_test_run_attachments(attach_dict, test_run.id)
        self.assertEqual(2, len(res))
        self.assertEqual(test_run.id, res[0].test_run_id)
        self.assertIn('attach_label', [x.label for x in res])
        self.assertIn('attach_label_a', [x.label for x in res])
        self.assertIn(b'attach', [x.attachment for x in res])
        self.assertIn(b'attach_a', [x.attachment for x in res])

    def test_get_ids_for_all_tests(self):
        test_a = api.create_test('fake_test')
        test_b = api.create_test('fake_test1')
        test_c = api.create_test('fake_test2')
        res = api.get_ids_for_all_tests()
        self.assertIsInstance(res, types.GeneratorType)
        res = list(res)
        self.assertIn((test_c.id,), res)
        self.assertIn((test_b.id,), res)
        self.assertIn((test_a.id,), res)
