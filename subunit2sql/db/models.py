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
import six
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
        return list(self.__dict__.keys())

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
    __table_args__ = (sa.Index('ix_test_ids', 'id', 'test_id',
                               mysql_length={'test_id': 30}),
                      sa.Index('ix_tests_test_id', 'test_id',
                               mysql_length=30))
    id = sa.Column(sa.BigInteger, primary_key=True)
    test_id = sa.Column(sa.String(256),
                        nullable=False)
    run_count = sa.Column(sa.Integer())
    success = sa.Column(sa.Integer())
    failure = sa.Column(sa.Integer())
    run_time = sa.Column(sa.Float())


class Run(BASE, SubunitBase):
    __tablename__ = 'runs'
    __table_args__ = (sa.Index('ix_run_at', 'run_at'),
                      sa.Index('ix_run_uuid', 'uuid'))
    uuid = sa.Column(sa.String(36),
                     default=lambda: six.text_type(uuid.uuid4()))
    id = sa.Column(sa.BigInteger, primary_key=True)
    skips = sa.Column(sa.Integer())
    fails = sa.Column(sa.Integer())
    passes = sa.Column(sa.Integer())
    run_time = sa.Column(sa.Float())
    artifacts = sa.Column(sa.Text())
    run_at = sa.Column(sa.DateTime,
                       default=datetime.datetime.utcnow)


class TestRun(BASE, SubunitBase):
    __tablename__ = 'test_runs'
    __table_args__ = (sa.Index('ix_test_id_status', 'test_id', 'status'),
                      sa.Index('ix_test_id_start_time', 'test_id',
                               'start_time'),
                      sa.Index('ix_test_runs_test_id', 'test_id'),
                      sa.Index('ix_test_runs_run_id', 'run_id'),
                      sa.Index('ix_test_runs_start_time', 'start_time'),
                      sa.Index('ix_test_runs_stop_time', 'stop_time'),
                      sa.UniqueConstraint('test_id', 'run_id',
                                          name='uq_test_runs'))

    id = sa.Column(sa.BigInteger, primary_key=True)
    test_id = sa.Column(sa.BigInteger)
    run_id = sa.Column(sa.BigInteger)
    status = sa.Column(sa.String(256))
    start_time = sa.Column(sa.DateTime())
    start_time_microsecond = sa.Column(sa.Integer(), default=0)
    stop_time = sa.Column(sa.DateTime())
    stop_time_microsecond = sa.Column(sa.Integer(), default=0)
    test = sa.orm.relationship(Test, backref=sa.orm.backref('test_run_test'),
                               foreign_keys=test_id,
                               primaryjoin=test_id == Test.id)
    run = sa.orm.relationship(Run, backref=sa.orm.backref('test_run_run'),
                              foreign_keys=run_id,
                              primaryjoin=run_id == Run.id)


class RunMetadata(BASE, SubunitBase):
    __tablename__ = 'run_metadata'
    __table_args__ = (sa.Index('ix_run_key_value', 'key', 'value'),
                      sa.Index('ix_run_id', 'run_id'),
                      sa.UniqueConstraint('run_id', 'key', 'value',
                                          name='uq_run_metadata'))

    id = sa.Column(sa.BigInteger, primary_key=True)
    key = sa.Column(sa.String(255))
    value = sa.Column(sa.String(255))
    run_id = sa.Column(sa.BigInteger)
    run = sa.orm.relationship(Run, backref='run', foreign_keys=run_id,
                              primaryjoin=run_id == Run.id)


class TestRunMetadata(BASE, SubunitBase):
    __tablename__ = 'test_run_metadata'
    __table_args__ = (sa.Index('ix_test_run_key_value', 'key', 'value'),
                      sa.Index('ix_test_run_id', 'test_run_id'),
                      sa.UniqueConstraint('test_run_id', 'key', 'value',
                                          name='uq_test_run_metadata'))

    id = sa.Column(sa.BigInteger, primary_key=True)
    key = sa.Column(sa.String(255))
    value = sa.Column(sa.String(255))
    test_run_id = sa.Column(sa.BigInteger)
    test_run = sa.orm.relationship(TestRun,
                                   backref=sa.orm.backref('test_run_meta'),
                                   foreign_keys=test_run_id,
                                   primaryjoin=test_run_id == TestRun.id)


class TestMetadata(BASE, SubunitBase):
    __tablename__ = 'test_metadata'
    __table_args__ = (sa.Index('ix_test_key_value', 'key', 'value'),
                      sa.Index('ix_test_id', 'test_id'),
                      sa.UniqueConstraint('test_id', 'key', 'value',
                                          name='uq_test_metadata'))

    id = sa.Column(sa.BigInteger, primary_key=True)
    key = sa.Column(sa.String(255))
    value = sa.Column(sa.String(255))
    test_id = sa.Column(sa.BigInteger)
    test = sa.orm.relationship(Test, backref='test', foreign_keys=test_id,
                               primaryjoin=test_id == Test.id)


class Attachments(BASE, SubunitBase):
    __tablename__ = 'attachments'
    __table_args__ = (sa.Index('ix_attach_test_run_id', 'test_run_id'),)
    id = sa.Column(sa.BigInteger, primary_key=True)
    test_run_id = sa.Column(sa.BigInteger)
    label = sa.Column(sa.String(255))
    attachment = sa.Column(sa.LargeBinary())
    test_run = sa.orm.relationship(TestRun, backref='test_run_attach',
                                   foreign_keys=test_run_id,
                                   primaryjoin=test_run_id == TestRun.id)
