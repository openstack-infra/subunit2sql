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

import uuid

from oslo.db.sqlalchemy import models  # noqa
import sqlalchemy as sa


class SubunitBase(models.ModelBase, models.TimestampMixin):
    """Base class for Subunit Models."""
    __table_args__ = {'mysql_engine': 'InnoDB'}
    __table_initialized__ = False

    def save(self, session=None):
        from subunit2sql.db import api as db_api
        super(SubunitBase, self).save(session or db_api.get_session())

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()

    def to_dict(self):
        return self.__dict__.copy()


class Test(SubunitBase):
    __tablename__ = 'tests'
    __table_args__ = ()
    id = sa.Column(sa.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    test_id = sa.String(256)
    run_count = sa.Integer()
    success = sa.Integer()
    failure = sa.Integer()


class Run(SubunitBase):
    __tablename__ = 'runs'
    __table_args__ = ()
    id = sa.Column(sa.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    skips = sa.Integer()
    fails = sa.Integer()
    passes = sa.Integer()
    run_time = sa.Integer()
    artifacts = sa.Text()


class TestRun(SubunitBase):
    __tablename__ = 'test_run'
    __table_args__ = (sa.Index('ix_test_run_test_id', 'test_id'),
                      sa.Index('ix_test_run_run_id', 'run_id'),
                      sa.UniqueConstraint('test_id', 'run_id',
                                          name='ix_test_run_test_id_run_id'))

    id = sa.Column(sa.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    test_id = sa.Column(sa.String(36), sa.ForeignKey('tests.id'),
                        nullable=False)
    run_id = sa.Column(sa.String(36), sa.ForeignKey('runs.id'), nullable=False)
    status = sa.Column(sa.String(256))
    start_time = sa.DateTime()
    end_time = sa.DateTime()
