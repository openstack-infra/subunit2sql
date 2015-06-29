# Copyright 2010-2011 OpenStack Foundation
# Copyright 2013 IBM Corp.
# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ConfigParser
import datetime
import os
import subprocess


from alembic import config
from alembic import script
from oslo_config import cfg
from oslo_db import options
import six
from six.moves.urllib import parse
import sqlalchemy

from subunit2sql import exceptions as exc
from subunit2sql.migrations import cli
from subunit2sql.tests import base

CONF = cfg.CONF
CONF.register_cli_opts(options.database_opts, group='database')


def _get_connect_string(backend,
                        user="openstack_citest",
                        passwd="openstack_citest",
                        database="openstack_citest"):
    """Generate a db uri for testing locally.

    Try to get a connection with a very specific set of values, if we get
    these then we'll run the tests, otherwise they are skipped
    """
    if backend == "mysql":
        backend = "mysql+mysqldb"
    elif backend == "postgres":
        backend = "postgresql+psycopg2"

    return ("%(backend)s://%(user)s:%(passwd)s@localhost/%(database)s"
            % {'backend': backend, 'user': user, 'passwd': passwd,
               'database': database})


def _is_backend_avail(backend,
                      user="openstack_citest",
                      passwd="openstack_citest",
                      database="openstack_citest"):
    try:
        if backend == "mysql":
            connect_uri = _get_connect_string("mysql", user=user,
                                              passwd=passwd, database=database)
        elif backend == "postgres":
            connect_uri = _get_connect_string("postgres", user=user,
                                              passwd=passwd, database=database)
        engine = sqlalchemy.create_engine(connect_uri)
        connection = engine.connect()
    except Exception:
        # intentionally catch all to handle exceptions even if we don't
        # have any backend code loaded.
        return False
    else:
        connection.close()
        engine.dispose()
        return True


def get_table(engine, name):
    """Returns an sqlalchemy table dynamically from db.

    Needed because the models don't work for us in migrations
    as models will be far out of sync with the current data.
    """
    metadata = sqlalchemy.schema.MetaData()
    metadata.bind = engine
    return sqlalchemy.Table(name, metadata, autoload=True)


class TestWalkMigrations(base.TestCase):

    DEFAULT_CONFIG_FILE = os.path.join(os.path.dirname(__file__),
                                       'test_migrations.conf')
    CONFIG_FILE_PATH = os.environ.get('SUBUNIT2SQL_TEST_MIGRATIONS_CONF',
                                      DEFAULT_CONFIG_FILE)
    script_location = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(__file__))), 'migrations')

    def setUp(self):
        super(TestWalkMigrations, self).setUp()

        self.snake_walk = False
        self.test_databases = {}

        if os.path.exists(self.CONFIG_FILE_PATH):
            cp = ConfigParser.RawConfigParser()
            try:
                cp.read(self.CONFIG_FILE_PATH)
                defaults = cp.options('unit_tests')
                for key in defaults:
                    self.test_databases[key] = cp.get('unit_tests', key)
                self.snake_walk = cp.getboolean('walk_style', 'snake_walk')
            except ConfigParser.ParsingError as e:
                self.fail("Failed to read test_migrations.conf config "
                          "file. Got error: %s" % e)
        else:
            self.fail("Failed to find test_migrations.conf config "
                      "file.")

        self.engines = {}
        for key, value in self.test_databases.items():
            self.engines[key] = sqlalchemy.create_engine(value)

        # We start each test case with a completely blank slate.
        self._reset_databases()

    def assertColumnExists(self, engine, table, column):
        table = get_table(engine, table)
        self.assertIn(column, table.c)

    def _reset_databases(self):
        def execute_cmd(cmd=None):
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, shell=True)
            output = proc.communicate()[0]
            self.assertEqual(0, proc.returncode, 'Command failed with '
                             'output:\n%s' % output)
        for key, engine in self.engines.items():
            conn_string = self.test_databases[key]
            conn_pieces = parse.urlparse(conn_string)
            engine.dispose()
            if conn_string.startswith('sqlite'):
                # We can just delete the SQLite database, which is
                # the easiest and cleanest solution
                db_path = conn_pieces.path[1:]
                if os.path.exists(db_path):
                    os.unlink(db_path)
                # No need to recreate the SQLite DB. SQLite will
                # create it for us if it's not there...
            elif conn_string.startswith('mysql'):
                # We can execute the MySQL client to destroy and re-create
                # the MYSQL database, which is easier and less error-prone
                # than using SQLAlchemy to do this via MetaData...trust me.
                database = conn_pieces.path.strip('/')
                loc_pieces = conn_pieces.netloc.split('@')
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
            elif conn_string.startswith('postgresql'):
                database = conn_pieces.path.strip('/')
                loc_pieces = conn_pieces.netloc.split('@')
                host = loc_pieces[1]

                auth_pieces = loc_pieces[0].split(':')
                user = auth_pieces[0]
                password = ""
                if len(auth_pieces) > 1:
                    password = auth_pieces[1].strip()
                # note(boris-42): This file is used for authentication
                # without password prompt.
                createpgpass = ("echo '*:*:*:%(user)s:%(password)s' > "
                                "~/.pgpass && chmod 0600 ~/.pgpass" %
                                {'user': user, 'password': password})
                execute_cmd(createpgpass)
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

    def _get_alembic_config(self, uri):
        db_config = config.Config(os.path.join(self.script_location,
                                               'alembic.ini'))
        db_config.set_main_option('script_location', 'subunit2sql:migrations')
        db_config.subunit2sql_config = CONF
        db_config.subunit2sql_config.set_override('connection',
                                                  six.text_type(uri),
                                                  group='database')
        self.script_dir = script.ScriptDirectory.from_config(db_config)
        return db_config

    def _revisions(self, downgrade=False):
        """Provides revisions and its parent revisions.

        :param downgrade: whether to include downgrade behavior or not.
        :type downgrade: Bool
        :return: List of tuples. Every tuple contains revision and its parent
        revision.
        """

        revisions = list(self.script_dir.walk_revisions("base", "head"))

        if not downgrade:
            revisions = list(reversed(revisions))

        if not revisions:
            raise exc.DbMigrationError('There is no suitable migrations.')

        for rev in revisions:
            if downgrade:
                # Destination, current
                yield rev.down_revision, rev.revision
            else:
                # Destination, current
                yield rev.revision, rev.down_revision

    def _walk_versions(self, config, engine, downgrade=True, snake_walk=False):
        """Test migrations ability to upgrade and downgrade.

        :param downgrade: whether to include downgrade behavior or not.
        :type downgrade: Bool
        :snake_walk: enable mode when at every upgrade revision will be
        downgraded and upgraded in previous state at upgrade and backward at
        downgrade.
        :type snake_walk: Bool
        """

        revisions = self._revisions()
        for dest, curr in revisions:
            self._migrate_up(config, engine, dest, curr, with_data=True)

            if snake_walk and dest != 'None':
                # NOTE(I159): Pass reversed arguments into `_migrate_down`
                # method because we have been upgraded to a destination
                # revision and now we going to downgrade back.
                self._migrate_down(config, curr, dest, with_data=True)
                self._migrate_up(config, dest, curr, with_data=True)

        if downgrade:
            revisions = self._revisions(downgrade)
            for dest, curr in revisions:
                self._migrate_down(config, engine, dest, curr, with_data=True)
                if snake_walk:
                    self._migrate_up(config, engine, curr, dest,
                                     with_data=True)
                    self._migrate_down(config, engine, dest, curr,
                                       with_data=True)

    def _migrate_down(self, config, engine, dest, curr, with_data=False):

        if dest:
            cli.do_alembic_command(config, 'downgrade', dest)
        else:
            meta = sqlalchemy.MetaData(bind=engine)
            meta.drop_all()

        if with_data:
            post_downgrade = getattr(
                self, "_post_downgrade_%s" % curr, None)
            if post_downgrade:
                post_downgrade(engine)

    def _migrate_up(self, config, engine, dest, curr, with_data=False):
        if with_data:
            data = None
            pre_upgrade = getattr(
                self, "_pre_upgrade_%s" % dest, None)
            if pre_upgrade:
                data = pre_upgrade(engine)
        cli.do_alembic_command(config, 'upgrade', dest)
        if with_data:
            check = getattr(self, "_check_%s" % dest, None)
            if check and data:
                check(engine, data)

    def test_walk_versions(self):
        """Test walk versions.

        Walks all version scripts for each tested database, ensuring
        that there are no errors in the version scripts for each engine
        """
        for key, engine in self.engines.items():
            config = self._get_alembic_config(self.test_databases[key])
            self._walk_versions(config, engine, self.snake_walk)

    def test_mysql_connect_fail(self):
        """Test graceful mysql connection failure.

        Test that we can trigger a mysql connection failure and we fail
        gracefully to ensure we don't break people without mysql
        """
        if _is_backend_avail('mysql', user="openstack_cifail"):
            self.fail("Shouldn't have connected")

    def test_mysql_opportunistically(self):
        # Test that table creation on mysql only builds InnoDB tables
        if not _is_backend_avail('mysql'):
            self.skipTest("mysql not available")
        # add this to the global lists to make reset work with it, it's removed
        # automatically in tearDown so no need to clean it up here.
        connect_string = _get_connect_string("mysql")
        engine = sqlalchemy.create_engine(connect_string)
        config = self._get_alembic_config(connect_string)
        self.engines["mysqlcitest"] = engine
        self.test_databases["mysqlcitest"] = connect_string

        # build a fully populated mysql database with all the tables
        self._reset_databases()
        self._walk_versions(config, engine, False, False)

        connection = engine.connect()
        # sanity check
        total = connection.execute("SELECT count(*) "
                                   "from information_schema.TABLES "
                                   "where TABLE_SCHEMA='openstack_citest'")
        self.assertTrue(total.scalar() > 0, "No tables found. Wrong schema?")

        noninnodb = connection.execute("SELECT count(*) "
                                       "from information_schema.TABLES "
                                       "where TABLE_SCHEMA='openstack_citest' "
                                       "and ENGINE!='InnoDB' "
                                       "and TABLE_NAME!='alembic_version'")
        count = noninnodb.scalar()
        self.assertEqual(count, 0, "%d non InnoDB tables created" % count)
        connection.close()

    def test_postgresql_connect_fail(self):
        """Test graceful postgresql connection failure.

        Test that we can trigger a postgres connection failure and we fail
        gracefully to ensure we don't break people without postgres
        """
        if _is_backend_avail('postgresql', user="openstack_cifail"):
            self.fail("Shouldn't have connected")

    def test_postgresql_opportunistically(self):
        # Test postgresql database migration walk
        if not _is_backend_avail('postgres'):
            self.skipTest("postgresql not available")
        # add this to the global lists to make reset work with it, it's removed
        # automatically in tearDown so no need to clean it up here.
        connect_string = _get_connect_string("postgres")
        engine = sqlalchemy.create_engine(connect_string)
        config = self._get_alembic_config(connect_string)
        self.engines["postgresqlcitest"] = engine
        self.test_databases["postgresqlcitest"] = connect_string

        # build a fully populated postgresql database with all the tables
        self._reset_databases()
        self._walk_versions(config, engine, False, False)

    def _pre_upgrade_1f92cfe8a6d3(self, engine):
        tests = get_table(engine, 'tests')
        data = {'id': 'fake_test.id',
                'test_id': 'fake_project.tests.FakeTestClass.fake_test',
                'run_count': 1,
                'success': 1,
                'failure': 0}
        tests.insert().values(data).execute()
        return data

    def _pre_upgrade_3db7b49816d5(self, engine):
        runs = get_table(engine, 'runs')
        data = {'id': 'fake_run.id',
                'skips': 0,
                'fails': 0,
                'passes': 1,
                'run_time': 1.0,
                'artifacts': 'fake_url'}
        runs.insert().values(data).execute()
        return data

    def _pre_upgrade_163fd5aa1380(self, engine):
        now = datetime.datetime.now()
        test_runs = get_table(engine, 'test_runs')
        data = {'id': 'fake_test_run.id',
                'test_id': 'fake_test.id',
                'run_id': 'fake_run.id',
                'status': 'pass',
                'start_time': now,
                'stop_time': now + datetime.timedelta(1, 0)}
        test_runs.insert().values(data).execute()
        return data

    def _check_163fd5aa1380(self, engine, data):
        self.assertColumnExists(engine, 'tests', 'run_time')

    def _pre_upgrade_28ac1ba9c3db(self, engine):
        runs = get_table(engine, 'runs')
        data = [{'id': 'fake_run.id1',
                 'skips': 0,
                 'fails': 0,
                 'passes': 1,
                 'run_time': 1.0,
                 'artifacts': 'fake_url'},
                {'id': 'fake_run.id2',
                 'skips': 0,
                 'fails': 0,
                 'passes': 1,
                 'run_time': 1.0,
                 'artifacts': 'fake_url'}]
        for run in data:
            runs.insert().values(run).execute()
        return data

    def _check_28ac1ba9c3db(self, engine, data):
        self.assertColumnExists(engine, 'runs', 'run_at')
        runs = get_table(engine, 'runs')
        now = datetime.datetime.now().replace(microsecond=0)
        time_data = {'id': 'fake_run_with_time.id1',
                     'skips': 0,
                     'fails': 0,
                     'passes': 1,
                     'run_time': 1.0,
                     'artifacts': 'fake_url',
                     'run_at': now}
        runs.insert().values(time_data).execute()
        runs = get_table(engine, 'runs')
        result = runs.select().execute()
        run_at = map(lambda x: (x['id'], x['run_at']), result)
        for run in data:
            self.assertIn((run['id'], None), run_at)
        self.assertIn((time_data['id'], now), run_at)

    def _pre_upgrade_5332fe255095(self, engine):
        tests = get_table(engine, 'tests')
        test_runs = get_table(engine, 'test_runs')
        # Create 2 sample rows one for a passing test the other failing
        fake_tests = {'pass': {'id': 'fake_null_test_id',
                               'test_id': 'I_am_a_little_test_that_works',
                               'success': 2,
                               'failure': 0},
                      'fail': {'id': 'fake_null_test_id_fails',
                               'test_id': 'Im_a_little_test_that_doesnt_work',
                               'success': 0,
                               'failure': 1}}
        now = datetime.datetime.now()
        future_now = now + datetime.timedelta(0, 4)
        # Create sample rows for the test_runs corresponding to the test rows
        fake_test_runs = {'pass': [
            {'id': 'fake_test_run_pass_1', 'test_id': 'fake_null_test_id',
             'run_id': 'fake_run.id1', 'start_time': now, 'status': 'success',
             'stop_time': future_now},
            {'id': 'fake_test_run_pass_2', 'test_id': 'fake_null_test_id',
             'run_id': 'fake_run.id2', 'start_time': now, 'status': 'success',
             'stop_time': future_now}]}
        fake_test_runs['fail'] = {'id': 'fake_test_run_fail',
                                  'test_id': 'fake_null_test_id_fails',
                                  'run_id': 'fake_run.id1',
                                  'start_time': now,
                                  'status': 'fail',
                                  'stop_time': future_now}
        for test in fake_tests:
            tests.insert().values(fake_tests[test]).execute()
        for test_run in fake_test_runs['pass']:
            test_runs.insert().values(test_run).execute()
        test_runs.insert().values(fake_test_runs['fail']).execute()
        return {'tests': fake_tests, 'test_runs': fake_test_runs}

    def _check_5332fe255095(self, engine, data):
        tests = get_table(engine, 'tests')
        # Get the test uuids from the same data set
        test_ids = [data['tests'][x]['id'] for x in data['tests']]
        # Query the DB for the tests from the sample dataset above
        where = ' OR '.join(["tests.id='%s'" % x for x in test_ids])
        result = tests.select(where).execute()
        run_time_pairs = map(lambda x: (x['id'], x['run_time']), result)
        # Ensure the test with one failure is None
        self.assertIn(('fake_null_test_id_fails', None), run_time_pairs)
        # Ensure the test with 2 success each taking 4 sec lists the proper
        # run_time
        self.assertIn(('fake_null_test_id', 4.0), run_time_pairs)

    def _pre_upgrade_1679b5bc102c(self, engine):
        test_runs = get_table(engine, 'test_runs')
        now = datetime.datetime.now()
        future_now = now + datetime.timedelta(0, 4)
        fake_test_runs = {'id': 'abc123',
                          'test_id': 'fake_null_test_id',
                          'run_id': 'fake_run.id',
                          'status': 'success',
                          'start_time': now,
                          'stop_time': future_now}
        test_runs.insert().values(fake_test_runs).execute()
        return fake_test_runs

    def _check_1679b5bc102c(self, engine, data):
        test_runs = get_table(engine, 'test_runs')
        start_micro = data['start_time'].microsecond
        stop_micro = data['stop_time'].microsecond
        result = test_runs.select().execute()
        row = None
        for i in result:
            if i.id == data['id']:
                row = i
                break
        else:
            self.fail("Row not present")
        if row.start_time_microsecond == 0 and row.stop_time_microsecond == 0:
            # Backing db doesn't store subseconds so the migration will just
            # populate zeros and the data is lost to the ether.
            pass
        else:
            self.assertEqual(start_micro, row.start_time_microsecond)
            self.assertEqual(row.stop_time_microsecond, stop_micro)
