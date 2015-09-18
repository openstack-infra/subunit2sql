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

import datetime

import mock

from subunit2sql import exceptions
from subunit2sql import shell
from subunit2sql.tests import base


class TestShell(base.TestCase):
    def test_run_totals(self):
        fake_results = {}
        # Fake Success
        for num in range(100):
            test_name = 'fake_test_' + str(num)
            fake_results[test_name] = {'status': 'success'}
        # Fake skips
        for num in range(50):
            test_name = 'fake_test_skip_' + str(num)
            fake_results[test_name] = {'status': 'skip'}
        # Fake skips
        for num in range(16):
            test_name = 'fake_test_fail_' + str(num)
            fake_results[test_name] = {'status': 'fail'}
        totals = shell.get_run_totals(fake_results)
        self.assertEqual(totals['success'], 100)
        self.assertEqual(totals['fails'], 16)
        self.assertEqual(totals['skips'], 50)

    def test_running_avg(self):
        fake_test = mock.MagicMock()
        fake_test.success = 150
        fake_test.run_time = 30.452
        fake_result = {
            'start_time': datetime.datetime(1914, 6, 28, 10, 45, 0),
            'end_time': datetime.datetime(1914, 6, 28, 10, 45, 50),
        }
        fake_values = {}
        result = shell.running_avg(fake_test, fake_values, fake_result)
        # Let's do some arithmetic
        expected_avg = ((150 * 30.452) + 50) / 151
        # Both values should be 30.581456953642384
        self.assertEqual(expected_avg, result['run_time'])

    def test_running_avg_no_prev(self):
        fake_test = mock.MagicMock()
        fake_test.success = 1
        fake_test.run_time = None
        fake_result = {
            'start_time': datetime.datetime(1914, 6, 28, 10, 45, 0),
            'end_time': datetime.datetime(1914, 6, 28, 10, 45, 50),
        }
        fake_values = {}
        result = shell.running_avg(fake_test, fake_values, fake_result)
        expected_avg = 50
        self.assertEqual(expected_avg, result['run_time'])

    def test_increment_counts_success(self):
        fake_test = mock.MagicMock()
        fake_test.run_count = 15
        fake_test.success = 5
        fake_test.run_time = 45.0
        fake_result = {
            'status': 'success',
            'start_time': datetime.datetime(1914, 6, 28, 10, 45, 0),
            'end_time': datetime.datetime(1914, 6, 28, 10, 45, 50),
        }
        values = shell.increment_counts(fake_test, fake_result)
        # Check to ensure counts incremented properly
        self.assertEqual(values['run_count'], 16)
        self.assertEqual(values['success'], 6)
        # Ensure run_time is updated on success
        expected_avg = ((5 * 45.0) + 50) / 6
        self.assertEqual(values['run_time'], expected_avg)

    def test_increment_counts_failure(self):
        fake_test = mock.MagicMock()
        fake_test.run_count = 15
        fake_test.success = 5
        fake_test.failure = 10
        fake_test.run_time = 45.0
        fake_result = {
            'status': 'fail',
            'start_time': datetime.datetime(1914, 6, 28, 10, 45, 0),
            'end_time': datetime.datetime(1914, 6, 28, 10, 45, 50),
        }
        values = shell.increment_counts(fake_test, fake_result)
        # Check to ensure counts incremented properly
        self.assertEqual(values['run_count'], 16)
        self.assertEqual(values['failure'], 11)
        # Avg runtime should only be updated on success
        self.assertNotIn('run_time', values)

    def test_increment_counts_skip(self):
        fake_test = mock.MagicMock()
        fake_test.run_count = 15
        fake_test.success = 5
        fake_test.failure = 10
        fake_test.run_time = 45.0
        fake_result = {
            'status': 'skip',
            'start_time': datetime.datetime(1914, 6, 28, 10, 45, 0),
            'end_time': datetime.datetime(1914, 6, 28, 10, 45, 2),
        }
        values = shell.increment_counts(fake_test, fake_result)
        # No test counts incremented with a skip
        self.assertEqual(values, {})

    def test_increment_counts_unknown_status(self):
        fake_test = mock.MagicMock()
        fake_result = {
            'status': 'explody',
            'start_time': datetime.datetime(1914, 6, 28, 10, 45, 0),
            'end_time': datetime.datetime(1914, 6, 28, 10, 45, 2),
        }
        self.assertRaises(exceptions.UnknownStatus,
                          shell.increment_counts, fake_test, fake_result)
