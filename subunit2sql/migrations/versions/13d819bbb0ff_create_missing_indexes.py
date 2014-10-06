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

from alembic import op


def upgrade():
    op.create_index('ix_test_id', 'tests', ['test_id'])
    op.create_index('ix_test_run_test_id', 'test_runs', ['test_id'])
    op.create_index('ix_test_run_run_id', 'test_runs', ['run_id'])
    op.create_unique_constraint('uq_test_runs', 'test_runs',
                                ['test_id', 'run_id'])


def downgrade():
    op.drop_constraint('uq_test_runs', 'test_runs')
    op.drop_index('ix_test_id', 'tests')
    op.drop_index('ix_test_run_test_id', 'test_runs')
    op.drop_index('ix_test_run_run_id', 'test_runs')
