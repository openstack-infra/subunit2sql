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

    def test_create_test_run_and_list(self):
        run = api.create_run()
        test = api.create_test('fake_test')
        test_run = api.create_test_run(test.id, run.id, 'fail')
        self.assertIsNotNone(test_run)
        all_test_runs = api.get_all_test_runs()
        self.assertEqual(len(all_test_runs), 1)
        self.assertEqual(test_run.id, all_test_runs[0].id)
