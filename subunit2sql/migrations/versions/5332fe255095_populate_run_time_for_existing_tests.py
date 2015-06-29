# Copyright 2014 Hewlett-Packard Development Company, L.P.
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

"""Populate run_time for existing tests

Revision ID: 5332fe255095
Revises: 28ac1ba9c3db
Create Date: 2014-10-03 10:23:25.469128

"""

# revision identifiers, used by Alembic.
revision = '5332fe255095'
down_revision = '28ac1ba9c3db'


from oslo_db.sqlalchemy import utils as db_utils

from subunit2sql.db import api as db_api
from subunit2sql.db import models
from subunit2sql import read_subunit


def upgrade():
    query = db_utils.model_query(
        models.Test, db_api.get_session()).filter(
            models.Test.success > 0, models.Test.run_time == None).join(
                models.TestRun).filter_by(
                    status='success').values(models.Test.id,
                                             models.TestRun.start_time,
                                             models.TestRun.stop_time)

    results = {}
    for test_run in query:
        delta = read_subunit.get_duration(test_run[1], test_run[2])
        if test_run[0] in results:
            results[test_run[0]].append(delta)
        else:
            results[test_run[0]] = [delta]

    for test in results:
        avg = float(sum(results[test])) / float(len(results[test]))
        db_api.update_test({'run_time': avg}, test)


def downgrade():
    # NOTE(mtreinish) there is no possible downgrade for this migration, since
    # we won't be able to tell which rows had run_time NULL before this.
    # Ideally this would have been baked into 163fd5aa1380 and the downgrade
    # there of deleting the column would have covered this. But, because that
    # wasn't included as a part of the released migration we can't change it.
    pass
