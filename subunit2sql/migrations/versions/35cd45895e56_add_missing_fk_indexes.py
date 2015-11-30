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

"""Add missing fk indexes

Revision ID: 35cd45895e56
Revises: 2822a408bdd0
Create Date: 2015-11-30 15:32:37.218171

"""

# revision identifiers, used by Alembic.
revision = '35cd45895e56'
down_revision = '2822a408bdd0'

from alembic import context
from alembic import op
from sqlalchemy.engine import reflection


def upgrade():
    migration_context = context.get_context()
    insp = reflection.Inspector(migration_context.bind)
    test_run_meta_indx = insp.get_indexes('test_run_metadata')
    run_meta_indx = insp.get_indexes('run_metadata')
    test_meta_indx = insp.get_indexes('test_metadata')
    runs_indx = insp.get_indexes('runs')
    attach_indx = insp.get_indexes('attachments')
    if 'run_id' not in [
        x['column_names'][0] for x in run_meta_indx if len(x) == 1]:
        op.create_index('ix_run_id', 'run_metadata', ['run_id'])
    if 'test_id' not in [
        x['column_names'][0] for x in test_meta_indx if len(x) == 1]:
        op.create_index('ix_test_id', 'test_metadata', ['test_id'])
    if 'test_run_id' not in [
        x['column_names'][0] for x in test_run_meta_indx if len(x) == 1]:
        op.create_index('ix_test_run_id', 'test_run_metadata', ['test_run_id'])
    if 'run_at' not in [
        x['column_names'][0] for x in runs_indx if len(x) == 1]:
        op.create_index('ix_run_at', 'runs', ['run_at'])
    if 'test_run_id' not in [
        x['column_names'][0] for x in attach_indx if len(x) == 1]:
        op.create_index('ix_attach_test_run_id', 'attachments',
                        ['test_run_id'])


def downgrade():
    NotImplementedError()
