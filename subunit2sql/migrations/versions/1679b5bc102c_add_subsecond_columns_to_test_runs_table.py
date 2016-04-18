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

"""Add microsecond columns to test_runs table

Revision ID: 1679b5bc102c
Revises: 5332fe255095
Create Date: 2015-02-27 18:39:13.275801

"""

# revision identifiers, used by Alembic.
revision = '1679b5bc102c'
down_revision = '5332fe255095'

import os

from alembic import context
from alembic import op
from oslo_config import cfg
import sqlalchemy as sa


CONF = cfg.CONF


def upgrade():
    migration_file = ('1679b5bc102c_add_subsecond_columns_to_test_runs_table.'
                      'mysql_upgrade.sql')
    migration_dir = os.path.dirname(os.path.realpath(__file__))
    sql_path = os.path.join(migration_dir, migration_file)
    migration_context = context.get_context()
    if migration_context.dialect.name == 'mysql':
        with open(sql_path, 'r') as sql_file:
            op.execute(sql_file.read())
    else:
        op.add_column('test_runs', sa.Column('start_time_microsecond',
                                             sa.Integer(), default=0))
        op.add_column('test_runs', sa.Column('stop_time_microsecond',
                                             sa.Integer(), default=0))
        if not CONF.disable_microsecond_data_migration:
            bind = op.get_bind()
            metadata = sa.schema.MetaData()
            metadata.bind = bind
            test_runs = sa.Table('test_runs', metadata, autoload=True)
            res = test_runs.select().execute()
            for test_run in res:
                start_micro = test_run[4].microsecond
                stop_micro = test_run[5].microsecond
                values = {'start_time_microsecond': start_micro,
                          'stop_time_microsecond': stop_micro}
                op.execute(test_runs.update().where(
                    test_runs.c.id == test_run[0]).values(values))
            res.close()


def downgrade():
    op.drop_column('test_runs', 'stop_time_microsecond')
    op.drop_column('test_runs', 'start_time_microsecond')
