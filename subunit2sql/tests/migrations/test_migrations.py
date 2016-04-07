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

import datetime
import os
import uuid

from alembic import config
from alembic import script
import six
from six.moves import configparser as ConfigParser
import sqlalchemy
from sqlalchemy.engine import reflection

from subunit2sql import exceptions as exc
from subunit2sql.tests import base
from subunit2sql.tests import db_test_utils
from subunit2sql.tests import subunit2sql_fixtures as fixtures


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

    def assertColumnExists(self, engine, table, column):
        table = get_table(engine, table)
        self.assertIn(column, table.c)

    def _revisions(self):
        """Provides revisions and its parent revisions.

        :return: List of tuples. Every tuple contains revision and its parent
        revision.
        """
        db_config = config.Config(os.path.join(self.script_location,
                                               'alembic.ini'))
        db_config.set_main_option('script_location', 'subunit2sql:migrations')
        script_dir = script.ScriptDirectory.from_config(db_config)
        revisions = list(script_dir.walk_revisions("base", "head"))

        if not revisions:
            raise exc.DbMigrationError('There is no suitable migrations.')

        for rev in list(reversed(revisions)):
            # Destination, current
            yield rev.revision, rev.down_revision

    def _walk_versions(self, engine):
        """Test migrations ability to upgrade."""

        revisions = self._revisions()
        for dest, curr in revisions:
            self._migrate_up(engine, dest, curr, with_data=True)

    def _migrate_up(self, engine, dest, curr, with_data=False):
        if with_data:
            data = None
            pre_upgrade = getattr(
                self, "_pre_upgrade_%s" % dest, None)
            if pre_upgrade:
                data = pre_upgrade(engine)
        db_test_utils.run_migration(dest, engine)
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
            self._walk_versions(engine)

    def test_mysql_connect_fail(self):
        """Test graceful mysql connection failure.

        Test that we can trigger a mysql connection failure and we fail
        gracefully to ensure we don't break people without mysql
        """
        if db_test_utils.is_backend_avail('mysql', user="openstack_cifail"):
            self.fail("Shouldn't have connected")

    def test_mysql_opportunistically(self):
        self.useFixture(fixtures.LockFixture('mysql'))
        if not db_test_utils.is_backend_avail('mysql'):
            raise self.skipTest('mysql is not available')

        self.useFixture(fixtures.MySQLConfFixture())
        # Test that table creation on mysql only builds InnoDB tables
        # add this to the global lists to make reset work with it, it's removed
        # automatically in tearDown so no need to clean it up here.
        connect_string = db_test_utils.get_connect_string("mysql")
        engine = sqlalchemy.create_engine(connect_string)
        self.engines["mysqlcitest"] = engine
        self.test_databases["mysqlcitest"] = connect_string

        # build a fully populated mysql database with all the tables
        self._walk_versions(engine)

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
        if db_test_utils.is_backend_avail('postgresql',
                                          user="openstack_cifail"):
            self.fail("Shouldn't have connected")

    def test_postgresql_opportunistically(self):
        # Test postgresql database migration walk
        self.useFixture(fixtures.LockFixture('postgres'))
        if not db_test_utils.is_backend_avail('postgres'):
            raise self.skipTest('postgres is not available')
        self.useFixture(fixtures.PostgresConfFixture())
        # add this to the global lists to make reset work with it, it's removed
        # automatically in tearDown so no need to clean it up here.
        connect_string = db_test_utils.get_connect_string("postgres")
        engine = sqlalchemy.create_engine(connect_string)
        self.engines["postgresqlcitest"] = engine
        self.test_databases["postgresqlcitest"] = connect_string

        # build a fully populated postgresql database with all the tables
        self._walk_versions(engine)

    def test_sqlite_opportunistically(self):
        self.useFixture(fixtures.LockFixture('sqlite'))
        self.useFixture(fixtures.SqliteConfFixture())

        connect_string = db_test_utils.get_connect_string("sqlite")
        engine = sqlalchemy.create_engine(connect_string)
        self.engines["sqlitecitest"] = engine
        self.test_databases["sqlitecitest"] = connect_string

        self._walk_versions(engine)

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
        run_at = list(map(lambda x: (x['id'], x['run_at']), result))
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
        run_time_pairs = list(map(lambda x: (x['id'], x['run_time']), result))
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

    def _pre_upgrade_2fb76f1a1393(self, engine):
        test_metadata = get_table(engine, 'test_metadata')
        tests = get_table(engine, 'tests')
        test = {'id': 'fake_test_with_metadata.id',
                'test_id': 'fake_project.tests.FakeTestClass.fake_test_meta',
                'run_count': 1,
                'success': 1,
                'failure': 0}
        tests.insert().values(test).execute()
        data = {'id': 'AUUID',
                'key': 'AKey',
                'value': 42,
                'test_run_id': 'fake_test_with_metadata.id'}
        test_metadata.insert().values(data).execute()
        return data

    def _check_2fb76f1a1393(self, engine, data):
        test_metadata = get_table(engine, 'test_metadata')
        res = list(test_metadata.select().execute())[0]
        self.assertEqual(res.id, data['id'])
        self.assertEqual(res.test_id, data['test_run_id'])

    def _pre_upgrade_b96122f780(self, engine):
        # NOTE(mtreinish) Return fake data to ensure we run check, this
        # is needed because the framework normall assumes you're preseeded
        # data is in the correct state post migration. But this time all we
        # want to do is ensure a single index exists so that isn't needed
        return 'data'

    def _check_b96122f780(self, engine, data):
        insp = reflection.Inspector(engine)
        indxs = insp.get_indexes('test_runs')
        # Check that we don't duplicate indexes anymore
        tests = [indx for indx in indxs if ['test_id'] == indx['column_names']]
        runs = [indx for indx in indxs if indx['column_names'] == ['run_id']]
        self.assertEqual(1, len(tests))
        self.assertEqual(1, len(runs))

    def _pre_upgrade_2822a408bdd0(self, engine):
        data = {}

        # Add run
        runs = get_table(engine, 'runs')
        run = {'id': six.text_type(uuid.uuid4()),
               'skips': 0,
               'fails': 0,
               'passes': 1,
               'run_time': 1.0,
               'artifacts': 'https://am_i_really_a_fake_url',
               'run_at': datetime.datetime.utcnow()}
        runs.insert().values(run).execute()
        data['run'] = run
        # Add test_metadata
        run_metadatas = get_table(engine, 'run_metadata')
        run_metadata = {'id': six.text_type(uuid.uuid4()),
                        'run_id': run['id'],
                        'key': 'attrs',
                        'value': 'an_attr'}
        run_metadatas.insert().values(run_metadata).execute()
        data['run_metadata'] = run_metadata

        # Add test
        tests = get_table(engine, 'tests')
        test = {'id': six.text_type(uuid.uuid4()),
                'test_id': 'I_am_a_real_test!',
                'success': 1,
                'failure': 0}
        tests.insert().values(test).execute()
        data['test'] = test

        # Add test_metadata
        test_metadatas = get_table(engine, 'test_metadata')
        test_metadata = {'id': six.text_type(uuid.uuid4()),
                         'test_id': test['id'],
                         'key': 'a_real_key',
                         'value': 'an_attr'}
        test_metadatas.insert().values(test_metadata).execute()
        data['test_metadata'] = test_metadata

        # Add test run
        now = datetime.datetime.now()
        future_now = now + datetime.timedelta(0, 4)

        test_runs = get_table(engine, 'test_runs')

        test_run = {'id': six.text_type(uuid.uuid4()),
                    'test_id': test['id'],
                    'run_id': run['id'],
                    'start_time': now,
                    'status': 'success',
                    'stop_time': future_now}
        test_runs.insert().values(test_run).execute()
        data['test_run'] = test_run

        # Add test_run_metadata
        test_run_metadatas = get_table(engine, 'test_run_metadata')
        test_run_metadata = {'id': six.text_type(uuid.uuid4()),
                             'test_run_id': test_run['id'],
                             'key': 'attrs',
                             'value': 'an_attr'}
        test_run_metadatas.insert().values(test_run_metadata).execute()
        data['test_run_metadata'] = test_run_metadata

        attachments = get_table(engine, 'attachments')
        attachment = {'id': six.text_type(uuid.uuid4()),
                      'test_run_id': test_run['id'],
                      'label': 'an_attachment',
                      'attachment': b'something'}
        attachments.insert().values(attachment).execute()
        data['attachment'] = attachment
        return data

    def _check_2822a408bdd0(self, engine, data):
        # Check Primary Keys
        insp = reflection.Inspector(engine)
        runs_pk = insp.get_pk_constraint('runs')
        self.assertEqual(['id'], runs_pk['constrained_columns'])
        run_meta_pk = insp.get_pk_constraint('run_metadata')
        self.assertEqual(['id'], run_meta_pk['constrained_columns'])
        tests_pk = insp.get_pk_constraint('tests')
        self.assertEqual(['id'], tests_pk['constrained_columns'])
        test_meta_pk = insp.get_pk_constraint('test_metadata')
        self.assertEqual(['id'], test_meta_pk['constrained_columns'])
        test_runs_pk = insp.get_pk_constraint('runs')
        self.assertEqual(['id'], test_runs_pk['constrained_columns'])
        test_run_meta_pk = insp.get_pk_constraint('tests')
        self.assertEqual(['id'], test_run_meta_pk['constrained_columns'])
        attach_pk = insp.get_pk_constraint('attachments')
        self.assertEqual(['id'], attach_pk['constrained_columns'])

        if engine.dialect.name == 'sqlite':
            new_id_type = sqlalchemy.Integer
        else:
            new_id_type = sqlalchemy.BigInteger

        # Check id column type
        runs_col = [x for x in insp.get_columns(
            'runs') if x['name'] == 'id'][0]
        self.assertIsInstance(runs_col['type'], new_id_type)
        run_meta_col = [x for x in insp.get_columns(
            'run_metadata') if x['name'] == 'id'][0]
        self.assertIsInstance(run_meta_col['type'], new_id_type)
        tests_col = [x for x in insp.get_columns(
            'tests') if x['name'] == 'id'][0]
        self.assertIsInstance(tests_col['type'], new_id_type)
        test_meta_col = [x for x in insp.get_columns(
            'test_metadata') if x['name'] == 'id'][0]
        self.assertIsInstance(test_meta_col['type'], new_id_type)
        test_runs_col = [x for x in insp.get_columns(
            'test_runs') if x['name'] == 'id'][0]
        self.assertIsInstance(test_runs_col['type'], new_id_type)
        test_run_meta_col = [x for x in insp.get_columns(
            'test_run_metadata') if x['name'] == 'id'][0]
        self.assertIsInstance(test_run_meta_col['type'], new_id_type)
        attach_col = [x for x in insp.get_columns(
            'attachments') if x['name'] == 'id'][0]
        self.assertIsInstance(attach_col['type'], new_id_type)

        # Check all the new ids match
        runs_t = get_table(engine, 'runs')
        run_ids = [x[1] for x in runs_t.select().execute()]
        run_metadatas_t = get_table(engine, 'run_metadata')
        tests_t = get_table(engine, 'tests')
        test_metadatas_t = get_table(engine, 'test_metadata')
        test_runs_t = get_table(engine, 'test_runs')
        test_runs_raw = list(test_runs_t.select().execute())
        test_run_test_ids = [x[1] for x in test_runs_raw]
        test_run_metadatas_t = get_table(engine, 'test_run_metadata')
        attachments_t = get_table(engine, 'attachments')
        # Get test we inserted before migration
        test_row = list(tests_t.select().where(
            tests_t.c.test_id == data['test']['test_id']).execute())[0]
        self.assertIn(test_row[0], test_run_test_ids)
        # Check test run
        test_run_row = list(test_runs_t.select().where(
            test_runs_t.c.test_id == test_row[0]).execute())[0]
        self.assertEqual(test_run_row[3], data['test_run']['status'])
        self.assertEqual(test_run_row[4].replace(microsecond=0),
                         data['test_run']['start_time'].replace(microsecond=0))
        self.assertEqual(test_run_row[5].replace(microsecond=0),
                         data['test_run']['stop_time'].replace(microsecond=0))
        self.assertIn(test_run_row[2], run_ids)
        # Check run
        run_row = list(runs_t.select().where(
            runs_t.c.id == test_run_row[2]).execute())[0]
        self.assertEqual(data['run']['artifacts'], run_row[6])
        self.assertEqual(data['run']['id'], run_row[0])
        # Check run metadata
        run_metadata_row = list(run_metadatas_t.select().where(
            run_metadatas_t.c.run_id == run_row[1]).execute())[0]
        self.assertEqual(data['run_metadata']['key'], run_metadata_row[1])
        self.assertEqual(data['run_metadata']['value'], run_metadata_row[2])
        # Check test metadata
        test_metadata_row = list(test_metadatas_t.select().where(
            test_metadatas_t.c.test_id == test_row[0]).execute())[0]
        self.assertEqual(data['test_metadata']['key'], test_metadata_row[1])
        self.assertEqual(data['test_metadata']['value'], test_metadata_row[2])
        # Check test run metadata
        test_run_metadata_row = list(test_run_metadatas_t.select().where(
            test_run_metadatas_t.c.test_run_id == test_run_row[0]).execute())
        test_run_metadata_row = test_run_metadata_row[0]
        self.assertEqual(data['test_run_metadata']['key'],
                         test_run_metadata_row[1])
        self.assertEqual(data['test_run_metadata']['value'],
                         test_run_metadata_row[2])
        # Check attachment
        attachment_row = list(attachments_t.select().where(
            attachments_t.c.test_run_id == test_run_row[0]).execute())[0]
        self.assertEqual(data['attachment']['label'], attachment_row[2])
        self.assertEqual(data['attachment']['attachment'], attachment_row[3])
