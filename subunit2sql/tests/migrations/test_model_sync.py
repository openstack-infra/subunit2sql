# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
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


import mock
from oslo_db.sqlalchemy import test_migrations
import sqlalchemy
import testscenarios

from subunit2sql.db import models
from subunit2sql.tests import base
from subunit2sql.tests import db_test_utils
from subunit2sql.tests import subunit2sql_fixtures as fixtures

load_tests = testscenarios.load_tests_apply_scenarios


class TestModelsMigrations(test_migrations.ModelsMigrationsSync,
                           base.TestCase):
    """Test for checking of equality models state and migrations.

    Output is a list that contains information about differences between db and
    models. Output example::
       [('add_table',
         Table('bat', MetaData(bind=None),
               Column('info', String(), table=<bat>), schema=None)),
        ('remove_table',
         Table(u'bar', MetaData(bind=None),
               Column(u'data', VARCHAR(), table=<bar>), schema=None)),
        ('add_column',
         None,
         'foo',
         Column('data', Integer(), table=<foo>)),
        ('remove_column',
         None,
         'foo',
         Column(u'old_data', VARCHAR(), table=None)),
        [('modify_nullable',
          None,
          'foo',
          u'x',
          {'existing_server_default': None,
          'existing_type': INTEGER()},
          True,
          False)]]
    * ``remove_*`` means that there is extra table/column/constraint in db;
    * ``add_*`` means that it is missing in db;
    * ``modify_*`` means that on column in db is set wrong
      type/nullable/server_default. Element contains information:
        - what should be modified,
        - schema,
        - table,
        - column,
        - existing correct column parameters,
        - right value,
        - wrong value.
    """

    scenarios = [
        ('mysql', {'dialect': 'mysql'}),
        ('postgresql', {'dialect': 'postgres'}),
        ('sqlite', {'dialect': 'sqlite'})
    ]
    # NOTE(mtreinish): Mock out db attr because oslo.db tries to assert
    # control of how the opportunistic db is setup. But, since subunit2sql's
    # tests already do this, just let oslo.db think it's doing the operations
    db = mock.MagicMock()

    def setUp(self):
        super(TestModelsMigrations, self).setUp()
        self.useFixture(fixtures.LockFixture(self.dialect))
        if not db_test_utils.is_backend_avail(self.dialect):
            raise self.skipTest('%s is not available' % self.dialect)
        if self.dialect == 'sqlite':
            raise self.skipException('sqlite skipped because of model sync '
                                     'issue with BigInteger vs Integer')
        if self.dialect == 'mysql':
            self.useFixture(fixtures.MySQLConfFixture())
        elif self.dialect == 'postgres':
            self.useFixture(fixtures.PostgresConfFixture())
        connect_string = db_test_utils.get_connect_string(self.dialect)
        self.engine = sqlalchemy.create_engine(connect_string)

    def get_engine(self):
        return self.engine

    def get_metadata(self):
        return models.BASE.metadata

    def db_sync(self, engine):
        db_test_utils.run_migration('head', engine)

    def include_object(self, object_, name, type_, reflected, compare_to):
        if type_ == 'table' and name == 'alembic_version':
                return False
        return super(TestModelsMigrations, self).include_object(
            object_, name, type_, reflected, compare_to)

    def filter_metadata_diff(self, diff):
        return list(filter(self.remove_unrelated_errors, diff))

    def remove_unrelated_errors(self, element):
        insp = sqlalchemy.engine.reflection.Inspector.from_engine(
            self.get_engine())
        dialect = self.get_engine().dialect.name
        if isinstance(element, tuple):
            if dialect == 'mysql' and element[0] == 'remove_index':
                table_name = element[1].table.name
                for fk in insp.get_foreign_keys(table_name):
                    if fk['name'] == element[1].name:
                        return False
                cols = [c.name for c in element[1].expressions]
                for col in cols:
                    if col in insp.get_pk_constraint(
                            table_name)['constrained_columns']:
                        return False
        else:
            for modified, _, table, column, _, _, new in element:
                if modified == 'modify_default' and dialect == 'mysql':
                    constrained = insp.get_pk_constraint(table)
                    if column in constrained['constrained_columns']:
                        return False
        return True
