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

import os
import os.path
import tempfile

from oslo_config import cfg
import testtools

OPTIONS = [
    cfg.StrOpt('attachments_storage_dir', default=None,
               help='Any file attachments will be stored here')
]

cfg.CONF.register_cli_opts(OPTIONS)
cfg.CONF.register_opts(OPTIONS)


class AttachmentsDir(testtools.StreamResult):
    @classmethod
    def enabled(self):
        if not cfg.CONF.attachments_storage_dir:
            return False
        if not os.path.isdir(cfg.CONF.attachments_storage_dir):
            return False
        return True

    def __init__(self):
        self.pending_files = {}

    def status(self, test_id=None, test_status=None, test_tags=None,
               runnable=True, file_name=None, file_bytes=None, eof=False,
               mime_type=None, route_code=None, timestamp=None):
        if not file_name or not file_bytes:
            return
        target_dirs = []
        if route_code:
            target_dirs.append(route_code)
        if test_id:
            target_dirs.append(test_id)
        target_dir = os.path.join(cfg.CONF.attachments_storage_dir,
                                  *target_dirs)
        os.makedirs(target_dir)
        target_file_path = os.path.join(target_dir, file_name)
        if target_file_path not in self.pending_files:
            self.pending_files[target_file_path] = tempfile.NamedTemporaryFile(
                prefix='.{}'.format(file_name), dir=target_dir, delete=False)
        self.pending_files[target_file_path].write(file_bytes)

    def stopTestRun(self):
        for target_path, f in self.pending_files.items():
            f.close()
            os.rename(f.name, target_path)
