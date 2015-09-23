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

import testscenarios

from subunit2sql.db import api
from subunit2sql.tests import base
from subunit2sql.tests import subunit2sql_fixtures as fixtures

load_tests = testscenarios.load_tests_apply_scenarios


class TestDatabaseAPI(base.TestCase):

    scenarios = [('mysql', {'dialect': 'mysql'})]

    def setUp(self):
        super(TestDatabaseAPI, self).setUp()
        self.useFixture(fixtures.LockFixture(self.dialect))
        if self.dialect == 'mysql':
            self.useFixture(fixtures.MySQLConfFixture())
        else:
            self.useFixture(fixtures.PostgresConfFixture())
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

    def test_get_test_runs_dicts_with_no_meta(self):
        run = api.create_run()
        test_a = api.create_test('fake_test')
        start_time = datetime.datetime.utcnow()
        stop_time = datetime.datetime.utcnow()
        api.create_test_run(test_a.id, run.id, 'success',
                            start_time, stop_time)
        test_run_dict = api.get_tests_run_dicts_from_run_id(run.id)
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
        test_run_dict = api.get_tests_run_dicts_from_run_id(run.id)
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
        test_run_dict = api.get_tests_run_dicts_from_run_id(run.id)
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
        test_run_dict = api.get_tests_run_dicts_from_run_id(run.id)
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
        test_run_dict = api.get_tests_run_dicts_from_run_id(run.id)
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
        test_run_dicts = api.get_tests_run_dicts_from_run_id(run.id)
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
        test_runs_a = api.get_test_runs_by_run_id(run_a.id)
        test_runs_b = api.get_test_runs_by_run_id(run_b.id)
        test_runs_c = api.get_test_runs_by_run_id(run_c.id)
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
        for i in range(20):
            if i % 2 == 1:
                fails = 10
            else:
                fails = 0
            year = 2010 + (i % 3)
            run_at = '%d-01-%02d 12:00:00' % (year, i + 1)
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
        for run_num in xrange(15):
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
        timestamp = runs_time_series.keys()[0]
        self.assertEqual(3, len(runs_time_series[timestamp]))
        for run_num in xrange(3):
            run_dict = {
                'skip': long(run_num),
                'fail': long(run_num + 1),
                'pass': long(run_num + 2),
                'id': unicode(runs[run_num].id),
                'run_time': 3.0,
                'metadata': {
                    u'test_key': u'fun',
                    u'non_test': u'value-%s' % run_num
                }
            }
            self.assertIn(run_dict, runs_time_series[timestamp])
        for run_num in range(3, 14):
            missing_run_dict = {
                'skip': long(run_num),
                'fail': long(run_num + 1),
                'pass': long(run_num + 2),
                'id': unicode(runs[run_num].id),
                'run_time': 3.0,
                'metadata': {
                    u'test_key': u'fun',
                    u'non_test': u'value-%s' % run_num
                }
            }
            self.assertNotIn(missing_run_dict, runs_time_series[timestamp])

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
