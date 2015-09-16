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

import os
import shutil
import subprocess
import urlparse

import fixtures as fix
from oslo_concurrency.fixture import lockutils as lock_fixture
from oslo_concurrency import lockutils
from oslo_config import fixture as config_fixture
from oslo_db import options

from subunit2sql.db import api as session
from subunit2sql.migrations import cli
from subunit2sql.tests import db_test_utils

DB_SCHEMA = ""


def execute_cmd(cmd=None):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, shell=True)
    output = proc.communicate()[0]
    if proc.returncode != 0:
        raise Exception('Command failed with output:\n%s' % output)


class Database(fix.Fixture):
    def _cache_schema(self):
        global DB_SCHEMA
        if not DB_SCHEMA:
            db_test_utils.run_migration("head")

    def cleanup(self):
        engine = session.get_engine()
        engine.dispose()

    def reset(self):
        self._cache_schema()
        engine = session.get_engine()
        engine.dispose()
        engine.connect()

    def setUp(self):
        super(Database, self).setUp()
        self.reset()
        self.addCleanup(self.cleanup)


class MySQLConfFixture(config_fixture.Config):
    """Fixture to manage global conf settings."""
    def _drop_db(self):
        addr = urlparse.urlparse(self.url)
        database = addr.path.strip('/')
        loc_pieces = addr.netloc.split('@')
        host = loc_pieces[1]
        auth_pieces = loc_pieces[0].split(':')
        user = auth_pieces[0]
        password = ""
        if len(auth_pieces) > 1:
            if auth_pieces[1].strip():
                password = "-p\"%s\"" % auth_pieces[1]
        sql = ("drop database if exists %(database)s; create "
               "database %(database)s;") % {'database': database}
        cmd = ("mysql -u \"%(user)s\" %(password)s -h %(host)s "
               "-e \"%(sql)s\"") % {'user': user, 'password': password,
                                    'host': host, 'sql': sql}
        execute_cmd(cmd)

    def setUp(self):
        super(MySQLConfFixture, self).setUp()
        self.register_opts(options.database_opts, group='database')
        self.url = db_test_utils.get_connect_string("mysql")
        self.set_default('connection', self.url, group='database')
        lockutils.set_defaults(lock_path='/tmp')
        self._drop_db()


class PostgresConfFixture(config_fixture.Config):
    """Fixture to manage global conf settings."""
    def _drop_db(self):
        addr = urlparse.urlparse(self.url)
        database = addr.path.strip('/')
        loc_pieces = addr.netloc.split('@')
        host = loc_pieces[1]

        auth_pieces = loc_pieces[0].split(':')
        user = auth_pieces[0]
        password = ""
        if len(auth_pieces) > 1:
            password = auth_pieces[1].strip()
        pg_file = os.path.join(os.path.expanduser('~'), '.pgpass')
        if os.path.isfile(pg_file):
            tmp_path = os.path.join('/tmp', 'pgpass')
            shutil.move(pg_file, tmp_path)
            self.addCleanup(shutil.move, tmp_path, pg_file)

        pg_pass = '*:*:*:%(user)s:%(password)s' % {
            'user': user, 'password': password}
        with open(pg_file, 'w') as fd:
            fd.write(pg_pass)
        os.chmod(pg_file, 384)
        # note(boris-42): We must create and drop database, we can't
        # drop database which we have connected to, so for such
        # operations there is a special database template1.
        sqlcmd = ("psql -w -U %(user)s -h %(host)s -c"
                  " '%(sql)s' -d template1")
        sql = ("drop database if exists %(database)s;")
        sql = sql % {'database': database}
        droptable = sqlcmd % {'user': user, 'host': host,
                              'sql': sql}
        execute_cmd(droptable)
        sql = ("create database %(database)s;")
        sql = sql % {'database': database}
        createtable = sqlcmd % {'user': user, 'host': host,
                                'sql': sql}
        execute_cmd(createtable)

    def setUp(self):
        super(PostgresConfFixture, self).setUp()
        self.register_opts(options.database_opts, group='database')
        self.register_opts(cli.MIGRATION_OPTS)
        self.url = db_test_utils.get_connect_string("postgres")
        self.set_default('connection', self.url, group='database')
        self.set_default('disable_microsecond_data_migration', False)
        lockutils.set_defaults(lock_path='/tmp')
        self._drop_db()


class SqliteConfFixture(config_fixture.Config):
    """Fixture to manage global conf settings."""
    def _drop_db(self):
        if os.path.exists(db_test_utils.SQLITE_TEST_DATABASE_PATH):
            os.remove(db_test_utils.SQLITE_TEST_DATABASE_PATH)

    def setUp(self):
        super(SqliteConfFixture, self).setUp()
        self.register_opts(options.database_opts, group='database')
        self.register_opts(cli.MIGRATION_OPTS)
        self.url = db_test_utils.get_connect_string("sqlite")
        self.set_default('connection', self.url, group='database')
        self.set_default('disable_microsecond_data_migration', False)
        lockutils.set_defaults(lock_path='/tmp')
        self._drop_db()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self._drop_db()


class LockFixture(lock_fixture.LockFixture):
    def __init__(self, name):
        lockutils.set_defaults(lock_path='/tmp')
        super(LockFixture, self).__init__(name, 'subunit-db-lock-')
