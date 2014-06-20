# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
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

"""Create metadata tables

Revision ID: 4ca26dac400e
Revises: 163fd5aa1380
Create Date: 2014-06-17 09:53:24.800069

"""

# revision identifiers, used by Alembic.
revision = '4ca26dac400e'
down_revision = '163fd5aa1380'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('run_metadata',
                    sa.Column('id', sa.String(36), primary_key=True,
                              nullable=False),
                    sa.Column('key', sa.String(255)),
                    sa.Column('value', sa.String(255)),
                    sa.Column('run_id', sa.String(36),
                              sa.ForeignKey('runs.id'),
                              nullable=False),
                    mysql_engine='InnoDB')
    op.create_table('test_run_metadata',
                    sa.Column('id', sa.String(36), primary_key=True,
                              nullable=False),
                    sa.Column('key', sa.String(255)),
                    sa.Column('value', sa.String(255)),
                    sa.Column('test_run_id', sa.String(36),
                              sa.ForeignKey('test_runs.id'),
                              nullable=False),
                    mysql_engine='InnoDB')
    op.create_table('test_metadata',
                    sa.Column('id', sa.String(36), primary_key=True,
                              nullable=False),
                    sa.Column('key', sa.String(255)),
                    sa.Column('value', sa.String(255)),
                    sa.Column('test_run_id', sa.String(36),
                              sa.ForeignKey('tests.id'),
                              nullable=False),
                    mysql_engine='InnoDB')


def downgrade():
    op.drop_table('test_metadata')
    op.drop_table('test_run_metadata')
    op.drop_table('run_metadata')
