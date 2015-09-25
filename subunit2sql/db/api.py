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

import collections
import datetime

from oslo_config import cfg
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils as db_utils
import sqlalchemy
from sqlalchemy.engine.url import make_url

import logging

from subunit2sql.db import models
from subunit2sql import exceptions
from subunit2sql import read_subunit

CONF = cfg.CONF
CONF.register_cli_opt(cfg.BoolOpt('verbose', short='v', default=False,
                                  help='Verbose output including logging of '
                                       'SQL statements'))

DAY_SECONDS = 60 * 60 * 24

_facades = {}


def _create_facade_lazily():
    global _facades
    db_url = make_url(CONF.database.connection)
    db_backend = db_url.get_backend_name()
    facade = _facades.get(db_backend)
    if facade is None:
        facade = db_session.EngineFacade(
            CONF.database.connection,
            **dict(CONF.database.iteritems()))
        _facades[db_backend] = facade
    return facade


def get_session(autocommit=True, expire_on_commit=False):
    """Get a new sqlalchemy Session instance

    :param bool autocommit: Enable autocommit mode for the session.
    :param bool expire_on_commit: Expire the session on commit defaults False.
    """
    facade = _create_facade_lazily()
    session = facade.get_session(autocommit=autocommit,
                                 expire_on_commit=expire_on_commit)

    # if --verbose was specified, turn on SQL logging
    # note that this is done after the session has been initialized so that
    # we can override the default sqlalchemy logging
    if CONF.get('verbose', False):
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    return session


def _filter_runs_by_date(query, start_date=None, stop_date=None):
    # Helper to apply a data range filter to a query on Run table
    if isinstance(start_date, str):
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(stop_date, str):
        stop_date = datetime.datetime.strptime(stop_date, '%Y-%m-%d')
    if start_date:
        query = query.filter(models.Run.run_at >= start_date)
    if stop_date:
        query = query.filter(models.Run.run_at <= stop_date)
    return query


def get_engine(use_slave=False):
    """Get a new sqlalchemy engine instance

    :param bool use_slave if possible, use 'slave' database for this engine

    :return: The engine object for the database connection
    :rtype: sqlalchemy.engine.Engine
    """
    facade = _create_facade_lazily()
    return facade.get_engine(use_slave=use_slave)


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
    If a field is omitted it will not be changed in the DB.

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
               id=None, session=None, run_at=None):
    """Create a new run record in the database

    :param int skips: total number of skipped tests defaults to 0
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
    if run_at:
        run.run_at = run_at
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


def update_test_run(values, test_run_id, session=None):
    """Update an individual test_run with new data.

    This method will take a dictionary of fields to update for a specific
    test_run. If a field is omitted it will not be changed in the DB.

    :param dict values: dict of values to update the test with. The key is the
                        column name and the value is the new value to be stored
                        in the DB
    :param str test_run_id: the uuid of the test_run to update. (value of the
                        id column for the row to be updated)
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The updated test_run object stored in the DB
    :rtype: subunit2sql.models.TestRun
    """
    session = session or get_session()
    with session.begin():
        test_run = get_test_run_by_id(test_run_id, session)
        test_run.update(values)
    return test_run


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

    session = session or get_session()
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


def get_run_metadata(run_id, session=None):
    """Return all run metadata objects associated with a given run.

    :param str run_id: The uuid of the run to get all the metadata
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of metadata objects
    :rtype: subunit2sql.models.RunMetadata
    """
    session = session or get_session()
    query = db_utils.model_query(models.RunMetadata, session).filter_by(
        run_id=run_id)
    return query.all()


def get_runs_by_key_value(key, value, session=None):
    """Return all run objects associated with a certain key/value metadata pair

    :param key: The key to be matched
    :param value: The value to be matched
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return list: The list of runs
    :rtype: subunit2sql.models.Run
    """
    session = session or get_session()
    query = db_utils.model_query(models.Run, session=session).join(
        models.RunMetadata).filter_by(key=key, value=value)

    return query.all()


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
    if start_time:
        start_time = start_time.replace(tzinfo=None)
        start_time_microsecond = start_time.microsecond
    else:
        start_time_microsecond = None
    if end_time:
        stop_time = end_time.replace(tzinfo=None)
        stop_time_microsecond = stop_time.microsecond
    else:
        stop_time = None
        stop_time_microsecond = None
    test_run.stop_time = stop_time
    test_run.stop_time_microsecond = stop_time_microsecond
    test_run.start_time = start_time
    test_run.start_time_microsecond = start_time_microsecond
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


def add_test_metadata(meta_dict, test_id, session=None):
    """Add a metadata key value pairs for a specific test.

    This method will take a dictionary and store key value pair metadata in the
    DB associated with the specified run.

    :param dict meta_dict: a dictionary which will generate a separate key
                           value pair row associated with the test_run_id
    :param str test_id: the uuid of the test to update. (value of the
                        id column for the row to be updated)
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of created metadata objects
    :rtype: subunit2sql.models.TestMeta
    """
    metadata = []
    for key, value in meta_dict.items():
        meta = models.TestMetadata()
        meta.key = key
        meta.value = value
        meta.test_id = test_id
        session = session or get_session()
        with session.begin():
            session.add(meta)
        metadata.append(meta)
    return metadata


def get_test_metadata(test_id, session=None):
    """Return all test metadata objects for associated with a given test.

    :param str test_id: The uuid of the test to get all the metadata
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of created metadata objects
    :rtype: subunit2sql.models.TestMetadata
    """
    session = session or get_session()
    query = db_utils.model_query(models.TestMetadata, session).filter_by(
        id=test_id)
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


def get_all_runs_by_date(start_date=None, stop_date=None, session=None):
    """Return all runs from the DB.

    :param str: optional start_date, if provided only runs started at or after
                the start_date will be included in the response
    :param str: optional end_date, if provided only runs started at or before
                the end_date will be included in the response
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of run objects
    :rtype: subunit2sql.models.Run
    """

    session = session or get_session()
    query = db_utils.model_query(models.Run, session=session)

    # Process date bounds
    query = _filter_runs_by_date(query, start_date, stop_date)

    return query.all()


def get_all_runs(session=None):
    """Return all runs from the DB.

    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of run objects
    :rtype: subunit2sql.models.Run
    """

    return get_all_runs_by_date(session=session)


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
    """Get the run duration for a specific test_run.

    :param str test_run_id: The test_run's uuid (the id column in the test_run
                            table) to get the duration of
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The duration of the test run in secs
    :rtype: float
    """
    session = session or get_session()
    test_run = get_test_run_by_id(test_run_id, session)
    start_time = test_run.start_time
    start_time = start_time.replace(
        microsecond=test_run.start_time_microsecond)
    stop_time = test_run.stop_time
    stop_time = stop_time.replace(microsecond=test_run.stop_time_microsecond)
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
        models.TestRun).filter(models.TestRun.run_id == run_id).outerjoin(
            models.TestRunMetadata).order_by(
                models.TestRun.start_time,
                models.TestRun.start_time_microsecond).values(
                    models.Test.test_id,
                    models.TestRun.status,
                    models.TestRun.start_time,
                    models.TestRun.start_time_microsecond,
                    models.TestRun.stop_time,
                    models.TestRun.stop_time_microsecond,
                    models.TestRunMetadata.key,
                    models.TestRunMetadata.value)
    test_runs = collections.OrderedDict()
    for test_run in query:
        if test_run[0] not in test_runs:
            # If there is no start_time set to None
            if test_run[2]:
                start_time = test_run[2]
                start_time = start_time.replace(microsecond=test_run[3])
            else:
                start_time = None
            # If there is no stop_time set to None
            if test_run[4]:
                stop_time = test_run[4]
                stop_time = stop_time.replace(microsecond=test_run[5])
            else:
                stop_time = None
            test_runs[test_run[0]] = {
                'status': test_run[1],
                'start_time': start_time,
                'stop_time': stop_time,
            }
            if test_run[6]:
                test_runs[test_run[0]]['metadata'] = {test_run[6]: test_run[7]}
        else:
            if test_run[6]:
                test_runs[test_run[0]]['metadata'][test_run[6]] = test_run[7]
    return test_runs


def get_test_run_time_series(test_id, session=None):
    """Returns a time series dict of run_times for successes of a single test

    :param str test_id: The test's uuid (the id column in the test table) which
                        will be used to get all the test run times for.
    :param session: optional session object if one isn't provided a new session

    :return dict: A dictionary with the start times as the keys and the values
                  being the duration of the test that started at that time in
                  sec.
    """
    session = session or get_session()
    query = db_utils.model_query(models.TestRun, session=session).filter_by(
        test_id=test_id).filter_by(status='success').values(
            models.TestRun.start_time, models.TestRun.start_time_microsecond,
            models.TestRun.stop_time, models.TestRun.stop_time_microsecond)
    time_series = {}
    for test_run in query:
        start_time = test_run[0]
        start_time = start_time.replace(microsecond=test_run[1])
        stop_time = test_run[2]
        stop_time = stop_time.replace(microsecond=test_run[3])
        time_series[test_run[0]] = (stop_time - start_time).total_seconds()
    return time_series


def get_test_run_series(start_date=None, stop_date=None, session=None):
    """Returns a time series dict of total daily run counts

    :param str start_date: Optional start date to filter results on
    :param str stop_date: Optional stop date to filter results on
    :param session: optional session object if one isn't provided a new session

    :return dict: A dictionary with the dates as the keys and the values
                  being the total run count for that day. (The sum of success
                  and failures from all runs that started that day)
    """
    session = session or get_session()
    full_query = db_utils.model_query(models.Run, session=session).join(
        models.RunMetadata).filter_by(key='build_queue', value='gate')

    # Process date bounds
    full_query = _filter_runs_by_date(full_query, start_date, stop_date)

    query = full_query.values(models.Run.run_at, models.Run.passes,
                              models.Run.fails)
    time_series = {}
    for test_run in query:
        start_time = test_run[0]
        # Sum of starts and failures is the count for the run
        local_run_count = test_run[1] + test_run[2]
        if start_time in time_series:
            time_series[start_time] = time_series[start_time] + local_run_count
        else:
            time_series[start_time] = local_run_count
    return time_series


def get_test_status_time_series(test_id, session=None):
    """Returns a time series dict of test_run statuses of a single test

    :param str test_id: The test's uuid (the id column in the test table) which
                        will be used to get all the test run times for.
    :param session: optional session object if one isn't provided a new session

    :return dict: A dictionary with the start times as the keys and the values
                  being the status of that test run.
    """
    session = session or get_session()
    query = db_utils.model_query(models.TestRun, session=session).filter_by(
        test_id=test_id).values(
            models.TestRun.start_time, models.TestRun.start_time_microsecond,
            models.TestRun.status)
    status_series = {}
    for test_run in query:
        start_time = test_run[0]
        start_time = start_time.replace(microsecond=test_run[1])
        status = test_run[2]
        status_series[start_time] = status
    return status_series


def get_recent_successful_runs(num_runs=10, session=None):
    """Return a list of run uuid strings for the most recent successful runs

    :param int num_runs: The number of runs to return in the list
    :param session: optional session object if one isn't provided a new session

    :return list: A list of run uuid strings (the id column in the runs table)
                  for the most recent runs.
    """
    session = session or get_session()
    results = db_utils.model_query(models.Run, session).order_by(
        models.Run.run_at.desc()).filter_by(fails=0).limit(num_runs).all()
    return map(lambda x: x.id, results)


def get_recent_failed_runs(num_runs=10, session=None):
    """Return a list of run uuid strings for the most recent failed runs

    :param int num_runs: The number of runs to return in the list
    :param session: optional session object if one isn't provided a new session

    :return list: A list of run uuid strings (the id column in the runs table)
                  for the most recent runs.
    """
    session = session or get_session()
    results = db_utils.model_query(models.Run, session).order_by(
        models.Run.run_at.desc()).filter(
        models.Run.fails > 0).limit(num_runs).all()
    return map(lambda x: x.id, results)


def delete_old_runs(expire_age=186, session=None):
    """Delete all runs and associated metadata older than the provided age

    :param int expire_age: The number of days into the past to use as the
                           expiration date for deleting the runs
    :param session: optional session object if one isn't provided a new session
    """
    session = session or get_session()
    expire_date = datetime.date.today() - datetime.timedelta(days=expire_age)
    db_utils.model_query(models.Run, session).filter(
        models.Run.run_at < expire_date).join(
            models.RunMetadata).delete(synchronize_session='evaluate')
    db_utils.model_query(models.Run, session).filter(
        models.Run.run_at < expire_date).delete(synchronize_session='evaluate')


def delete_old_test_runs(expire_age=186, session=None):
    """Delete all test runs and associated metadata older than the provided age

    :param int expire_age: The number of days into the past to use as the
                           expiration date for deleting the test runs
    :param session: optional session object if one isn't provided a new session
    """
    session = session or get_session()
    expire_date = datetime.date.today() - datetime.timedelta(days=expire_age)
    db_utils.model_query(models.TestRun, session).filter(
        models.TestRun.start_time < expire_date).join(
            models.TestRunMetadata).delete(synchronize_session='evaluate')
    db_utils.model_query(models.TestRun, session).filter(
        models.TestRun.start_time < expire_date).delete(
            synchronize_session='evaluate')


def get_id_from_test_id(test_id, session=None):
    """Return the id (uuid primary key) for a test given it's test_id value

    :param str test_id:
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return: The id for the specified test
    :rtype: str
    """
    session = session or get_session()
    return db_utils.model_query(models.Test, session).filter_by(
        test_id=test_id).value('id')


def get_ids_for_all_tests(session=None):
    """Return a list of ids (uuid primary key) for all tests in the database

    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return: The list of all ids for tests in the tests table
    :rtype: list
    """
    session = session or get_session()
    return db_utils.model_query(models.Test, session).value(models.Test.id)


def get_test_counts_in_date_range(test_id, start_date=None, stop_date=None,
                                  session=None):
    """Return the number of successes, failures, and skips for a single test.

    Optionally you can provide a date to filter the results to be within a
    certain date range

    :param str start_date: The date to use as the start for counting
    :param str stop_date: The date to use as the cutoff for counting
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return: a dict containing the number of successes, failures, and skips
    :rtype: dict
    """
    start_date = datetime.datetime.strptime(start_date, '%b %d %Y')
    if isinstance(stop_date, str):
        stop_date = datetime.datetime.strptime(stop_date, '%b %d %Y')
    session = session or get_session()
    count_dict = {}
    success_query = db_utils.model_query(models.TestRun, session).filter_by(
        test_id=test_id).filter(models.TestRun.status == 'success')
    fail_query = db_utils.model_query(models.TestRun, session).filter_by(
        test_id=test_id).filter(models.TestRun.status == 'fail')
    skip_query = db_utils.model_query(models.TestRun, session).filter_by(
        test_id=test_id).filter(models.TestRun.status == 'skip')

    if start_date:
        success_query = success_query.filter(
            models.TestRun.start_time > start_date)
        fail_query = fail_query.filter(
            models.TestRun.start_time > start_date)
        skip_query = skip_query.filter(
            models.TestRun.start_time > start_date)

    if stop_date:
        success_query = success_query.filter(
            models.TestRun.stop_time < stop_date)
        fail_query = fail_query.filter(
            models.TestRun.stop_time < stop_date)
        skip_query = skip_query.filter(
            models.TestRun.stop_time < stop_date)

    count_dict['success'] = success_query.count()
    count_dict['failure'] = fail_query.count()
    count_dict['skips'] = skip_query.count()
    return count_dict


def get_failing_test_ids_from_runs_by_key_value(key, value, session=None):
    """Get a list of failing test_ids from runs with run_metadata.

    This method gets a distinct list of test_ids (the test_id column not the id
    column) from all runs that match a run metadata key value pair.

    :param str key: The key to use to match runs from in run_metadata
    :param str value: The value of the key in run_metadata to match runs
                      against
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: A list of test_ids that failed from runs that match the provided
             key value run_metadata pair
    :rtype: list
    """

    session = session or get_session()
    test_ids = db_utils.model_query(models.TestRun, session).join(
        models.Test, models.TestRun.test_id == models.Test.id).join(
            models.RunMetadata,
            models.TestRun.run_id == models.RunMetadata.run_id).filter(
                models.RunMetadata.key == key,
                models.RunMetadata.value == value,
                models.TestRun.status == 'fail').values(
                    sqlalchemy.distinct(models.Test.test_id))
    return [test_id[0] for test_id in test_ids]


def get_test_run_dict_by_run_meta_key_value(key, value, start_date=None,
                                            stop_date=None, session=None):
    """Get a list of test run dicts from runs with a run metadata key value pair

    :param str key: The key to use to match runs from in run_metadata
    :param str value: The value of the key in run_metadata to match runs
                      against
    :param start_date: Optional start date to filter results on
    :param stop_date: Optional stop date to filter results on
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return test_runs: The dictionary of all the tests run on any run that had
                       metadata matching the provided key value pair.
    :rtype: dict
    """
    session = session or get_session()
    query = db_utils.model_query(models.RunMetadata, session).filter(
        models.RunMetadata.key == key,
        models.RunMetadata.value == value).join(
            models.TestRun,
            models.RunMetadata.run_id == models.TestRun.run_id).join(
                models.Test)
    query = _filter_runs_by_date(query, start_date=start_date,
                                 stop_date=stop_date)
    query = query.values(models.Test.test_id,
                         models.TestRun.status,
                         models.TestRun.start_time,
                         models.TestRun.start_time_microsecond,
                         models.TestRun.stop_time,
                         models.TestRun.stop_time_microsecond)
    tests = []
    for test in query:
        if test[2]:
            start_time = test[2]
            start_time = start_time.replace(microsecond=test[3])
        else:
            start_time = None
        if test[4]:
            stop_time = test[4]
            stop_time = stop_time.replace(microsecond=test[5])
        else:
            stop_time = None
        test_run_dict = {
            'test_id': test[0],
            'status': test[1],
            'start_time': start_time,
            'stop_time': stop_time,
        }
        tests.append(test_run_dict)
    return tests


def get_all_runs_time_series_by_key(key, start_date=None,
                                    stop_date=None, session=None):
    """Get a time series of run summaries grouped by a key

    This method will get a time series dictionary of run summary views which
    are grouped by the values of the specified key

    :param str key: the key to use for grouping the run summaries
    :param str start_date: Optional start date to filter results on
    :param str stop_date: Optional stop date to filter results on
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return runs: a time series dictionary of runs grouped by values of the
                  specified key
    :rtype: dict
    """
    session = session or get_session()
    runs_query = db_utils.model_query(models.Run, session).join(
        models.RunMetadata).filter(models.RunMetadata.key == key)
    runs_query = _filter_runs_by_date(runs_query, start_date, stop_date)
    runs_query = runs_query.values(models.Run.run_at,
                                   models.Run.passes,
                                   models.Run.fails,
                                   models.Run.skips,
                                   models.RunMetadata.value)
    runs = {}
    for run in runs_query:
        if run[0] not in runs:
            runs[run[0]] = {run[4]: [{
                'pass': run[1],
                'fail': run[2],
                'skip': run[3],
            }]}
        else:
            if run[4] not in runs[run[0]].keys():
                runs[run[0]][run[4]] = [{
                    'pass': run[1],
                    'fail': run[2],
                    'skip': run[3],
                }]
            else:
                runs[run[0]][run[4]].append({
                    'pass': run[1],
                    'fail': run[2],
                    'skip': run[3],
                })
    return runs


def get_time_series_runs_by_key_value(key, value, start_date=None,
                                      stop_date=None, session=None):
    """Get a time series of runs with meta for all runs with a key value pai

    :param str key: the metadata key to use for matching the runs
    :param str value: the metadata value to use for matching the runs
    :param start_date: Optional start date to filter results on
    :param str stop_date: Optional stop date to filter results on
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation


    :return runs: a time series dictionary (where the top level key is a
                  timestamp) that contains all the runs which
    :rtype: dict
    """
    session = session or get_session()
    sub_query = session.query(models.RunMetadata.run_id).filter(
        models.RunMetadata.key == key,
        models.RunMetadata.value == value).subquery()
    run_query = db_utils.model_query(models.Run, session).join(
        models.RunMetadata).filter(models.Run.id.in_(sub_query))
    run_query = _filter_runs_by_date(run_query, start_date, stop_date)
    run_query = run_query.values(models.Run.id,
                                 models.Run.passes,
                                 models.Run.fails,
                                 models.Run.skips,
                                 models.Run.run_time,
                                 models.Run.run_at,
                                 models.RunMetadata.key,
                                 models.RunMetadata.value)
    runs = {}
    for run in run_query:
        run_at = run[5]
        run_id = run[0]
        if run_at not in runs:
            # We have hit a new time stamp so we need to add a top level key
            # for the timestamp and populate the run list with a new dict for
            # the run
            runs[run_at] = []
            run_dict = {
                'id': run_id,
                'pass': run[1],
                'fail': run[2],
                'skip': run[3],
                'run_time': run[4],
                'metadata': {run[6]: run[7]}
            }
            runs[run_at].append(run_dict)
        else:
            if run_id not in [loc_run["id"] for loc_run in runs[run_at]]:
                # We have hit a new run for an existing timestamp, we need to
                # append a new run dict to the list of runs for that timestamp
                run_dict = {
                    'id': run_id,
                    'pass': run[1],
                    'fail': run[2],
                    'skip': run[3],
                    'run_time': run[4],
                    'metadata': {run[6]: run[7]}
                }
                runs[run_at].append(run_dict)
            else:
                # The run dictionary has already been added for this timestamp
                # this means we've hit a new metadata entry, so we need to
                # update the metadata dictionary with the additional info
                update_index = None
                for index, run_dict in list(enumerate(runs[run_at])):
                    if run_dict['id'] == run_id:
                        update_index = index
                runs[run_at][update_index]['metadata'][run[6]] = run[7]
    return runs


def add_test_run_attachments(attach_dict, test_run_id, session=None):
    """Add attachments a specific test run.

    This method will take a dictionary and store key blob pair attachments in
    the DB associated with the specified test_run.

    :param dict attachments_dict: a dictionary which will generate a separate
                                  key blob pair row associated with the
                                  test_run_id
    :param str test_run_id: the uuid of the test_run to update. (value of the
                            id column for the row to be updated)
    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of created attachment objects
    :rtype: subunit2sql.models.Attachments
    """

    session = session or get_session()
    attachments = []
    for label, attach in attach_dict.items():
        attachment = models.Attachments()
        attachment.label = label
        attachment.attachment = attach
        attachment.test_run_id = test_run_id
        with session.begin():
            session.add(attachment)
        attachments.append(attachment)
    return attachments


def get_runs_by_status_grouped_by_run_metadata(key, start_date=None,
                                               stop_date=None, session=None):
    session = session or get_session()
    val = models.RunMetadata.value
    run_pass_query = session.query(
        sqlalchemy.func.count(models.Run.id), val).filter(
            models.Run.fails == 0, models.Run.passes > 0).join(
                models.RunMetadata).group_by(val).filter(
                    models.RunMetadata.key == key)
    run_fail_query = session.query(
        sqlalchemy.func.count(models.Run.id), val).filter(
            models.Run.fails > 0, models.Run.passes > 0).join(
                models.RunMetadata).group_by(val).filter(
                    models.RunMetadata.key == key)

    run_pass_query = _filter_runs_by_date(run_pass_query, start_date,
                                          stop_date)
    run_fail_query = _filter_runs_by_date(run_fail_query, start_date,
                                          stop_date)
    rows = run_pass_query.all()
    result = {}
    for row in rows:
        result[row[1]] = {'pass': row[0]}
    rows = run_fail_query.all()
    for row in rows:
        if row[1] in result:
            result[row[1]]['fail'] = row[0]
        else:
            result[row[1]] = {'fail': row[0]}
    return result


def get_all_run_metadata_keys(session=None):
    """Get a list of all the keys used in the run_metadata table

    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return keys: a list of all keys used in the run_metadata table
    :rtype: list
    """
    session = session or get_session()
    keys = session.query(models.RunMetadata.key).distinct().all()
    return [key[0] for key in keys]


def get_all_test_metadata_keys(session=None):
    """Get a list of all the keys used in the test_metadata table

    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return keys: a list of all keys used in the test_metadata table
    :rtype: list
    """
    session = session or get_session()
    keys = session.query(models.TestMetadata.key).distinct().all()
    return [key[0] for key in keys]


def get_all_test_run_metadata_keys(session=None):
    """Get a list of all the keys used in the test_run_metadata table

    :param session: optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return keys: a list of all keys used in the test_run_metadata table
    :rtype: list
    """
    session = session or get_session()
    keys = session.query(models.TestRunMetadata.key).distinct().all()
    return [key[0] for key in keys]
