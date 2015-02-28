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

"""Add microsecond columns to test_runs table

Revision ID: 1679b5bc102c
Revises: 5332fe255095
Create Date: 2015-02-27 18:39:13.275801

"""

# revision identifiers, used by Alembic.
revision = '1679b5bc102c'
down_revision = '5332fe255095'

from alembic import op
from oslo.config import cfg
from oslo.db.sqlalchemy import utils as db_utils
import sqlalchemy as sa

from subunit2sql.db import api as db_api
from subunit2sql.db import models


CONF = cfg.CONF


def upgrade():
    op.add_column('test_runs', sa.Column('start_time_microsecond',
                                         sa.Integer(), default=0))
    op.add_column('test_runs', sa.Column('stop_time_microsecond',
                                         sa.Integer(), default=0))
    if not CONF.disable_microsecond_data_migration:
        session = db_api.get_session()
        query = db_utils.model_query(models.TestRun, session).values(
            models.TestRun.id, models.TestRun.start_time,
            models.TestRun.stop_time)
        for test_run in query:
            start_micro = test_run[1].microsecond
            stop_micro = test_run[2].microsecond
            values = {'start_time_microsecond': start_micro,
                      'stop_time_microsecond': stop_micro}
            db_api.update_test_run(values, test_run[0], session)
        session.close()


def downgrade():
    op.drop_column('test_runs', 'stop_time_microsecond')
    op.drop_column('test_runs', 'start_time_microsecond')
