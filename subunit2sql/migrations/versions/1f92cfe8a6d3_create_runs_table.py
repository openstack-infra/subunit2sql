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

"""create runs table

Revision ID: 1f92cfe8a6d3
Revises: 5ef013efbc2
Create Date: 2014-06-08 14:29:17.622700

"""

# revision identifiers, used by Alembic.
revision = '1f92cfe8a6d3'
down_revision = '5ef013efbc2'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('runs',
                    sa.Column('id', sa.String(36), primary_key=True),
                    sa.Column('skips', sa.Integer()),
                    sa.Column('fails', sa.Integer()),
                    sa.Column('passes', sa.Integer()),
                    sa.Column('run_time', sa.Float()),
                    sa.Column('artifacts', sa.Text()),
                    mysql_engine='InnoDB')


def downgrade():
    op.drop_table('runs')
