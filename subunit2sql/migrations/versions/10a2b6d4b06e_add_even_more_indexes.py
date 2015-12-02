# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Add even more indexes

Revision ID: 10a2b6d4b06e
Revises: 35cd45895e56
Create Date: 2015-12-01 18:19:11.328298

"""

# revision identifiers, used by Alembic.
revision = '10a2b6d4b06e'
down_revision = '35cd45895e56'

from alembic import op


def upgrade():
    with op.batch_alter_table('run_metadata') as batch_op:
        batch_op.create_unique_constraint('uq_run_metadata',
                                          ['run_id', 'key', 'value'])
    with op.batch_alter_table('test_metadata') as batch_op:
        batch_op.create_unique_constraint('uq_test_metadata',
                                          ['test_id', 'key', 'value'])
    with op.batch_alter_table('test_run_metadata') as batch_op:
        batch_op.create_unique_constraint('uq_test_run_metadata',
                                          ['test_run_id', 'key', 'value'])


def downgrade():
    NotImplementedError()
