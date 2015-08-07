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

"""Add indexes on common search fields

Revision ID: 1ff737bef438
Revises: 487f279b8c78
Create Date: 2015-06-25 14:27:10.465845

"""

# revision identifiers, used by Alembic.
revision = '1ff737bef438'
down_revision = '487f279b8c78'

from alembic import context
from alembic import op
from sqlalchemy.engine import reflection


def upgrade():
    migration_context = context.get_context()
    insp = reflection.Inspector(migration_context.bind)
    run_indx = insp.get_indexes('runs')
    run_indx_names = [x['name'] for x in run_indx]
    test_run_indx = insp.get_indexes('test_runs')
    test_run_indx_names = [x['name'] for x in test_run_indx]
    test_run_metad_indx = insp.get_indexes('test_run_metadata')
    test_run_metad_indx_names = [x['name'] for x in test_run_metad_indx]
    run_metad_indx = insp.get_indexes('run_metadata')
    run_metad_indx_names = [x['name'] for x in run_metad_indx]
    test_metad_indx = insp.get_indexes('test_metadata')
    test_metad_indx_names = [x['name'] for x in test_metad_indx]

    # Add indexes to time columns these are often used for searches and filters
    if 'ix_test_start_time' not in test_run_indx_names:
        op.create_index('ix_test_start_time', 'test_runs',
                        ['start_time'])
    if 'ix_test_stop_time' not in test_run_indx_names:
        op.create_index('ix_test_stop_time', 'test_runs',
                        ['stop_time'])
    if 'ix_run_at' not in run_indx_names:
        op.create_index('ix_run_at', 'runs', ['run_at'])
    # Add compound index on metadata tables key, value columns
    if 'ix_run_key_value' not in run_metad_indx_names:
        op.create_index('ix_run_key_value', 'run_metadata', ['key', 'value'])
    if 'ix_test_run_key_value' not in test_run_metad_indx_names:
        op.create_index('ix_test_run_key_value', 'test_run_metadata',
                        ['key', 'value'])
    if 'ix_test_key_value' not in test_metad_indx_names:
        op.create_index('ix_test_key_value', 'test_metadata', ['key', 'value'])
    # Add compound index on test_id and status and start_time, these are common
    # graph query patterns
    if 'ix_test_id_status' not in test_run_indx_names:
        op.create_index('ix_test_id_status', 'test_runs',
                        ['test_id', 'status'], mysql_length={'status': 30})
    if 'ix_test_id_start_time' not in test_run_indx_names:
        op.create_index('ix_test_id_start_time', 'test_runs', ['test_id',
                                                               'start_time'])


def downgrade():
    op.drop_index('ix_test_start_time', 'test_runs')
    op.drop_index('ix_test_stop_time', 'test_runs')
    op.drop_index('ix_run_at', 'runs')
    op.drop_index('ix_run_key_value', 'run_metadata')
    op.drop_index('ix_test_run_key_value', 'test_run_metadata')
    op.drop_index('ix_test_key_value', 'test_metadata')
    op.drop_index('ix_test_id_status', 'test_runs')
    op.drop_index('ix_test_id_start_time', 'test_runs')
