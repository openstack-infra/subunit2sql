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

import os
import os.path
import tempfile

from oslo_config import cfg
from oslo_config import fixture

from subunit2sql.targets import localdir
from subunit2sql.tests import base


class TestLocaldir(base.TestCase):
    def setUp(self):
        super(TestLocaldir, self).setUp()
        self.useFixture(fixture.Config(cfg.CONF))
        self.tdir = tempfile.mkdtemp()
        cfg.CONF.set_override(name='attachments_storage_dir',
                              override=self.tdir)
        self.ad = localdir.AttachmentsDir()

    def test_localdir_enabled_when_configured(self):
        self.assertTrue(self.ad.enabled())

    def test_localdir_disabled_when_no_conf(self):
        cfg.CONF.clear_override(name='attachments_storage_dir')
        self.assertFalse(self.ad.enabled())

    def test_localdir_status_ignores_non_attachments(self):
        self.ad.status(test_id='foo.test',
                       test_status='melancholy')
        self.ad.stopTestRun()
        self.assertEqual(0, len(os.listdir(self.tdir)))

    def test_localdir_saves_testless_attachments(self):
        self.ad.status(file_name='super.txt',
                       file_bytes=b'the quick brown fox',
                       route_code='routecode1')
        self.ad.status(file_name='super.txt',
                       file_bytes=b'jumped over the lazy brown dog',
                       route_code='routecode2')
        self.ad.stopTestRun()
        expected_path = os.path.join(self.tdir, 'routecode1', 'super.txt')
        self.assertTrue(os.path.exists(expected_path))
        with open(expected_path, 'rb') as f:
            self.assertEqual(b'the quick brown fox', f.read())
        expected_path = os.path.join(self.tdir, 'routecode2', 'super.txt')
        self.assertTrue(os.path.exists(expected_path))
        with open(expected_path, 'rb') as f:
            self.assertEqual(b'jumped over the lazy brown dog', f.read())
