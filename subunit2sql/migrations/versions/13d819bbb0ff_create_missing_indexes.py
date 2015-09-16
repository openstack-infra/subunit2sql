# Copyright 2014 Hewlett-Packard Development Company, L.P.
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

"""create missing indexes

Revision ID: 13d819bbb0ff
Revises: 4ca26dac400e
Create Date: 2014-06-20 21:27:01.629724

"""

# revision identifiers, used by Alembic.
revision = '13d819bbb0ff'
down_revision = '4ca26dac400e'

from alembic import context
from alembic import op
from sqlalchemy.engine import reflection


def upgrade():
    migration_context = context.get_context()
    insp = reflection.Inspector(migration_context.bind)
    test_indx = insp.get_indexes('tests')
    test_indx_names = [x['name'] for x in test_indx]
    test_indx_columns = [x['column_names'][0] for x in test_indx
                         if len(x) == 1]
    test_run_indx = insp.get_indexes('test_runs')
    test_run_indx_names = [x['name'] for x in test_run_indx]
    test_run_indx_columns = [x['column_names'][0] for x in test_run_indx
                             if len(x) == 1]
    if ('ix_test_id' not in test_indx_names and
        'test_id' not in test_indx_columns):
        op.create_index('ix_test_id', 'tests', ['test_id'], mysql_length=30)

    # remove auto created indexes (sqlite only)
    # note the name is with test_runs not test_run
    if migration_context.dialect.name == 'sqlite':
        if 'ix_test_runs_test_id' in test_run_indx_names:
            op.drop_index('ix_test_runs_test_id', 'test_runs')
        if 'ix_test_runs_run_id' in test_run_indx_names:
            op.drop_index('ix_test_runs_run_id', 'test_runs')

    with op.batch_alter_table('test_runs') as batch_op:
        batch_op.create_unique_constraint('uq_test_runs',
                                          ['test_id', 'run_id'])

    if ('ix_test_run_test_id' not in test_run_indx_names and
        'test_id' not in test_run_indx_columns):
        op.create_index('ix_test_run_test_id', 'test_runs', ['test_id'])
    if ('ix_test_run_run_id' not in test_run_indx_names and
        'run_id' not in test_run_indx_columns):
        op.create_index('ix_test_run_run_id', 'test_runs', ['run_id'])


def downgrade():
    op.drop_constraint('uq_test_runs', 'test_runs')
    op.drop_index('ix_test_id', 'tests')
    op.drop_index('ix_test_run_test_id', 'test_runs')
    op.drop_index('ix_test_run_run_id', 'test_runs')
