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
import six
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
            **dict(six.iteritems(CONF.database)))
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


def _filter_test_runs_by_date(query, start_date=None, stop_date=None):
    # Helper to apply a data range filter to a query on Run table
    if isinstance(start_date, str):
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(stop_date, str):
        stop_date = datetime.datetime.strptime(stop_date, '%Y-%m-%d')
    if start_date:
        query = query.filter(models.TestRun.start_time >= start_date)
    if stop_date:
        query = query.filter(models.TestRun.start_time <= stop_date)
    return query


def get_engine(use_slave=False):
    """Get a new sqlalchemy engine instance

    :param bool use_slave: If possible, use 'slave' database for this engine

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
    :param int run_count: Total number or runs defaults to 0
    :param int success: Number of successful runs defaults 0
    :param int failure: Number of failed runs defaults to 0
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return: The test object stored in the DB
    :rtype: subunit2sql.models.Test

    :raises InvalidRunCount: If the run_count doesn't equal the sum of the
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

    :param dict values: Dict of values to update the test with. The key is the
                        column name and the value is the new value to be stored
                        in the DB
    :param str test_id: The uuid of the test to update. (value of the id column
                        for the row to be updated)
    :param session: Optional session object if one isn't provided a new session
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

    :param int skips: Total number of skipped tests defaults to 0
    :param int fails: Total number of failed tests defaults to 0
    :param int passes: Total number of passed tests defaults to 0
    :param float run_time: Total run timed defaults to 0
    :param str artifacts: A link to any artifacts from the test run defaults to
                          None
    :param str id: The run id for the new run, needs to be a unique value
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :param run_at: Optional time at which the run was started. If not specified
                   the time that data is added to the DB will be used instead

    :return: The run object stored in the DB
    :rtype: subunit2sql.models.Run
    """
    run = models.Run()
    if id:
        run.uuid = id
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

    :param dict values: Dict of values to update the test with. The key is the
                        column name and the value is the new value to be stored
                        in the DB
    :param str run_id: The uuid of the run to update. (value of the id column
                        for the row to be updated)
    :param session: Optional session object if one isn't provided a new session
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

    :param dict values: Dict of values to update the test with. The key is the
                        column name and the value is the new value to be stored
                        in the DB
    :param str test_run_id: The uuid of the test_run to update. (value of the
                        id column for the row to be updated)
    :param session: Optional session object if one isn't provided a new session
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

    :param dict meta_dict: A dictionary which will generate a separate key
                           value pair row associated with the run_id
    :param str run_id: The uuid of the run to update. (value of the id column
                       for the row to be updated)
    :param session: Optional session object if one isn't provided a new session
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
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of metadata objects
    :rtype: subunit2sql.models.RunMetadata
    """
    session = session or get_session()
    query = db_utils.model_query(models.RunMetadata, session).join(
        models.Run,
        models.RunMetadata.run_id == models.Run.id).filter(
            models.Run.uuid == run_id)
    return query.all()


def get_runs_by_key_value(key, value, session=None):
    """Return all run objects associated with a certain key/value metadata pair

    :param key: The key to be matched
    :param value: The value to be matched
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return list: The list of runs
    :rtype: subunit2sql.models.Run
    """
    session = session or get_session()
    query = db_utils.model_query(models.Run, session=session).join(
        models.RunMetadata,
        models.Run.id == models.RunMetadata.run_id).filter_by(
            key=key, value=value)

    return query.all()


def create_test_run(test_id, run_id, status, start_time=None,
                    end_time=None, session=None):
    """Create a new test run record in the database

    This method creates a new record in the database

    :param str test_id: UUID for test that was run
    :param str run_id: UUID for run that this was a member of
    :param str status: Status of the test run, normally success, fail, or skip
    :param datetime.Datetime start_time: When the test was started defaults to
                                         None
    :param datetime.Datetime end_time: When the test was finished defaults to
                                       None
    :param session: Optional session object if one isn't provided a new session
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

    :param dict meta_dict: A dictionary which will generate a separate key
                           value pair row associated with the test_run_id
    :param str test_run_id: The uuid of the test_run to update. (value of the
                            id column for the row to be updated)
    :param session: Optional session object if one isn't provided a new session
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
    :param session: Optional session object if one isn't provided a new session
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

    :param dict meta_dict: A dictionary which will generate a separate key
                           value pair row associated with the test_run_id
    :param str test_id: The uuid of the test to update. (value of the
                        id column for the row to be updated)
    :param session: Optional session object if one isn't provided a new session
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
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of created metadata objects
    :rtype: subunit2sql.models.TestMetadata
    """
    session = session or get_session()
    query = db_utils.model_query(models.TestMetadata, session).filter_by(
        test_id=test_id)
    return query.all()


def get_all_tests(session=None):
    """Return all tests from the DB.

    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of test objects
    :rtype: subunit2sql.models.Test
    """
    session = session or get_session()
    query = db_utils.model_query(models.Test, session)
    return query.all()


def _get_test_prefixes_mysql(session):
    query = session.query(
        sqlalchemy.func.substring_index(models.Test.test_id, '.', 1))

    prefixes = set()
    for prefix in query.distinct().all():
        prefix = prefix[0]

        # strip out any wrapped function names, e.g. 'setUpClass (
        if '(' in prefix:
            prefix = prefix.split('(', 1)[1]

        prefixes.add(prefix)

    return list(prefixes)


def _get_test_prefixes_other(session):
    query = session.query(models.Test.test_id)

    unique = set()
    for test_id in query:
        # get the first '.'-separated token (possibly including 'setUpClass (')
        prefix = test_id[0].split('.', 1)[0]
        if '(' in prefix:
            # strip out the function name and paren, e.g. 'setUpClass(a' -> 'a'
            prefix = prefix.split('(', 1)[1]

        unique.add(prefix)

    return list(unique)


def get_test_prefixes(session=None):
    """Returns all test prefixes from the DB.

    This returns a list of unique test_id prefixes from the database, defined
    as the first dot-separated token in the test id. Prefixes wrapped in
    function syntax, such as 'setUpClass (a', will have this extra syntax
    stripped out of the returned value, up to and including the '(' character.

    As an example, given an input test with an ID 'prefix.test.Clazz.a_method',
    the derived prefix would be 'prefix'. Given a second test with an ID
    'setUpClass (prefix.test.Clazz)', the derived prefix would also be
    'prefix'. If this function were called on a database containing only these
    tests, a list with only one entry, 'prefix', would be returned.

    Note that this implementation assumes that tests ids are semantically
    separated by a period. If this is not the case (and no period characters
    occur at any position within test ids), the full test id will be considered
    the prefix, and the result of this function will be all unique test ids in
    the database.

    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return list: A list of all unique prefix strings, with any extraneous
                  details removed, e.g. 'setUpClass ('.
    :rtype: str
    """
    session = session or get_session()

    backend = session.bind.dialect.name
    if backend == 'mysql':
        return _get_test_prefixes_mysql(session)
    else:
        return _get_test_prefixes_other(session)


def _get_tests_by_prefix_mysql(prefix, session, limit, offset):
    # use mysql's substring_index to pull the prefix out of the full test_id
    func_filter = sqlalchemy.func.substring_index(models.Test.test_id, '.', 1)

    # query for tests against the prefix token, but use an ends-with compare
    # this way, if a test_id has a function call, e.g. 'setUpClass (a.b..c)' we
    # can still match it here
    # (we use an ugly 'like' query here, but this won't be operating on an
    # index regardless)
    query = db_utils.model_query(models.Test, session).filter(
        func_filter.like('%' + prefix)).order_by(models.Test.test_id.asc())

    return query.limit(limit).offset(offset).all()


def _get_tests_by_prefix_other(prefix, session, limit, offset):
    query = db_utils.model_query(models.Test, session).order_by(
        models.Test.test_id.asc())

    # counter to track progress toward offset
    skipped = 0

    ret = []
    for test in query:
        test_prefix = test.test_id.split('.', 1)[0]
        # compare via endswith to match wrapped test_ids: given
        # 'setUpClass (a.b.c)',  the first token will be 'setUpClass (a',
        # which endswith() will catch
        if test_prefix.endswith(prefix):
            # manually track offset progress since we aren't checking for
            # matches on the database-side
            if offset > 0 and skipped < offset:
                skipped += 1
                continue

            ret.append(test)

            if len(ret) >= limit:
                break

    return ret


def get_tests_by_prefix(prefix, session=None, limit=100, offset=0):
    """Returns all tests with the given prefix in the DB.

    A test prefix is the first segment of a test_id when split using a period
    ('.'). This function will return a list of tests whose first
    period-separated token ends with the specified prefix. As a side-effect,
    given an input 'a', this will return tests with prefixes 'a', but also
    prefixes wrapped in function syntax, such as 'setUpClass (a'.

    Note that this implementation assumes that tests ids are semantically
    separated by a period. If no period character exists in a test id, its
    prefix will be considered the full test id, and this method may return
    unexpected results.

    :param str prefix: The test prefix to search for
    :param session: Optional session object: if one isn't provided, a new
                    session will be acquired for the duration of this operation
    :param int limit: The maximum number of results to return
    :param int offset: The starting index, for pagination purposes
    :return list: The list of matching test objects, ordered by their test id
    :rtype: subunit2sql.models.Test
    """
    session = session or get_session()

    backend = session.bind.dialect.name
    if backend == 'mysql':
        return _get_tests_by_prefix_mysql(prefix, session, limit, offset)
    else:
        return _get_tests_by_prefix_other(prefix, session, limit, offset)


def get_all_runs_by_date(start_date=None, stop_date=None, session=None):
    """Return all runs from the DB.

    :param str: Optional start_date, if provided only runs started at or after
                the start_date will be included in the response
    :param str: Optional end_date, if provided only runs started at or before
                the end_date will be included in the response
    :param session: Optional session object if one isn't provided a new session
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

    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of run objects
    :rtype: subunit2sql.models.Run
    """

    return get_all_runs_by_date(session=session)


def get_all_test_runs(session=None):
    """Return all test runs from the DB.

    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of test run objects
    :rtype: subunit2sql.models.TestRun
    """
    session = session or get_session()
    query = db_utils.model_query(models.TestRun, session)
    return query.all()


def get_latest_run(session=None):
    """Return the most recently created run from the DB.

    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The latest run object
    :rtype: subunit2sql.models.Run
    """
    session = session or get_session()
    query = db_utils.model_query(models.Run, session).order_by(
        models.Run.run_at.desc())
    return query.first()


def get_failing_from_run(run_id, session=None):
    """Return the set of failing test runs for a give run.

    This method will return all the test run objects that failed during the
    specified run.

    :param str run_id: UUID for the run to find all the failing runs
    :param session: Optional session object if one isn't provided a new session
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
    :param session: Optional session object if one isn't provided a new session
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
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The specified test object
    :rtype: subunit2sql.models.Test
    """
    session = session or get_session()
    test = db_utils.model_query(models.Test, session).filter_by(
        test_id=test_id).first()
    return test


def get_run_id_from_uuid(uuid, session=None):
    """Get the id for a run by it's uuid

    :param str uuid: The uuid for the run
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return: The id for the run with the provided uuid
    :rtype: int
    """
    session = session or get_session()
    run_id = session.query(models.Run.id).filter(
        models.Run.uuid == uuid).first()[0]
    return run_id


def get_run_by_id(id, session=None):
    """Get an individual run by it's id.

    :param str id: The id for the run
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return: The specified run object
    :rtype: subunit2sql.models.Run
    """
    session = session or get_session()
    run = db_utils.model_query(models.Run, session).filter_by(id=id).first()
    return run


def get_test_run_by_id(test_run_id, session=None):
    """Get an individual test run by it's id.

    :param str test_run_id: The id for the test run
    :param session: Optional session object if one isn't provided a new session
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
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of test run objects for the specified test
    :rtype: subunit2sql.models.TestRun
    """
    session = session or get_session()
    test_runs = db_utils.model_query(models.TestRun,
                                     session=session).filter_by(
        test_id=test_id).all()
    return test_runs


def get_test_runs_by_test_test_id(test_id, start_date=None, stop_date=None,
                                  session=None, key=None, value=None):
    """Get all test runs for a specific test by the test'stest_id column

    :param str test_id: The test's test_id (the test_id column in the test
                        table) which to get all test runs for
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :param datetime.datetime start_date: The date to use as the start date for
                                         results
    :param datetime.datetime stop_date: The date to use as the cutoff date for
                                        results
    :param str key: An optional key for run metadata to filter the test runs
                    on. Must be specified with a value otherwise it does
                    nothing.
    :param str value: An optional value for run metadata to filter the test
                      runs on. Must be specified with a key otherwise it does
                      nothing.

    :return list: The list of test run objects for the specified test
    :rtype: subunit2sql.models.TestRun
    """
    session = session or get_session()

    test_runs_query = db_utils.model_query(models.TestRun,
                                           session=session).join(
        models.Test, models.TestRun.test_id == models.Test.id).filter(
            models.Test.test_id == test_id)
    if start_date:
        test_runs_query = test_runs_query.filter(
            models.TestRun.start_time >= start_date)
    if stop_date:
        test_runs_query = test_runs_query.filter(
            models.TestRun.start_time <= stop_date)
    if key and value:
        test_runs_query = test_runs_query.join(
            models.RunMetadata,
            models.TestRun.run_id == models.RunMetadata.run_id).filter(
                models.RunMetadata.key == key,
                models.RunMetadata.value == value)
    test_runs = test_runs_query.all()
    return test_runs


def get_test_runs_by_run_id(run_id, session=None):
    """Get all test runs for a specific run.

    :param str run_id: The run's uuid (the uuid column in the run table) which
                       to get all test runs for
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of test run objects for the specified test
    :rtype: subunit2sql.models.TestRun
    """
    session = session or get_session()
    test_runs = db_utils.model_query(
        models.TestRun, session=session).join(
            models.Run, models.TestRun.run_id == models.Run.id).filter(
                models.Run.uuid == run_id).all()
    return test_runs


def get_test_run_duration(test_run_id, session=None):
    """Get the run duration for a specific test_run.

    :param str test_run_id: The test_run's uuid (the id column in the test_run
                            table) to get the duration of
    :param session: Optional session object if one isn't provided a new session
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
    :param session: Optional session object if one isn't provided a new session

    :return list: The list of test objects for the specified test
    :rtype: subunit2sql.models.Test
    """
    session = session or get_session()
    query = db_utils.model_query(models.Test, session=session).join(
        models.TestRun, models.Test.id == models.TestRun.test_id).filter_by(
            run_id=run_id)
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
    :param session: Optional session object if one isn't provided a new session

    :return dict: A dictionary with the test_id from the tests for keys that
                  contains all the stored information about the test_runs.
    """
    session = session or get_session()
    query = db_utils.model_query(models.Test, session=session).join(
        models.TestRun, models.Test.id == models.TestRun.test_id).join(
            models.Run, models.TestRun.run_id == models.Run.id).filter(
                models.Run.uuid == run_id).outerjoin(
                    models.TestRunMetadata,
                    models.TestRun.id == models.TestRunMetadata.
                    test_run_id).order_by(
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
    :param session: Optional session object if one isn't provided a new session

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


def get_test_run_series(start_date=None, stop_date=None, session=None,
                        key='build_queue', value='gate'):
    """Returns a time series dict of total daily run counts

    :param str start_date: Optional start date to filter results on
    :param str stop_date: Optional stop date to filter results on
    :param session: Optional session object if one isn't provided a new session
    :param str key: Optional run_metadata key to filter the runs used on. Key
                    must be specified with value for filtering to occur.
                    This defaults to 'build_queue' for backwards compatibility
                    with earlier versions. Note, this default will be removed
                    in the future.
    :param str value: Optional run_metadata value to filter the runs used on.
                      Value must be specified with key for filtering to occur.
                      This defaults to 'gate' for backwards
                      compatibility with earlier versions. Note, this default
                      will be removed in the future.
    :return dict: A dictionary with the dates as the keys and the values
                  being the total run count for that day. (The sum of success
                  and failures from all runs that started that day)
    """
    session = session or get_session()
    full_query = db_utils.model_query(models.Run, session=session)
    if key and value:
        full_query = full_query.join(
            models.RunMetadata,
            models.Run.id == models.RunMetadata.run_id).filter_by(
                key=key, value=value)

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
    :param session: Optional session object if one isn't provided a new session

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


def get_recent_successful_runs(num_runs=10, session=None, start_date=None):
    """Return a list of run uuid strings for the most recent successful runs

    :param int num_runs: The number of runs to return in the list
    :param session: Optional session object if one isn't provided a new session
    :param datetime start_date: An optional date to use as the starting point
                                for getting recent runs. Only runs after this
                                date will be returned.

    :return list: A list of run uuid strings (the id column in the runs table)
                  for the most recent runs.
    """
    session = session or get_session()
    results = db_utils.model_query(models.Run, session)
    results = _filter_runs_by_date(results, start_date)
    results = results.order_by(
        models.Run.run_at.desc()).filter_by(fails=0).limit(num_runs).all()
    return list(map(lambda x: x.uuid, results))


def get_recent_failed_runs(num_runs=10, session=None, start_date=None):
    """Return a list of run uuid strings for the most recent failed runs

    :param int num_runs: The number of runs to return in the list
    :param session: Optional session object if one isn't provided a new session
    :param datetime start_date: An optional date to use as the starting point
                                for getting recent runs. Only runs after this
                                date will be returned.

    :return list: A list of run uuid strings (the id column in the runs table)
                  for the most recent runs.
    """
    session = session or get_session()
    results = db_utils.model_query(models.Run, session)
    results = _filter_runs_by_date(results, start_date)
    results = results.order_by(
        models.Run.run_at.desc()).filter(
        models.Run.fails > 0).limit(num_runs).all()
    return list(map(lambda x: x.uuid, results))


def get_recent_runs_by_key_value_metadata(key, value, num_runs=10,
                                          session=None, start_date=None):
    """Get a list of runs for recent runs with a key value metadata pair

    :param int num_runs: The number of runs to return in the list
    :param session: Optional session object if one isn't provided a new session
    :param datetime start_date: An optional date to use as the starting point
                                for getting recent runs. Only runs after this
                                date will be returned.

    :return list: A list of run objects for the most recent runs.
    :rtype subunit2sql.db.models.Run
    """
    session = session or get_session()
    results = db_utils.model_query(models.Run, session).join(
        models.RunMetadata,
        models.Run.id == models.RunMetadata.run_id)
    results = _filter_runs_by_date(results, start_date)
    results = results.filter(
        models.RunMetadata.key == key,
        models.RunMetadata.value == value).order_by(
            models.Run.run_at.desc()).limit(num_runs).all()
    return results


def delete_old_runs(expire_age=186, session=None):
    """Delete all runs and associated metadata older than the provided age

    :param int expire_age: The number of days into the past to use as the
                           expiration date for deleting the runs
    :param session: Optional session object if one isn't provided a new session
    """
    session = session or get_session()
    expire_date = datetime.date.today() - datetime.timedelta(days=expire_age)

    # Delete the run_metadata
    sub_query = session.query(models.Run.id).filter(
        models.Run.run_at < expire_date).subquery()
    db_utils.model_query(models.RunMetadata, session).filter(
        models.RunMetadata.run_id.in_(sub_query)).delete(
            synchronize_session=False)
    # Delete the runs
    db_utils.model_query(models.Run, session).filter(
        models.Run.run_at < expire_date).delete(synchronize_session=False)


def delete_old_test_runs(expire_age=186, session=None):
    """Delete all test runs and associated metadata older than the provided age

    :param int expire_age: The number of days into the past to use as the
                           expiration date for deleting the test runs
    :param session: Optional session object if one isn't provided a new session
    """
    session = session or get_session()
    expire_date = datetime.date.today() - datetime.timedelta(days=expire_age)

    # Delete the test run metadata
    sub_query = session.query(models.TestRun.id).filter(
        models.TestRun.start_time < expire_date).subquery()
    db_utils.model_query(models.TestRunMetadata, session).filter(
        models.TestRunMetadata.test_run_id.in_(sub_query)).delete(
            synchronize_session=False)
    # Delete the test runs
    db_utils.model_query(models.TestRun, session).filter(
        models.TestRun.start_time < expire_date).delete(
            synchronize_session=False)


def get_id_from_test_id(test_id, session=None):
    """Return the id (uuid primary key) for a test given it's test_id value

    :param str test_id: The test_id's string (not UUID) to identify the test
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return: The id for the specified test
    :rtype: str
    """
    session = session or get_session()
    return db_utils.model_query(models.Test, session).filter_by(
        test_id=test_id).value('id')


def get_ids_for_all_tests(session=None):
    """Return an iterator of ids (uuid primary key) for all tests in the database

    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return: The iterator of all ids for tests in the tests table
    :rtype: iterator
    """
    session = session or get_session()
    return db_utils.model_query(models.Test, session).values(models.Test.id)


def get_run_times_grouped_by_run_metadata_key(key, start_date=None,
                                              stop_date=None, session=None):
    """Return the aggregate run times for all runs grouped by a metadata key

    :param key: The run_metadata key to use for grouping runs
    :param session: Optional session object if one isn't provided a new session
                        will be acquired for the duration of this operation

    :return: A dictionary where keys are the value of the provided metadata key
             and the values are a list of run_times for successful runs with
             that metadata value
    :rtype: dict
    """
    session = session or get_session()
    run_times_query = db_utils.model_query(models.Run, session).filter(
        models.Run.fails == 0, models.Run.passes > 0).join(
            models.RunMetadata,
            models.Run.id == models.RunMetadata.run_id).filter(
                models.RunMetadata.key == key)

    run_times_query = _filter_runs_by_date(run_times_query, start_date,
                                           stop_date)
    run_times = run_times_query.values(models.Run.run_at, models.Run.run_time,
                                       models.RunMetadata.value)
    result = {}
    for run in run_times:
        if result.get(run.value):
            result[run.value].append(run.run_time)
        else:
            result[run.value] = [run.run_time]
    return result


def get_test_counts_in_date_range(test_id, start_date=None, stop_date=None,
                                  session=None):
    """Return the number of successes, failures, and skips for a single test.

    Optionally you can provide a date to filter the results to be within a
    certain date range

    :param str test_id: The test_id's ID(big integer) to identify the test
    :param datetime start_date: The date to use as the start for counting. A
                                str in the datetime str format "%b %d %Y" was
                                the previous format here and will still work
                                but is deprecated in favor of passing in a
                                datetime object.
    :param datetime stop_date: The date to use as the cutoff for counting. A
                               str in the datetime str format "%b %d %Y" was
                               the previous format here and will still work but
                               is deprecated in favor of passing in a datetime.
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return: A dict containing the number of successes, failures, and skips
    :rtype: dict
    """
    if isinstance(start_date, str):
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
    :param session: Optional session object if one isn't provided a new session
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
                models.Test, models.TestRun.test_id == models.Test.id)
    query = _filter_test_runs_by_date(query, start_date=start_date,
                                      stop_date=stop_date)
    query = query.values(models.Test.test_id,
                         models.TestRun.status,
                         models.TestRun.start_time,
                         models.TestRun.start_time_microsecond,
                         models.TestRun.stop_time,
                         models.TestRun.stop_time_microsecond)
    tests = []
    for test in query:
        if test.start_time:
            start_time = test.start_time
            start_time = start_time.replace(
                microsecond=test.start_time_microsecond)
        else:
            start_time = None
        if test.stop_time:
            stop_time = test.stop_time
            stop_time = stop_time.replace(
                microsecond=test.stop_time_microsecond)
        else:
            stop_time = None
        test_run_dict = {
            'test_id': test.test_id,
            'status': test.status,
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

    :param str key: The key to use for grouping the run summaries
    :param str start_date: Optional start date to filter results on
    :param str stop_date: Optional stop date to filter results on
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :return runs: A time series dictionary of runs grouped by values of the
                  specified key
    :rtype: dict
    """
    session = session or get_session()
    runs_query = db_utils.model_query(models.Run, session).join(
        models.RunMetadata,
        models.Run.id == models.RunMetadata.run_id).filter(
            models.RunMetadata.key == key)
    runs_query = _filter_runs_by_date(runs_query, start_date, stop_date)
    runs_query = runs_query.values(models.Run.run_at,
                                   models.Run.passes,
                                   models.Run.fails,
                                   models.Run.skips,
                                   models.RunMetadata.value)
    runs = {}
    for run in runs_query:
        if run.run_at not in runs:
            runs[run.run_at] = {run.value: [{
                'pass': run.passes,
                'fail': run.fails,
                'skip': run.skips,
            }]}
        else:
            if run.value not in list(runs[run.run_at].keys()):
                runs[run.run_at][run.value] = [{
                    'pass': run.passes,
                    'fail': run.fails,
                    'skip': run.skips,
                }]
            else:
                runs[run.run_at][run.value].append({
                    'pass': run.passes,
                    'fail': run.fails,
                    'skip': run.skips,
                })
    return runs


def get_time_series_runs_by_key_value(key, value, start_date=None,
                                      stop_date=None, session=None):
    """Get a time series of runs with meta for all runs with a key value pai

    :param str key: The metadata key to use for matching the runs
    :param str value: The metadata value to use for matching the runs
    :param start_date: Optional start date to filter results on
    :param str stop_date: Optional stop date to filter results on
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation


    :return runs: A time series dictionary (where the top level key is a
                  timestamp) that contains all the runs which
    :rtype: dict
    """
    session = session or get_session()
    sub_query = session.query(models.RunMetadata.run_id).filter(
        models.RunMetadata.key == key,
        models.RunMetadata.value == value).subquery()
    run_query = db_utils.model_query(models.Run, session).join(
        models.RunMetadata,
        models.Run.id == models.RunMetadata.run_id).filter(
            models.Run.id.in_(sub_query))
    run_query = _filter_runs_by_date(run_query, start_date, stop_date)
    run_query = run_query.values(models.Run.uuid,
                                 models.Run.passes,
                                 models.Run.fails,
                                 models.Run.skips,
                                 models.Run.run_time,
                                 models.Run.run_at,
                                 models.RunMetadata.key,
                                 models.RunMetadata.value)
    runs = {}
    for run in run_query:
        run_at = run.run_at
        run_id = run.uuid
        if run_at not in runs:
            # We have hit a new time stamp so we need to add a top level key
            # for the timestamp and populate the run list with a new dict for
            # the run
            runs[run_at] = []
            run_dict = {
                'id': run_id,
                'pass': run.passes,
                'fail': run.fails,
                'skip': run.skips,
                'run_time': run.run_time,
                'metadata': {run.key: run.value}
            }
            runs[run_at].append(run_dict)
        else:
            if run_id not in [loc_run["id"] for loc_run in runs[run_at]]:
                # We have hit a new run for an existing timestamp, we need to
                # append a new run dict to the list of runs for that timestamp
                run_dict = {
                    'id': run_id,
                    'pass': run.passes,
                    'fail': run.fails,
                    'skip': run.skips,
                    'run_time': run.run_time,
                    'metadata': {run.key: run.value}
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
                runs[run_at][update_index]['metadata'][run.key] = run.value
    return runs


def get_run_failure_rate_by_key_value_metadata(key, value, start_date=None,
                                               stop_date=None, session=None):
    """Return the failure percentage of runs with a set of run metadata

    :param str key: The metadata key to use for matching the runs
    :param str value: The metadata value to use for matching the runs
    :param start_date: Optional start date to filter results on
    :param str stop_date: Optional stop date to filter results on
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return failure_rate: The percentage of runs that failed, will be None if
                          no runs are found
    :rtype: float
    """
    session = session or get_session()
    base_query = db_utils.model_query(models.Run, session).join(
        models.RunMetadata,
        models.Run.id == models.RunMetadata.run_id).filter(
            models.RunMetadata.key == key,
            models.RunMetadata.value == value)
    base_query = _filter_runs_by_date(base_query, start_date, stop_date)
    fails = base_query.filter(models.Run.fails >= 1).count()
    successes = base_query.filter(models.Run.passes > 0,
                                  models.Run.fails == 0).count()
    if fails == 0 and successes == 0:
        return None
    return (float(fails) / float(successes + fails)) * 100


def add_test_run_attachments(attach_dict, test_run_id, session=None):
    """Add attachments a specific test run.

    This method will take a dictionary and store key blob pair attachments in
    the DB associated with the specified test_run.

    :param dict attachments_dict: A dictionary which will generate a separate
                                  key blob pair row associated with the
                                  test_run_id
    :param str test_run_id: The uuid of the test_run to update. (value of the
                            id column for the row to be updated)
    :param session: Optional session object if one isn't provided a new session
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


def get_recent_failed_runs_by_run_metadata(key, value, num_runs=10,
                                           start_date=None, session=None):
    """Get a list of recent failed runs for a given run metadata pair

    :param str key: The run_metadata key to get failed runs
    :param str value: The run_metadata value to get failed runs
    :param int num_runs: The number of results to fetch, defaults to 10
    :param datetime start_date: The optional starting dates to get runs from.
                                Nothing older than this date will be returned
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return list: The list of recent failed Run objects
    :rtype: subunit2sql.models.Run
    """
    session = session or get_session()
    query = db_utils.model_query(models.Run, session).join(
        models.RunMetadata, models.Run.id == models.RunMetadata.run_id).filter(
            models.RunMetadata.key == key,
            models.RunMetadata.value == value)
    query = _filter_runs_by_date(query, start_date)
    return query.filter(models.Run.fails > 0).order_by(
        models.Run.run_at.desc()).limit(num_runs).all()


def get_runs_by_status_grouped_by_run_metadata(key, start_date=None,
                                               stop_date=None, session=None):
    session = session or get_session()
    val = models.RunMetadata.value
    run_pass_query = session.query(
        sqlalchemy.func.count(models.Run.id), val).filter(
            models.Run.fails == 0, models.Run.passes > 0).join(
                models.RunMetadata,
                models.Run.id == models.RunMetadata.run_id).group_by(
                    val).filter(models.RunMetadata.key == key)
    run_fail_query = session.query(
        sqlalchemy.func.count(models.Run.id), val).filter(
            models.Run.fails > 0, models.Run.passes > 0).join(
                models.RunMetadata,
                models.Run.id == models.RunMetadata.run_id).group_by(
                    val).filter(
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


def get_test_runs_by_status_for_run_ids(status, run_ids, key=None,
                                        session=None, include_run_id=False):
    """Get a list of test run dicts by status for all the specified runs

    :param str status: The test status to filter the returned test runs on
    :param list run_ids: A list of run ids (the uuid column from the runs
                         table) to get the test runs from
    :param str key: An optional run_metadata key to add the values for a run
                    to the output dict for each test_run
    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation
    :param bool include_run_id: boolean flag to enable including the run uuid
                    in the test run dicts returned

    :return test_runs: A list of dicts for the test_runs and associated data
    :rtype: list
    """
    session = session or get_session()
    query = db_utils.model_query(models.TestRun, session).filter(
        models.TestRun.status == status).join(
            models.Test, models.TestRun.test_id == models.Test.id).join(
                models.Run, models.TestRun.run_id == models.Run.id).filter(
                    models.Run.uuid.in_(run_ids))

    if key:
        query = query.join(
            models.RunMetadata,
            models.TestRun.run_id == models.RunMetadata.run_id).filter(
                models.RunMetadata.key == key)
        results = query.values(models.Test.test_id, models.Run.artifacts,
                               models.TestRun.start_time,
                               models.TestRun.start_time_microsecond,
                               models.TestRun.stop_time,
                               models.TestRun.stop_time_microsecond,
                               models.RunMetadata.value,
                               models.Run.uuid)
    else:
        results = query.values(models.Test.test_id, models.Run.artifacts,
                               models.TestRun.start_time,
                               models.TestRun.start_time_microsecond,
                               models.TestRun.stop_time,
                               models.TestRun.stop_time_microsecond,
                               models.Run.uuid)
    test_runs = []
    for result in results:
        test_run = {
            'test_id': result.test_id,
            'link': result.artifacts,
            'start_time': result.start_time,
            'stop_time': result.stop_time,
        }
        if include_run_id:
            test_run['uuid'] = result.uuid
        if result.start_time_microsecond is not None:
            test_run['start_time'] = test_run['start_time'].replace(
                microsecond=result.start_time_microsecond)
        if result.stop_time_microsecond is not None:
            test_run['stop_time'] = test_run['stop_time'].replace(
                microsecond=result.stop_time_microsecond)
        if hasattr(result, "value"):
            test_run[key] = result.value
        test_runs.append(test_run)
    return test_runs


def get_all_run_metadata_keys(session=None):
    """Get a list of all the keys used in the run_metadata table

    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return keys: A list of all keys used in the run_metadata table
    :rtype: list
    """
    session = session or get_session()
    keys = session.query(models.RunMetadata.key).distinct().all()
    return [key[0] for key in keys]


def get_all_test_metadata_keys(session=None):
    """Get a list of all the keys used in the test_metadata table

    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return keys: A list of all keys used in the test_metadata table
    :rtype: list
    """
    session = session or get_session()
    keys = session.query(models.TestMetadata.key).distinct().all()
    return [key[0] for key in keys]


def get_all_test_run_metadata_keys(session=None):
    """Get a list of all the keys used in the test_run_metadata table

    :param session: Optional session object if one isn't provided a new session
                    will be acquired for the duration of this operation

    :return keys: A list of all keys used in the test_run_metadata table
    :rtype: list
    """
    session = session or get_session()
    keys = session.query(models.TestRunMetadata.key).distinct().all()
    return [key[0] for key in keys]
