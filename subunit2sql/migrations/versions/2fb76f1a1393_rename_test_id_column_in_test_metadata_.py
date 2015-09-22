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

"""Rename test_id column in test_metadata table

Revision ID: 2fb76f1a1393
Revises: 1ff737bef438
Create Date: 2015-09-22 10:12:03.820855

"""

# revision identifiers, used by Alembic.
revision = '2fb76f1a1393'
down_revision = '1ff737bef438'

from alembic import context
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import reflection


def upgrade():
    migration_context = context.get_context()
    insp = reflection.Inspector(migration_context.bind)
    indx_names = [x['name'] for x in insp.get_indexes('test_metadata')]
    # Prempt duplicate index creation on sqlite
    if migration_context.dialect.name == 'sqlite':
        if 'ix_test_key_value' in indx_names:
            op.drop_index('ix_test_key_value', 'test_metadata')
    # NOTE(mtreinish) on some mysql versions renaming the column with a fk
    # constraint errors out so, delete it before the rename and add it back
    # after
    if migration_context.dialect.name == 'mysql':
        op.drop_constraint('test_metadata_ibfk_1', 'test_metadata',
                           'foreignkey')
    with op.batch_alter_table('test_metadata') as batch_op:
        batch_op.alter_column('test_run_id',
                              existing_type=sa.String(36),
                              existing_nullable=False,
                              new_column_name='test_id')
    if migration_context.dialect.name == 'mysql':
        op.create_foreign_key('test_metadata_ibfk_1', 'test_metadata',
                              'tests', ["test_id"], ['id'])


def downgrade():
    pass
