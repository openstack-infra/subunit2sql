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

"""Create avg runtime column in test table

Revision ID: 163fd5aa1380
Revises: 3db7b49816d5
Create Date: 2014-06-16 15:45:19.221576

"""

# revision identifiers, used by Alembic.
revision = '163fd5aa1380'
down_revision = '3db7b49816d5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('tests', sa.Column('run_time', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('tests', 'run_time')
