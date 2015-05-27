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

"""Add Attachments Table

Revision ID: 487f279b8c78
Revises: 1679b5bc102c
Create Date: 2015-05-27 15:18:21.653867

"""

# revision identifiers, used by Alembic.
revision = '487f279b8c78'
down_revision = '1679b5bc102c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('attachments',
                    sa.Column('id', sa.String(36), primary_key=True,
                              nullable=False),
                    sa.Column('test_run_id', sa.String(36),
                              sa.ForeignKey('test_runs.id'), nullable=False),
                    sa.Column('label', sa.String(255)),
                    sa.Column('attachment', sa.LargeBinary()),
                    mysql_engine='InnoDB')


def downgrade():
    op.drop_table('attachments')
