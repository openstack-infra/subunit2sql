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

from oslo.config import cfg
from oslo.db.sqlalchemy import session as db_session
from oslo.db.sqlalchemy import utils as db_utils

from subunit2sql.db import models
from subunit2sql import exceptions
from subunit2sql import read_subunit

CONF = cfg.CONF

DAY_SECONDS = 60 * 60 * 24

_FACADE = None


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = db_session.EngineFacade(
            CONF.database.connection,
            **dict(CONF.database.iteritems()))
    return _FACADE


def get_session(autocommit=True, expire_on_commit=False):
    facade = _create_facade_lazily()
    return facade.get_session(autocommit=autocommit,
                              expire_on_commit=expire_on_commit)


def create_test(test_id, run_count=0, success=0, failure=0, run_time=0.0,
                session=None):
    """Create a new test record in the database

    :param test_id: test_id identifying the test
    :param run_count: total number or runs
    :param success: number of successful runs
    :param failure: number of failed runs

    Raises InvalidRunCount if the run_count doesn't equal the sum of the
    successes and failures.
    """
    if run_count != success + failure:
        raise exceptions.InvalidRunCount()
    test = models.Test()
    test.test_id = test_id
    test.run_count = run_count
    test.success = success
    test.failure = failure
    test.run_time = run_time
    session = session or get_session()
    with session.begin():
        session.add(test)
    return test


def update_test(values, test_id, session=None):
    session = session or get_session()
    with session.begin():
        test = get_test_by_id(test_id, session)
        test.update(values)
    return test


def create_run(skips=0, fails=0, passes=0, run_time=0, artifacts=None,
               session=None):
    """Create a new run record in the database

    :param skips: total number of skiped tests
    :param fails: total number of failed tests
    :param passes: total number of passed tests
    :param run_time: total run time
    :param artifacts: A link to any artifacts from the test run
    """
    run = models.Run()
    run.skips = skips
    run.fails = fails
    run.passes = passes
    run.run_time = run_time
    run.artifacts = artifacts
    session = session or get_session()
    with session.begin():
        session.add(run)
    return run


def update_run(values, run_id, session=None):
    session = session or get_session()
    with session.begin():
        run = get_run_by_id(run_id, session)
        run.update(values)
    return run


def add_run_metadata(meta_dict, run_id, session=None):
    metadata = []
    for key, value in meta_dict.items():
        meta = models.RunMetadata()
        meta.key = key
        meta.value = value
        meta.run_id = run_id
        with session.begin():
            session.add(meta)
        metadata.append(meta)
    return metadata


def create_test_run(test_id, run_id, status, start_time=None,
                    end_time=None, session=None):
    """Create a new test run record in the database

    :param test_id: uuid for test that was run
    :param run_id: uuid for run that this was a member of
    :param start_time: when the test was started
    :param end_time: when the test was finished
    """
    test_run = models.TestRun()
    test_run.test_id = test_id
    test_run.run_id = run_id
    test_run.status = status
    test_run.stop_time = end_time.replace(tzinfo=None)
    test_run.start_time = start_time.replace(tzinfo=None)
    session = session or get_session()
    with session.begin():
        session.add(test_run)
    return test_run


def add_test_run_metadata(meta_dict, test_run_id, session=None):
    metadata = []
    for key, value in meta_dict.items():
        meta = models.TestRunMetadata()
        meta.key = key
        meta.value = value
        meta.test_run_id = test_run_id
        session = session or get_session()
        with session.begin():
            session.add(meta)
        metadata.append(meta)
    return metadata


def get_test_run_metadata(test_run_id, session=None):
    session = session or get_session()
    query = db_utils.model_query(models.TestRunMetadata, session).filter_by(
        test_run_id=test_run_id)
    return query.all()


def get_all_tests(session=None):
    session = session or get_session()
    query = db_utils.model_query(models.Test, session)
    return query.all()


def get_all_runs(session=None):
    session = session or get_session()
    query = db_utils.model_query(models.Run, session)
    return query.all()


def get_all_test_runs(session=None):
    session = session or get_session()
    query = db_utils.model_query(models.TestRun, session)
    return query.all()


def get_latest_run(session=None):
    session = session or get_session()
    query = db_utils.model_query(models.Run, session).order_by(
        models.Run.run_at.desc())
    return query.first()


def get_failing_from_run(run_id, session=None):
    session = session or get_session()
    query = db_utils.model_query(models.TestRun, session).filter_by(
        run_id=run_id, status='fail')
    return query.all()


def get_test_by_id(id, session=None):
    session = session or get_session()
    test = db_utils.model_query(models.Test, session).filter_by(
        id=id).first()
    return test


def get_test_by_test_id(test_id, session=None):
    session = session or get_session()
    test = db_utils.model_query(models.Test, session).filter_by(
        test_id=test_id).first()
    return test


def get_run_by_id(id, session=None):
    session = session or get_session()
    run = db_utils.model_query(models.Run, session).filter_by(id=id).first()
    return run


def get_test_run_by_id(test_run_id, session=None):
    session = session or get_session()
    test_run = db_utils.model_query(models.TestRun, session=session).filter_by(
        id=test_run_id).first()
    return test_run


def get_test_runs_by_test_id(test_id, session=None):
    session = session or get_session()
    test_runs = db_utils.model_query(models.TestRun,
                                     session=session).filter_by(
        test_id=test_id).all()
    return test_runs


def get_test_runs_by_run_id(run_id, session=None):
    session = session or get_session()
    test_runs = db_utils.model_query(models.TestRun,
                                     session=session).filter_by(
        run_id=run_id).all()
    return test_runs


def get_test_run_duration(test_run_id, session=None):
    session = session or get_session()
    test_run = get_test_run_by_id(test_run_id, session)
    return read_subunit.get_duration(test_run.start_time, test_run.stop_time)
