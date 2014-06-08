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

import os
import sys

from oslo.config import cfg
from oslo.db import options

from subunit2sql import subunit

shell_opts = [
    cfg.StrOpt('state_path', default='$pybasedir',
               help='Top level dir for maintaining subunit2sql state'),
    cfg.MultiStrOpt('subunit_files', positional=True)
]

CONF = cfg.CONF
for opt in shell_opts:
    CONF.register_cli_opt(opt)


def state_path_def(*args):
    """Return an uninterpolated path relative to $state_path."""
    return os.path.join('$state_path', *args)


_DEFAULT_SQL_CONNECTION = 'sqlite:///' + state_path_def('subunit2sql.sqlite')


def parse_args(argv, default_config_files=None):
    options.set_defaults(CONF, connection=_DEFAULT_SQL_CONNECTION,
                         sqlite_db='subunit2sql.sqlite')
    CONF.register_opts(options.database_opts)
    cfg.CONF(argv[1:], project='subunit2sql',
             default_config_files=default_config_files)

def main():
    parse_args(sys.argv)
    if CONF.subunit_files:
        streams = [ subunit.ReadSubunit(s) for s in subunit_files ]
    else:
        steams = [ subunit.ReadSubunit(sys.stdin) ]


if __name__ == "__main__":
    sys.exit(main())
