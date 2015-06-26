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

from alembic import op


def upgrade():
    # Add indexes to time columns these are often used for searches and filters
    op.create_index('ix_test_start_time', 'test_runs',
                    ['start_time'])
    op.create_index('ix_test_stop_time', 'test_runs',
                    ['stop_time'])
    op.create_index('ix_run_at', 'runs', ['run_at'])
    # Add compound index on metadata tables key, value columns
    op.create_index('ix_run_key_value', 'run_metadata', ['key', 'value'])
    op.create_index('ix_test_run_key_value', 'test_run_metadata',
                    ['key', 'value'])
    op.create_index('ix_test_key_value', 'test_metadata', ['key', 'value'])
    # Add compound index on test_id and status and start_time, these are common
    # graph query patterns
    op.create_index('ix_test_id_status', 'test_runs', ['test_id', 'status'])
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
