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
import sys
import tempfile

import fixtures
import mock
from oslo_config import cfg

from subunit2sql import exceptions
from subunit2sql.migrations import cli as migration_cli
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


class TestMain(base.TestCase):
    def setUp(self):
        super(TestMain, self).setUp()
        cfg.CONF.reset()
        cfg.CONF.unregister_opt(migration_cli.command_opt)
        self.fake_args = ['subunit2sql']
        self.useFixture(fixtures.MonkeyPatch('sys.argv', self.fake_args))

    @mock.patch('subunit2sql.read_subunit.ReadSubunit')
    @mock.patch('subunit2sql.shell.process_results')
    def test_main(self, process_results_mock, read_subunit_mock):
        fake_read_subunit = mock.MagicMock('ReadSubunit')
        fake_get_results = 'fake results'
        fake_read_subunit.get_results = mock.MagicMock('get_results')
        fake_read_subunit.get_results.return_value = fake_get_results
        read_subunit_mock.return_value = fake_read_subunit
        shell.main()
        read_subunit_mock.assert_called_once_with(sys.stdin,
                                                  attachments=False,
                                                  attr_regex='\[(.*)\]',
                                                  targets=[])
        process_results_mock.assert_called_once_with(fake_get_results)

    @mock.patch('subunit2sql.read_subunit.ReadSubunit')
    @mock.patch('subunit2sql.shell.process_results')
    def test_main_multiple_files(self, process_results_mock,
                                 read_subunit_mock):
        tfile1 = tempfile.NamedTemporaryFile()
        tfile2 = tempfile.NamedTemporaryFile()
        tfile1.write(b'test me later 1')
        tfile2.write(b'test me later 2')
        tfile1.flush()
        tfile2.flush()
        self.fake_args.extend([tfile1.name, tfile2.name])
        fake_read_subunit = mock.MagicMock('ReadSubunit')
        fake_get_results_1 = 'fake results 1'
        fake_get_results_2 = 'fake results 2'
        fake_read_subunit.get_results = mock.MagicMock('get_results')
        fake_read_subunit.get_results.side_effect = [fake_get_results_1,
                                                     fake_get_results_2]
        read_subunit_mock.return_value = fake_read_subunit
        shell.main()
        read_subunit_mock.assert_called_with(mock.ANY,
                                             attachments=False,
                                             attr_regex='\[(.*)\]',
                                             targets=[])
        self.assertEqual(2, len(read_subunit_mock.call_args_list))
        file_1 = read_subunit_mock.call_args_list[0][0][0]
        file_1.seek(0)
        self.assertEqual('test me later 1', file_1.read())
        file_2 = read_subunit_mock.call_args_list[1][0][0]
        file_2.seek(0)
        self.assertEqual('test me later 2', file_2.read())
        self.assertEqual(fake_get_results_1,
                         process_results_mock.call_args_list[0][0][0])
        self.assertEqual(fake_get_results_2,
                         process_results_mock.call_args_list[1][0][0])

    @mock.patch('stevedore.enabled.EnabledExtensionManager')
    @mock.patch('subunit2sql.read_subunit.ReadSubunit')
    @mock.patch('subunit2sql.shell.process_results')
    def test_main_with_targets(self, process_results_mock, read_subunit_mock,
                               ext_mock):
        exts = mock.MagicMock('EnabledExtensionManager()')
        ext_mock.return_value = exts
        exts.map = mock.MagicMock('extensions.map')
        exts.map.return_value = [mock.sentinel.extension]
        fake_read_subunit = mock.MagicMock('ReadSubunit')
        fake_get_results = 'fake results'
        fake_read_subunit.get_results = mock.MagicMock('get_results')
        fake_read_subunit.get_results.return_value = fake_get_results
        read_subunit_mock.return_value = fake_read_subunit
        shell.main()
        read_subunit_mock.assert_called_once_with(
            sys.stdin, attachments=False, attr_regex='\[(.*)\]',
            targets=[mock.sentinel.extension])
        process_results_mock.assert_called_once_with(fake_get_results)
