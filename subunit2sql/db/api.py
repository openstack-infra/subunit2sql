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
    """Get a new sqlalchemy Session instance

    :param bool autocommit: Enable autocommit mode for the session.
    :param bool expire_on_commit: Expire the session on commit defaults False.
    """
    facade = _create_facade_lazily()
    return facade.get_session(autocommit=autocommit,
                              expire_on_commit=expire_on_commit)


def create_test(test_id, run_count=0, success=0, failure=0, run_time=0.0,
                session=None):
    """Create a new test record in the database.

    This method is used to add a new test in the database. Tests are used to
    track the run history of a unique test over all runs.

    :param str test_id: test_id identifying the test
    :param int run_count: total number or runs defaults to 0
    :param int success: number of successful runs defaults 0
    :param int failure: number of failed runs defaults to 0
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return: The test object stored in the DB
    :rtype: subunit2sql.models.Test

    :raises InvalidRunCount: if the run_count doesn't equal the sum of the
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
    """Update an individual test with new data.

    This method will take a dictionary of fields to update for a specific test.
    If a field is ommited it will not be changed in the DB.

    :param dict values: dict of values to update the test with. The key is the
                        column name and the value is the new value to be stored
                        in the DB
    :param str test_id: the uuid of the test to update. (value of the id column
                        for the row to be updated)
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The updated test object stored in the DB
    :rtype: subunit2sql.models.Test
    """
    session = session or get_session()
    with session.begin():
        test = get_test_by_id(test_id, session)
        test.update(values)
    return test


def create_run(skips=0, fails=0, passes=0, run_time=0, artifacts=None,
               id=None, session=None):
    """Create a new run record in the database

    :param int skips: total number of skiped tests defaults to 0
    :param int fails: total number of failed tests defaults to 0
    :param int passes: total number of passed tests defaults to 0
    :param float run_time: total run timed defaults to 0
    :param str artifacts: A link to any artifacts from the test run defaults to
                          None
    :param str id: the run id for the new run, needs to be a unique value
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The run object stored in the DB
    :rtype: subunit2sql.models.Run
    """
    run = models.Run()
    if id:
        run.id = id
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
    """Update an individual run with new data.

    This method will take a dictionary of fields to update for a specific run.
    If a field is omitted it will not be changed in the DB.

    :param dict values: dict of values to update the test with. The key is the
                        column name and the value is the new value to be stored
                        in the DB
    :param str run_id: the uuid of the run to update. (value of the id column
                        for the row to be updated)
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The updated run object stored in the DB
    :rtype: subunit2sql.models.Run
    """
    session = session or get_session()
    with session.begin():
        run = get_run_by_id(run_id, session)
        run.update(values)
    return run


def add_run_metadata(meta_dict, run_id, session=None):
    """Add a metadata key value pairs for a specific run.

    This method will take a dictionary and store key value pair metadata in the
    DB associated with the specified run.

    :param dict meta_dict: a dictionary which will generate a separate key
                           value pair row associated with the run_id
    :param str run_id: the uuid of the run to update. (value of the id column
                       for the row to be updated)
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of created metadata objects
    :rtype: subunit2sql.models.RunMeta
    """

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

    This method creates a new record in the database

    :param str test_id: uuid for test that was run
    :param str run_id: uuid for run that this was a member of
    :param str status: status of the test run, normally success, fail, or skip
    :param datetime.Datetime start_time: when the test was started defaults to
                                         None
    :param datetime.Datetime end_time: when the test was finished defaults to
                                       None
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The test_run object stored in the DB
    :rtype: subunit2sql.models.TestRun
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
    """Add a metadata key value pairs for a specific run.

    This method will take a dictionary and store key value pair metadata in the
    DB associated with the specified run.

    :param dict meta_dict: a dictionary which will generate a separate key
                           value pair row associated with the test_run_id
    :param str test_run_id: the uuid of the test_run to update. (value of the
                            id column for the row to be updated)
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of created metadata objects
    :rtype: subunit2sql.models.TestRunMeta
    """
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
    """Return all run metadata objects for associated with a given run.

    :param str test_run_id: The uuid of the test_run to get all the metadata
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of created metadata objects
    :rtype: subunit2sql.models.RunMeta
    """
    session = session or get_session()
    query = db_utils.model_query(models.TestRunMetadata, session).filter_by(
        test_run_id=test_run_id)
    return query.all()


def get_all_tests(session=None):
    """Return all tests from the DB.

    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of test objects
    :rtype: subunit2sql.models.Test
    """
    session = session or get_session()
    query = db_utils.model_query(models.Test, session)
    return query.all()


def get_all_runs(session=None):
    """Return all runs from the DB.

    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of run objects
    :rtype: subunit2sql.models.Run
    """
    session = session or get_session()
    query = db_utils.model_query(models.Run, session)
    return query.all()


def get_all_test_runs(session=None):
    """Return all test runs from the DB.

    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of test run objects
    :rtype: subunit2sql.models.TestRun
    """
    session = session or get_session()
    query = db_utils.model_query(models.TestRun, session)
    return query.all()


def get_latest_run(session=None):
    """Return the most recently created run from the DB.

    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The latest run object
    :rtype: subunit2sql.models.Run
    """
    session = session or get_session()
    query = db_utils.model_query(models.Run, session).order_by(
        models.Run.run_at.desc())
    return query.first()


def get_failing_from_run(run_id, session=None):
    """Return the set of failing test_ids for a give run.

    This method will return all the test run objects that failed during the
    specified run.

    :param str run_id: uuid for run tho find all the failing runs
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of failing test runs for the given run
    :rtype: subunit2sql.models.TestRun
    """
    session = session or get_session()
    query = db_utils.model_query(models.TestRun, session).filter_by(
        run_id=run_id, status='fail')
    return query.all()


def get_test_by_id(id, session=None):
    """Get an individual test by it's uuid.

    :param str id: The uuid for the test (the id field in the DB)
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The specified test object
    :rtype: subunit2sql.models.Test
    """
    session = session or get_session()
    test = db_utils.model_query(models.Test, session).filter_by(
        id=id).first()
    return test


def get_test_by_test_id(test_id, session=None):
    """Get an individual test by it's test_id.

    :param str test_id: The id (aka the test name) for the test (the test_id
                        field in the DB)
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The specified test object
    :rtype: subunit2sql.models.Test
    """
    session = session or get_session()
    test = db_utils.model_query(models.Test, session).filter_by(
        test_id=test_id).first()
    return test


def get_run_by_id(id, session=None):
    """Get an individual run by it's uuid.

    :param str id: The uuid for the run (the id field in the DB)
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The specified run object
    :rtype: subunit2sql.models.Run
    """
    session = session or get_session()
    run = db_utils.model_query(models.Run, session).filter_by(id=id).first()
    return run


def get_test_run_by_id(test_run_id, session=None):
    """Get an individual test run by it's uuid.

    :param str test_run_id: The uuid for the test run (the id field in the DB)
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The specified test run object
    :rtype: subunit2sql.models.TestRun
    """
    session = session or get_session()
    test_run = db_utils.model_query(models.TestRun, session=session).filter_by(
        id=test_run_id).first()
    return test_run


def get_test_runs_by_test_id(test_id, session=None):
    """Get all test runs for a specific test.

    :param str test_id: The test's uuid (the id column in the test table) which
                        to get all test runs for
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of test run objects for the specified test
    :rtype: subunit2sql.models.TestRun
    """
    session = session or get_session()
    test_runs = db_utils.model_query(models.TestRun,
                                     session=session).filter_by(
        test_id=test_id).all()
    return test_runs


def get_test_runs_by_run_id(run_id, session=None):
    """Get all test runs for a specific run.

    :param str run_id: The run's uuid (the id column in the run table) which to
                        get all test runs for
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of test run objects for the specified test
    :rtype: subunit2sql.models.TestRun
    """
    session = session or get_session()
    test_runs = db_utils.model_query(models.TestRun,
                                     session=session).filter_by(
        run_id=run_id).all()
    return test_runs


def get_test_run_duration(test_run_id, session=None):
    """Get the run duration for a specifc test_run.

    :param str test_run_id: The test_run's uuid (the id column in the test_run
                            table) to get the duration of
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The duration of the test run in secs
    :rtype: float
    """
    session = session or get_session()
    test_run = get_test_run_by_id(test_run_id, session)
    return read_subunit.get_duration(test_run.start_time, test_run.stop_time)


def get_tests_from_run_id(run_id, session=None):
    """Return the all tests for a specific run.

    This method returns a list of all the Test objects that were executed as
    part of a specified run.

    :param str run_id: The run's uuid (the id column in the run table) which to
                       get all tests for
    :param session: optional session object if one isn't provided a new session

    :return list: The list of test objects for the specified test
    :rtype: subunit2sql.models.Test
    """
    session = session or get_session()
    query = db_utils.model_query(models.Test, session=session).join(
        models.TestRun).filter_by(run_id=run_id)
    return query.all()


def get_tests_run_dicts_from_run_id(run_id, session=None):
    """Returns all the stored data about test runs for a specific run.

    This method returns a dictionary containing all the information stored in
    the database regarding the test_runs. This includes the test_id from the
    tests table, all the stored key value pair metadata from the
    test_run_metadata table, and from the test_runs table the status,
    start_time, and stop_time.

    :param str run_id: The run's uuid (the id column in the run table) which to
                       use to select it's run ids to collect information for.
    :param session: optional session object if one isn't provided a new session

    :return dict: A dictionary with the test_id from the tests for keys that
                  contains all the stored information about the test_runs.
    """
    session = session or get_session()
    query = db_utils.model_query(models.Test, session=session).join(
        models.TestRun).filter_by(run_id=run_id).join(
            models.TestRunMetadata).values(models.Test.test_id,
                                           models.TestRun.status,
                                           models.TestRun.start_time,
                                           models.TestRun.stop_time,
                                           models.TestRunMetadata.key,
                                           models.TestRunMetadata.value)
    test_runs = {}
    for test_run in query:
        if test_run[0] not in test_runs:
            test_runs[test_run[0]] = {
                'status': test_run[1],
                'start_time': test_run[2],
                'stop_time': test_run[3],
            }
            if test_run[4]:
                test_runs[test_run[0]]['metadata'] = {test_run[4]: test_run[5]}
        else:
            if test_run[4]:
                test_runs[test_run[0]]['metadata'][test_run[4]] = test_run[5]
    return test_runs
