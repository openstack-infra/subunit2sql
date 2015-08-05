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

import datetime
import uuid

from oslo_db.sqlalchemy import models  # noqa
import sqlalchemy as sa
from sqlalchemy.ext import declarative

BASE = declarative.declarative_base()


class SubunitBase(models.ModelBase):
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
        d = self.__dict__.copy()
        d.pop("_sa_instance_state")
        return d


class Test(BASE, SubunitBase):
    __tablename__ = 'tests'
    __table_args__ = (sa.Index('ix_id', 'id'),
                      sa.Index('ix_test_id', 'test_id'))
    id = sa.Column(sa.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    test_id = sa.Column(sa.String(256))
    run_count = sa.Column(sa.Integer())
    success = sa.Column(sa.Integer())
    failure = sa.Column(sa.Integer())
    run_time = sa.Column(sa.Float())


class Run(BASE, SubunitBase):
    __tablename__ = 'runs'
    __table_args__ = (sa.Index('ix_run_id', 'id'), )
    id = sa.Column(sa.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    skips = sa.Column(sa.Integer())
    fails = sa.Column(sa.Integer())
    passes = sa.Column(sa.Integer())
    run_time = sa.Column(sa.Float())
    artifacts = sa.Column(sa.Text())
    run_at = sa.Column(sa.DateTime,
                       default=datetime.datetime.utcnow)


class TestRun(BASE, SubunitBase):
    __tablename__ = 'test_runs'
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
    start_time = sa.Column(sa.DateTime())
    start_time_microsecond = sa.Column(sa.Integer(), default=0)
    stop_time = sa.Column(sa.DateTime())
    stop_time_microsecond = sa.Column(sa.Integer(), default=0)


class RunMetadata(BASE, SubunitBase):
    __tablename__ = 'run_metadata'
    __table_args__ = (sa.Index('ix_run_metadata_run_id', 'run_id'),)

    id = sa.Column(sa.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    key = sa.Column(sa.String(255))
    value = sa.Column(sa.String(255))
    run_id = sa.Column(sa.String(36), sa.ForeignKey('runs.id'))


class TestRunMetadata(BASE, SubunitBase):
    __tablename__ = 'test_run_metadata'
    __table_args__ = (sa.Index('ix_test_run_metadata_test_run_id',
                               'test_run_id'),)

    id = sa.Column(sa.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    key = sa.Column(sa.String(255))
    value = sa.Column(sa.String(255))
    test_run_id = sa.Column(sa.String(36), sa.ForeignKey('test_runs.id'))


class TestMetadata(BASE, SubunitBase):
    __tablename__ = 'test_metadata'
    __table_args__ = (sa.Index('ix_test_metadata_test_id',
                               'test_id'),)

    id = sa.Column(sa.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    key = sa.Column(sa.String(255))
    value = sa.Column(sa.String(255))
    test_id = sa.Column(sa.String(36), sa.ForeignKey('tests.id'))


class Attachments(BASE, SubunitBase):
    __tablename__ = 'attachments'
    __table_args__ = (sa.Index('ix_attachemnts_id',
                               'test_run_id'),)
    id = sa.Column(sa.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    test_run_id = sa.Column(sa.String(36))
    label = sa.Column(sa.String(255))
    attachment = sa.Column(sa.LargeBinary())
