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
import datetime
from dateutil import parser as date_parser
import fixtures
import mock
from oslo_config import cfg
import sys
import tempfile
import testtools

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
                                                  non_subunit_name=None,
                                                  targets=[],
                                                  use_wall_time=False)
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
                                             non_subunit_name=None,
                                             targets=[],
                                             use_wall_time=False)
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
            non_subunit_name=None,
            targets=[mock.sentinel.extension],
            use_wall_time=False)
        process_results_mock.assert_called_once_with(fake_get_results)


class TestProcessResults(base.TestCase):

    def setUp(self):
        super(TestProcessResults, self).setUp()
        cfg.CONF.reset()
        shell.cli_opts()
        # Ensure the config defaults are what we need
        cfg.CONF.set_override(name='run_at', override=None)
        cfg.CONF.set_override(name='artifacts', override=None)
        cfg.CONF.set_override(name='run_id', override=None)
        # Mock the whole subunit2sql.db.api module
        self.db_api_mock = self.useFixture(fixtures.MockPatch(
            'subunit2sql.shell.api')).mock
        # Mock session
        self.fake_session = mock.Mock(name='session', spec=['close'])
        self.db_api_mock.get_session.return_value = self.fake_session
        # Mock get_run_totals
        self.fake_totals = dict(skips=11, fails=22, success=33)
        self.get_run_totals_mock = self.useFixture(
            fixtures.MockPatch('subunit2sql.shell.get_run_totals',
                               return_value=self.fake_totals)).mock

    def test_process_results_no_results(self):
        fake_run_time = 'run time'
        fake_results = dict(run_time=fake_run_time)
        fake_db_run_id = 'run id'
        fake_db_run = mock.Mock(name='db run')
        fake_db_run.id = fake_db_run_id
        self.db_api_mock.create_run.return_value = fake_db_run

        # Setup Configuration
        fake_run_at = '2016-08-17 10:58:00.000'
        cfg.CONF.set_override(name='run_at', override=fake_run_at)
        fake_artifacts = 'artifacts'
        cfg.CONF.set_override(name='artifacts', override=fake_artifacts)
        fake_run_id = 'run_id'
        cfg.CONF.set_override(name='run_id', override=fake_run_id)
        fake_run_meta = {'run_meta': 'value'}
        cfg.CONF.set_override(name='run_meta', override=fake_run_meta)
        # Run process_results
        shell.process_results(fake_results)
        self.db_api_mock.get_session.assert_called_once()
        expected_run_at = date_parser.parse(fake_run_at)
        self.db_api_mock.create_run.assert_called_once_with(
            self.fake_totals['skips'], self.fake_totals['fails'],
            self.fake_totals['success'], fake_run_time, fake_artifacts,
            id=fake_run_id, run_at=expected_run_at, session=self.fake_session)
        self.db_api_mock.add_run_metadata.assert_called_once_with(
            fake_run_meta, fake_db_run_id, self.fake_session)
        self.fake_session.close.assert_called_once()

    @mock.patch('subunit2sql.read_subunit.get_duration')
    def test_process_results_new_tests(self, get_duration_mock):
        fake_run_time = 'run time'
        fake_results = dict(test1={'status': 'success', 'start_time': 0,
                                   'end_time': 1, 'metadata': None,
                                   'attachments': None},
                            test2={'status': 'fail', 'start_time': 0,
                                   'end_time': 2, 'metadata': None,
                                   'attachments': None},
                            test3={'status': 'skip', 'start_time': 0,
                                   'end_time': 3, 'metadata': None,
                                   'attachments': None})
        fake_results_all = copy.deepcopy(fake_results)
        fake_results_all['run_time'] = fake_run_time
        # Mock create_run
        fake_db_run_id = 'run id'
        fake_db_run = mock.Mock(name='db run')
        fake_db_run.id = fake_db_run_id
        self.db_api_mock.create_run.return_value = fake_db_run
        # Tests are not found in the DB
        self.db_api_mock.get_test_by_test_id.return_value = None
        # Mock create test
        get_duration_mock.return_value = 'fake_duration'
        fake_db_test_id = 'test_db_id'
        fake_test_create = mock.Mock(name='db test')
        fake_test_create.id = fake_db_test_id
        self.db_api_mock.create_test.return_value = fake_test_create
        # Run process_results
        shell.process_results(fake_results_all)
        # Check that we lookup all tests in the DB
        expected_test_by_id_calls = [mock.call(x, self.fake_session) for x in
                                     fake_results]
        self.db_api_mock.get_test_by_test_id.assert_has_calls(
            expected_test_by_id_calls, any_order=True)
        # Check that all tests are created in the DB
        expected_create_test_calls = [
            mock.call('test1', 1, 1, 0, 'fake_duration', self.fake_session),
            mock.call('test2', 1, 0, 1, 'fake_duration', self.fake_session),
            mock.call('test3', 0, 0, 0, 'fake_duration', self.fake_session)]
        self.db_api_mock.create_test.assert_has_calls(
            expected_create_test_calls, any_order=True)
        # Check that a test_run for each test is created in the DB
        expected_create_test_run_calls = [
            mock.call(fake_db_test_id, fake_db_run_id,
                      fake_results[x]['status'], fake_results[x]['start_time'],
                      fake_results[x]['end_time'], self.fake_session)
            for x in fake_results]
        self.db_api_mock.create_test_run.assert_has_calls(
            expected_create_test_run_calls, any_order=True)
        self.fake_session.close.assert_called_once()

    @mock.patch('subunit2sql.shell.running_avg')
    def test_process_results_existing_tests(self, running_avg_mock):
        fake_run_time = 'run time'
        # Setup a common fake DB test
        fake_db_test = mock.Mock(name='db test')
        fake_db_test.id = 'test id'
        fake_db_test.run_count = 3
        fake_db_test.success = 2
        fake_db_test.failure = 1
        # Setup results
        fake_results = dict(test1={'status': 'success', 'start_time': 0,
                                   'end_time': 1, 'metadata': None,
                                   'attachments': None},
                            test2={'status': 'fail', 'start_time': 0,
                                   'end_time': 2, 'metadata': None,
                                   'attachments': None},
                            test3={'status': 'skip', 'start_time': 0,
                                   'end_time': 3, 'metadata': None,
                                   'attachments': None})
        fake_results_all = copy.deepcopy(fake_results)
        fake_results_all['run_time'] = fake_run_time
        # Mock create run
        fake_db_run_id = 'run id'
        fake_db_run = mock.Mock(name='db run')
        fake_db_run.id = fake_db_run_id
        self.db_api_mock.create_run.return_value = fake_db_run
        # Tests are found in the DB
        self.db_api_mock.get_test_by_test_id.return_value = fake_db_test
        # Mock running avg
        fake_running_avg = 'running average'

        def fake_running_avg_method(test, values, result):
            values['run_time'] = fake_running_avg
            return values

        running_avg_mock.side_effect = fake_running_avg_method

        # Run process_results
        shell.process_results(fake_results_all)
        # Check that we lookup all tests in the DB
        expected_test_by_id_calls = [mock.call(x, self.fake_session) for x in
                                     fake_results]
        self.db_api_mock.get_test_by_test_id.assert_has_calls(
            expected_test_by_id_calls, any_order=True)
        # Check that counters for tests are updated (if not skip)
        expected_update_test_calls = [
            mock.call({'run_count': 4, 'success': 3,
                       'run_time': fake_running_avg},
                      fake_db_test.id, self.fake_session),
            mock.call({'run_count': 4, 'failure': 2},
                      fake_db_test.id, self.fake_session)]
        self.db_api_mock.update_test.assert_has_calls(
            expected_update_test_calls, any_order=True)
        # Check that a test_run for each test is created in the DB
        expected_create_test_run_calls = [
            mock.call(fake_db_test.id, fake_db_run_id,
                      fake_results[x]['status'],
                      fake_results[x]['start_time'],
                      fake_results[x]['end_time'], self.fake_session)
            for x in fake_results]
        self.db_api_mock.create_test_run.assert_has_calls(
            expected_create_test_run_calls, any_order=True)
        self.fake_session.close.assert_called_once()

    def test_process_results_existing_tests_invalid_status(self):
        fake_run_time = 'run time'
        # Setup a common fake DB test
        fake_db_test = mock.Mock(name='db test')
        fake_db_test.run_count = 3
        # Setup results
        fake_results = dict(test1={'status': 'invalid', 'start_time': 0,
                                   'end_time': 1, 'metadata': None,
                                   'attachments': None})
        fake_results_all = copy.deepcopy(fake_results)
        fake_results_all['run_time'] = fake_run_time
        # Tests are found in the DB
        self.db_api_mock.get_test_by_test_id.return_value = fake_db_test
        with testtools.ExpectedException(exceptions.UnknownStatus,
                                         '^.*\n.*%s$' % 'invalid'):
            # Run process_results
            shell.process_results(fake_results_all)
        # Check that we lookup all tests in the DB
        expected_test_by_id_calls = [mock.call(x, self.fake_session) for x in
                                     fake_results]
        self.db_api_mock.get_test_by_test_id.assert_has_calls(
            expected_test_by_id_calls, any_order=True)
        # Check that a run is created in the DB
        self.db_api_mock.create_run.assert_called_once_with(
            self.fake_totals['skips'], self.fake_totals['fails'],
            self.fake_totals['success'], fake_run_time, None, id=None,
            run_at=None, session=self.fake_session)
        # Check no test run was added to the DB
        self.db_api_mock.create_test_run.assert_not_called()
        # FIXME(andreaf) Session is not closed.
        # https://storyboard.openstack.org/?#!/story/2000702
        # self.fake_session.close.assert_called_once()

    def test_process_results_test_metadata_new(self):
        # Setup the metadata prefix configuration
        fake_meta_prefix = '_meta_'
        cfg.CONF.set_override(name='test_attr_prefix',
                              override=fake_meta_prefix)
        fake_run_time = 'run time'
        # Setup a common fake DB test
        fake_db_test = mock.Mock(name='db test')
        fake_db_test.id = 'test id'
        fake_db_test.run_count = 3
        fake_db_test.success = 2
        fake_db_test.failure = 1
        # Setup results
        expected_metadata_list = [fake_meta_prefix + 'a',
                                  fake_meta_prefix + 'b']
        extra_metadata_list = ['c', 'd']
        full_metadata_list = expected_metadata_list + extra_metadata_list
        fake_results = dict(
            test1={'status': 'fail', 'start_time': 0, 'end_time': 1,
                   'metadata': {'attrs': ','.join(full_metadata_list)},
                   'attachments': None})
        fake_results_all = copy.deepcopy(fake_results)
        fake_results_all['run_time'] = fake_run_time
        # Mock create run
        fake_db_run_id = 'run id'
        fake_db_run = mock.Mock(name='db run')
        fake_db_run.id = fake_db_run_id
        self.db_api_mock.create_run.return_value = fake_db_run
        # Mock create test run
        fake_db_test_run_id = 'test run id'
        fake_db_test_run = mock.Mock(name='db test run')
        fake_db_test_run.id = fake_db_test_run_id
        self.db_api_mock.create_test_run.return_value = fake_db_test_run
        # Tests are found in the DB
        self.db_api_mock.get_test_by_test_id.return_value = fake_db_test
        # Test metadata is not found in the DB
        self.db_api_mock.get_test_metadata.return_value = []
        # Run process_results
        shell.process_results(fake_results_all)
        # Check only matching metadata is added to test_metadata
        expected_add_test_metadata_calls = [
            mock.call({'attr': x}, fake_db_test.id, session=self.fake_session)
            for x in expected_metadata_list]
        self.db_api_mock.add_test_metadata.assert_has_calls(
            expected_add_test_metadata_calls, any_order=True)
        # Check all metadata is added to test_run_metadata
        self.db_api_mock.add_test_run_metadata.assert_has_calls([
            mock.call(fake_results['test1']['metadata'], fake_db_test_run_id,
                      self.fake_session)])
        self.fake_session.close.assert_called_once()

    def test_process_results_test_metadata_existing(self):
        # Setup the metadata prefix configuration
        fake_meta_prefix = '_meta_'
        cfg.CONF.set_override(name='test_attr_prefix',
                              override=fake_meta_prefix)
        fake_run_time = 'run time'
        # Setup a common fake DB test
        fake_db_test = mock.Mock(name='db test')
        fake_db_test.id = 'test id'
        fake_db_test.run_count = 3
        fake_db_test.success = 2
        fake_db_test.failure = 1
        # Setup results
        expected_metadata_list = [fake_meta_prefix + 'a',
                                  fake_meta_prefix + 'b']
        existing_metadata_list = [fake_meta_prefix + 'c',
                                  fake_meta_prefix + 'd']
        full_metadata_list = expected_metadata_list + existing_metadata_list
        fake_results = dict(
            test1={'status': 'fail', 'start_time': 0, 'end_time': 1,
                   'metadata': {'attrs': ','.join(full_metadata_list)},
                   'attachments': None})
        fake_results_all = copy.deepcopy(fake_results)
        fake_results_all['run_time'] = fake_run_time
        # Mock create run
        fake_db_run_id = 'run id'
        fake_db_run = mock.Mock(name='db run')
        fake_db_run.id = fake_db_run_id
        self.db_api_mock.create_run.return_value = fake_db_run
        # Mock create test run
        fake_db_test_run_id = 'test run id'
        fake_db_test_run = mock.Mock(name='db test run')
        fake_db_test_run.id = fake_db_test_run_id
        self.db_api_mock.create_test_run.return_value = fake_db_test_run
        # Tests are found in the DB
        self.db_api_mock.get_test_by_test_id.return_value = fake_db_test
        # Test metadata is found in the DB
        test_metadata_list = []
        for value in existing_metadata_list:
            test_metadata = mock.Mock()
            test_metadata.key = 'attr'
            test_metadata.value = value
            test_metadata_list.append(test_metadata)
        self.db_api_mock.get_test_metadata.return_value = test_metadata_list
        # Run process_results
        shell.process_results(fake_results_all)
        # Check only matching metadata is added to test_metadata
        expected_add_test_metadata_calls = [
            mock.call({'attr': x}, fake_db_test.id, session=self.fake_session)
            for x in expected_metadata_list]
        self.db_api_mock.add_test_metadata.assert_has_calls(
            expected_add_test_metadata_calls, any_order=True)
        # Check all metadata is added to test_run_metadata
        self.db_api_mock.add_test_run_metadata.assert_has_calls([
            mock.call(fake_results['test1']['metadata'], fake_db_test_run_id,
                      self.fake_session)])
        self.fake_session.close.assert_called_once()

    def test_process_result_test_metadata_no_prefix(self):
        # Setup the metadata prefix configuration
        cfg.CONF.set_override(name='test_attr_prefix',
                              override='')
        fake_run_time = 'run time'
        # Setup a common fake DB test
        fake_db_test = mock.Mock(name='db test')
        fake_db_test.id = 'test id'
        fake_db_test.run_count = 3
        fake_db_test.success = 2
        fake_db_test.failure = 1
        # Setup results
        expected_metadata_list = ['a', 'b', 'c']
        fake_results = dict(
            test1={'status': 'fail', 'start_time': 0, 'end_time': 1,
                   'metadata': {'attrs': ','.join(expected_metadata_list)},
                   'attachments': None})
        fake_results_all = copy.deepcopy(fake_results)
        fake_results_all['run_time'] = fake_run_time
        # Mock create run
        fake_db_run_id = 'run id'
        fake_db_run = mock.Mock(name='db run')
        fake_db_run.id = fake_db_run_id
        self.db_api_mock.create_run.return_value = fake_db_run
        # Mock create test run
        fake_db_test_run_id = 'test run id'
        fake_db_test_run = mock.Mock(name='db test run')
        fake_db_test_run.id = fake_db_test_run_id
        self.db_api_mock.create_test_run.return_value = fake_db_test_run
        # Tests are found in the DB
        self.db_api_mock.get_test_by_test_id.return_value = fake_db_test
        # Run process_results
        shell.process_results(fake_results_all)
        # Check test metadata is not added
        self.db_api_mock.add_test_metadata.assert_not_called()
        # Check all metadata is added to test_run_metadata
        self.db_api_mock.add_test_run_metadata.assert_has_calls([
            mock.call(fake_results['test1']['metadata'],
                      fake_db_test_run_id,
                      self.fake_session)])
        self.fake_session.close.assert_called_once()

    def test_process_result_test_run_attachments(self):
        fake_run_time = 'run time'
        # Setup a common fake DB test
        fake_db_test = mock.Mock(name='db test')
        fake_db_test.id = 'test id'
        fake_db_test.run_count = 3
        fake_db_test.success = 2
        fake_db_test.failure = 1
        # Setup results
        fake_attachment = 'some text'
        fake_results = dict(
            test1={'status': 'fail', 'start_time': 0, 'end_time': 1,
                   'metadata': None, 'attachments': fake_attachment})
        fake_results_all = copy.deepcopy(fake_results)
        fake_results_all['run_time'] = fake_run_time
        # Mock create run
        fake_db_run_id = 'run id'
        fake_db_run = mock.Mock(name='db run')
        fake_db_run.id = fake_db_run_id
        self.db_api_mock.create_run.return_value = fake_db_run
        # Mock create test run
        fake_db_test_run_id = 'test run id'
        fake_db_test_run = mock.Mock(name='db test run')
        fake_db_test_run.id = fake_db_test_run_id
        self.db_api_mock.create_test_run.return_value = fake_db_test_run
        # Tests are found in the DB
        self.db_api_mock.get_test_by_test_id.return_value = fake_db_test
        # Run process_results
        shell.process_results(fake_results_all)
        # Check attachments are added to the test run
        self.db_api_mock.add_test_metadata.assert_not_called()
        # Check all metadata is added to test_run_metadata
        self.db_api_mock.add_test_run_attachments.assert_has_calls([
            mock.call(fake_attachment, fake_db_test_run_id,
                      self.fake_session)])
        self.fake_session.close.assert_called_once()

    def test_process_results_test_metadata_new_remove_prefix(self):
        # Setup the metadata prefix configuration
        fake_meta_prefix = '_meta_'
        cfg.CONF.set_override(name='test_attr_prefix',
                              override=fake_meta_prefix)
        cfg.CONF.set_override(name='remove_test_attr_prefix',
                              override=True)
        fake_run_time = 'run time'
        # Setup a common fake DB test
        fake_db_test = mock.Mock(name='db test')
        fake_db_test.id = 'test id'
        fake_db_test.run_count = 3
        fake_db_test.success = 2
        fake_db_test.failure = 1
        # Setup results
        expected_metadata_list = ['a', 'b']
        extra_metadata_list = ['c', 'd']
        full_metadata_list = [fake_meta_prefix + x for x in
                              expected_metadata_list] + extra_metadata_list
        fake_results = dict(
            test1={'status': 'fail', 'start_time': 0, 'end_time': 1,
                   'metadata': {'attrs': ','.join(full_metadata_list)},
                   'attachments': None})
        fake_results_all = copy.deepcopy(fake_results)
        fake_results_all['run_time'] = fake_run_time
        # Mock create run
        fake_db_run_id = 'run id'
        fake_db_run = mock.Mock(name='db run')
        fake_db_run.id = fake_db_run_id
        self.db_api_mock.create_run.return_value = fake_db_run
        # Mock create test run
        fake_db_test_run_id = 'test run id'
        fake_db_test_run = mock.Mock(name='db test run')
        fake_db_test_run.id = fake_db_test_run_id
        self.db_api_mock.create_test_run.return_value = fake_db_test_run
        # Tests are found in the DB
        self.db_api_mock.get_test_by_test_id.return_value = fake_db_test
        # Test metadata is not found in the DB
        self.db_api_mock.get_test_metadata.return_value = []
        # Run process_results
        shell.process_results(fake_results_all)
        # Check only matching metadata is added to test_metadata
        expected_add_test_metadata_calls = [
            mock.call({'attr': x}, fake_db_test.id, session=self.fake_session)
            for x in expected_metadata_list]
        self.db_api_mock.add_test_metadata.assert_has_calls(
            expected_add_test_metadata_calls, any_order=True)
        # Check all metadata is added to test_run_metadata
        self.db_api_mock.add_test_run_metadata.assert_has_calls([
            mock.call(fake_results['test1']['metadata'], fake_db_test_run_id,
                      self.fake_session)])
        self.fake_session.close.assert_called_once()

    def test_process_results_test_metadata_existing_remove_prefix(self):
        # Setup the metadata prefix configuration
        fake_meta_prefix = '_meta_'
        cfg.CONF.set_override(name='test_attr_prefix',
                              override=fake_meta_prefix)
        cfg.CONF.set_override(name='remove_test_attr_prefix',
                              override=True)
        fake_run_time = 'run time'
        # Setup a common fake DB test
        fake_db_test = mock.Mock(name='db test')
        fake_db_test.id = 'test id'
        fake_db_test.run_count = 3
        fake_db_test.success = 2
        fake_db_test.failure = 1
        # Setup results
        expected_metadata_list = ['a', 'b']
        existing_metadata_list = ['c', 'd']
        full_metadata_list = [fake_meta_prefix + x for x in (
            expected_metadata_list + existing_metadata_list)]
        fake_results = dict(
            test1={'status': 'fail', 'start_time': 0, 'end_time': 1,
                   'metadata': {'attrs': ','.join(full_metadata_list)},
                   'attachments': None})
        fake_results_all = copy.deepcopy(fake_results)
        fake_results_all['run_time'] = fake_run_time
        # Mock create run
        fake_db_run_id = 'run id'
        fake_db_run = mock.Mock(name='db run')
        fake_db_run.id = fake_db_run_id
        self.db_api_mock.create_run.return_value = fake_db_run
        # Mock create test run
        fake_db_test_run_id = 'test run id'
        fake_db_test_run = mock.Mock(name='db test run')
        fake_db_test_run.id = fake_db_test_run_id
        self.db_api_mock.create_test_run.return_value = fake_db_test_run
        # Tests are found in the DB
        self.db_api_mock.get_test_by_test_id.return_value = fake_db_test
        # Test metadata is found in the DB
        test_metadata_list = []
        for value in existing_metadata_list:
            test_metadata = mock.Mock()
            test_metadata.key = 'attr'
            test_metadata.value = value
            test_metadata_list.append(test_metadata)
        self.db_api_mock.get_test_metadata.return_value = test_metadata_list
        # Run process_results
        shell.process_results(fake_results_all)
        # Check only matching metadata is added to test_metadata
        expected_add_test_metadata_calls = [
            mock.call({'attr': x}, fake_db_test.id, session=self.fake_session)
            for x in expected_metadata_list]
        self.db_api_mock.add_test_metadata.assert_has_calls(
            expected_add_test_metadata_calls, any_order=True)
        # Check all metadata is added to test_run_metadata
        self.db_api_mock.add_test_run_metadata.assert_has_calls([
            mock.call(fake_results['test1']['metadata'], fake_db_test_run_id,
                      self.fake_session)])
        self.fake_session.close.assert_called_once()
