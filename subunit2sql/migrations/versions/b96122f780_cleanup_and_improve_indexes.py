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

"""Cleanup and Improve Indexes

Revision ID: b96122f780
Revises: 2fb76f1a1393
Create Date: 2015-10-14 12:03:26.965724

"""

# revision identifiers, used by Alembic.
revision = 'b96122f780'
down_revision = '2fb76f1a1393'

from alembic import context
from alembic import op
from sqlalchemy.engine import reflection


def upgrade():
    migration_context = context.get_context()
    insp = reflection.Inspector(migration_context.bind)
    test_run_indx = insp.get_indexes('test_runs')
    test_run_indx_names = [x['name'] for x in test_run_indx]
    # Cleanup any duplicate indexes on test_runs
    if 'ix_test_runs_test_id' in test_run_indx_names:
        if 'ix_test_run_test_id' in test_run_indx_names:
            op.drop_index('ix_test_run_test_id', 'test_runs')
    if 'ix_test_runs_run_id' in test_run_indx_names:
        if 'ix_test_run_run_id' in test_run_indx_names:
            op.drop_index('ix_test_run_run_id', 'test_runs')

    # Add an index for test, test_id
    op.create_index('ix_test_ids', 'tests', ['id', 'test_id'], mysql_length=30)


def downgrade():
    pass
