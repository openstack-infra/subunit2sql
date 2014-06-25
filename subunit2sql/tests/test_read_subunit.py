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

from subunit2sql import read_subunit as subunit
from subunit2sql.tests import base


class TestReadSubunit(base.TestCase):
    def test_get_duration(self):
        dur = subunit.get_duration(datetime.datetime(1914, 6, 28, 10, 45, 0),
                                   datetime.datetime(1914, 6, 28, 10, 45, 50))
        self.assertEqual(dur, '50.000000s')
