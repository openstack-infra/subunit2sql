# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
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

from subunit2sql.tests import base
from subunit2sql import write_subunit

timestamp_a = datetime.datetime.utcnow()
timestamp_b = datetime.datetime.utcnow()


class TestWriteSubunit(base.TestCase):

    @mock.patch('subunit2sql.db.api.get_tests_run_dicts_from_run_id',
                return_value={'fake_test_id': {
                              'start_time': timestamp_a,
                              'stop_time': timestamp_b,
                              'status': 'success'}})
    @mock.patch('subunit2sql.write_subunit.write_test')
    @mock.patch('subunit2sql.db.api.get_session')
    def test_test_runs_without_metdata(self, api_mock, write_mock,
                                       sesion_mock):
        out = mock.MagicMock()
        write_subunit.sql2subunit('fake_id', out)
        self.assertEqual(write_mock.call_count, 1)
        args = write_mock.call_args_list[0][0]
        self.assertEqual(timestamp_a, args[1])
        self.assertEqual(timestamp_b, args[2])
        self.assertEqual('success', args[3])
        self.assertEqual('fake_test_id', args[4])
        self.assertEqual(None, args[5])

    @mock.patch('subunit2sql.db.api.get_tests_run_dicts_from_run_id',
                return_value={'fake_test_id': {
                    'start_time': timestamp_a,
                    'stop_time': timestamp_b,
                    'status': 'success',
                    'metadata': {
                        'key': 'value'}}})
    @mock.patch('subunit2sql.write_subunit.write_test')
    @mock.patch('subunit2sql.db.api.get_session')
    def test_test_runs_with_metdata(self, api_mock, write_mock, session_mock):
        out = mock.MagicMock()
        write_subunit.sql2subunit('fake_id', out)
        self.assertEqual(write_mock.call_count, 1)
        args = write_mock.call_args_list[0][0]
        self.assertEqual(timestamp_a, args[1])
        self.assertEqual(timestamp_b, args[2])
        self.assertEqual('success', args[3])
        self.assertEqual('fake_test_id', args[4])
        self.assertEqual({'key': 'value'}, args[5])
