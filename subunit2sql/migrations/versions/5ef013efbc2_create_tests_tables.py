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

"""create tests tables

Revision ID: 5ef013efbc2
Revises: None
Create Date: 2014-06-08 11:18:41.529268

"""

# revision identifiers, used by Alembic.
revision = '5ef013efbc2'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('tests',
                    sa.Column('id', sa.String(36), primary_key=True,
                              nullable=False),
                    sa.Column('test_id', sa.String(256), nullable=False),
                    sa.Column('run_count', sa.Integer()),
                    sa.Column('success', sa.Integer()),
                    sa.Column('failure', sa.Integer()),
                    mysql_engine='InnoDB')


def downgrade():
    op.drop_table('tables')
