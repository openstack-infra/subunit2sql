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
