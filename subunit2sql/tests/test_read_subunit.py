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
import io

import mock

from subunit2sql import read_subunit as subunit
from subunit2sql.tests import base


class TestReadSubunit(base.TestCase):
    def test_get_duration(self):
        dur = subunit.get_duration(datetime.datetime(1914, 6, 28, 10, 45, 0),
                                   datetime.datetime(1914, 6, 28, 10, 45, 50))
        self.assertEqual(dur, 50.000000)

    def test_get_duration_no_start(self):
        dur = subunit.get_duration(None,
                                   datetime.datetime(1914, 6, 28, 10, 45, 50))
        self.assertIsNone(dur)

    def test_get_duration_no_end(self):
        dur = subunit.get_duration(datetime.datetime(1914, 6, 28, 10, 45, 50),
                                   None)
        self.assertIsNone(dur)

    def test_get_attrs(self):
        fake_subunit = subunit.ReadSubunit(mock.MagicMock())
        fake_name = 'fake_dir.fake_module.fakeClass.test_fake[attr1,attr2]'
        attrs = fake_subunit.get_attrs(fake_name)
        self.assertEqual(attrs, 'attr1,attr2')

    def test_cleanup_test_name_with_attrs(self):
        fake_subunit = subunit.ReadSubunit(mock.MagicMock())
        fake_name = 'fake_dir.fake_module.fakeClass.test_fake[attr1,attr2]'
        name = fake_subunit.cleanup_test_name(fake_name)
        self.assertEqual(name, 'fake_dir.fake_module.fakeClass.test_fake')

    def test_cleanup_test_name_with_attrs_leave_scenarios(self):
        fake_subunit = subunit.ReadSubunit(mock.MagicMock())
        fake_name = ('fake_dir.fake_module.fakeClass.test_fake[attr1,attr2]'
                     '(scenario)')
        name = fake_subunit.cleanup_test_name(fake_name)
        self.assertEqual(name, 'fake_dir.fake_module.fakeClass.test_fake'
                         '(scenario)')

    def test_cleanup_test_name_with_strip_scenarios_and_attrs(self):
        fake_subunit = subunit.ReadSubunit(mock.MagicMock())
        fake_name = ('fake_dir.fake_module.fakeClass.test_fake[attr1,attr2]'
                     '(scenario)')
        name = fake_subunit.cleanup_test_name(fake_name, strip_scenarios=True)
        self.assertEqual(name, 'fake_dir.fake_module.fakeClass.test_fake')

    def test_cleanup_test_name_strip_nothing(self):
        fake_subunit = subunit.ReadSubunit(mock.MagicMock())
        fake_name = ('fake_dir.fake_module.fakeClass.test_fake[attr1,attr2]'
                     '(scenario)')
        name = fake_subunit.cleanup_test_name(fake_name, strip_tags=False)
        self.assertEqual(name, fake_name)

    def test_run_time(self):
        fake_subunit = subunit.ReadSubunit(mock.MagicMock())
        fake_results = {}
        fifty_sec_run_result = {
            'start_time': datetime.datetime(1914, 6, 28, 10, 45, 0),
            'end_time': datetime.datetime(1914, 6, 28, 10, 45, 50),
        }
        for num in range(100):
            test_name = 'test_fake_' + str(num)
            fake_results[test_name] = fifty_sec_run_result
        fake_subunit.results = fake_results
        runtime = fake_subunit.run_time()
        self.assertEqual(runtime, 5000.0)

    def test_parse_outcome(self):
        fake_subunit = subunit.ReadSubunit(mock.MagicMock())

        fake_id = 'fake_dir.fake_module.fakeClass.test_fake[attr1,attr2]'
        fake_timestamps = [datetime.datetime(1914, 8, 26, 20, 00, 00),
                           datetime.datetime(2014, 8, 26, 20, 00, 00)]
        fake_status = 'skip'
        tags = set(['worker-0'])

        fake_results = {
            'status': fake_status,
            'details': {
                'reason': 'fake reason'
            },
            'id': fake_id,
            'timestamps': fake_timestamps,
            'tags': tags
        }
        fake_subunit.parse_outcome(fake_results)

        parsed_results = fake_subunit.results
        # assert that the dict root key is the test name - the fake_id stripped
        # of the tags
        fake_test_name = fake_id[:fake_id.find('[')]
        self.assertEqual(list(parsed_results.keys()), [fake_test_name])

        self.assertEqual(parsed_results[fake_test_name]['status'],
                         fake_status)
        self.assertEqual(parsed_results[fake_test_name]['start_time'],
                         fake_timestamps[0])
        self.assertEqual(parsed_results[fake_test_name]['end_time'],
                         fake_timestamps[1])
        fake_attrs = fake_id[fake_id.find('[') + 1:fake_id.find(']')]
        self.assertEqual(parsed_results[fake_test_name]['metadata']['attrs'],
                         fake_attrs)
        self.assertEqual(parsed_results[fake_test_name]['metadata']['tags'],
                         ','.join(tags))

    def test_attrs_default_regex(self):
        fake_id = 'test_fake.TestThing.testA[good_test,fun_test,legit]'
        read = subunit.ReadSubunit(io.BytesIO())
        attrs = read.get_attrs(fake_id)
        attrs_list = attrs.split(',')
        self.assertIn('legit', attrs_list)
        self.assertIn('fun_test', attrs_list)
        self.assertIn('good_test', attrs_list)

    def test_attrs_non_default_regex(self):
        fake_id = 'test_fake.TestThing.testB`good_test,fun_test,legit`'
        regex = '\`(.*)\`'
        read = subunit.ReadSubunit(io.BytesIO(), attr_regex=regex)
        attrs = read.get_attrs(fake_id)
        attrs_list = attrs.split(',')
        self.assertIn('legit', attrs_list)
        self.assertIn('fun_test', attrs_list)
        self.assertIn('good_test', attrs_list)

    def test_attrs_no_matches(self):
        fake_id = 'test_fake.TestThing.testB`good_test,fun_test,legit`'
        read = subunit.ReadSubunit(io.BytesIO())
        attrs = read.get_attrs(fake_id)
        self.assertIsNone(attrs)

    def test_cleanup_test_name_default_attr_regex(self):
        fake_id = 'test_fake.TestThing.testA[good_test,fun_test,legit]'
        read = subunit.ReadSubunit(io.BytesIO())
        test_name = read.cleanup_test_name(fake_id, strip_tags=True,
                                           strip_scenarios=False)
        self.assertEqual('test_fake.TestThing.testA', test_name)

    def test_cleanup_test_name_non_default_attr_regex(self):
        fake_id = 'test_fake.TestThing.testB`good_test,fun_test,legit`'
        regex = '\`(.*)\`'
        read = subunit.ReadSubunit(io.BytesIO(), attr_regex=regex)
        test_name = read.cleanup_test_name(fake_id, strip_tags=True,
                                           strip_scenarios=False)
        self.assertEqual('test_fake.TestThing.testB', test_name)

    def test_cleanup_test_name_no_attr_matches(self):
        fake_id = 'test_fake.TestThing.testB`good_test,fun_test,legit`'
        read = subunit.ReadSubunit(io.BytesIO())
        test_name = read.cleanup_test_name(fake_id, strip_tags=True,
                                           strip_scenarios=False)
        self.assertEqual(fake_id, test_name)

    @mock.patch('testtools.CopyStreamResult')
    def test_targets_added_to_result(self, ttc_mock):
        subunit.ReadSubunit(mock.MagicMock(), targets=['foo'])
        self.assertIn('foo', ttc_mock.call_args[0][0])

    @mock.patch('testtools.CopyStreamResult')
    def test_targets_not_modified(self, ttc_mock):
        # A regression test that verifies that the subunit reader does
        # not modify the passed in value of targets.
        targets = ['foo']

        subunit.ReadSubunit(mock.MagicMock(), targets=targets)
        ntargets1 = len(ttc_mock.call_args[0][0])

        subunit.ReadSubunit(mock.MagicMock(), targets=targets)
        ntargets2 = len(ttc_mock.call_args[0][0])

        self.assertEqual(ntargets1, ntargets2)
        self.assertEqual(targets, ['foo'])
