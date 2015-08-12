==================
subunit2SQL README
==================

subunit2SQL is a tool for storing test results data in a SQL database. Like
it's name implies it was originally designed around converting `subunit`_
streams to data in a SQL database and the packaged utilities assume a subunit
stream as the input format. However, the data model used for the DB does not
preclude using any test result format. Additionally the analysis tooling built
on top of a database is data format agnostic. However if you choose to use a
different result format as an input for the database additional tooling using
the DB api would need to be created to parse a different test result output
format. It's also worth pointing out that subunit has several language library
bindings available. So as a user you could create a small filter to convert a
different format to subunit. Creating a filter should be fairly easy and then
you don't have to worry about writing a tool like :ref:_`subunit2sql` to use a
different format.

.. _subunit: https://github.com/testing-cabal/subunit/blob/master/README.rst

For multiple distributed test runs that are generating subunit output it is
useful to store the results in a unified repository. This is the motivation for
the _`testrepository` project which does a good job for centralizing the
results from multiple test runs.

.. _testrepository: http://testrepository.readthedocs.org/en/latest/

However, imagine something like the OpenStack CI system where the same basic
test suite is normally run several hundreds of times a day. To provide useful
introspection on the data from those runs and to build trends over time
the test results need to be stored in a format that allows for easy querying.
Using a SQL database makes a lot of sense for doing this, which was the
original motivation for the project.

At a high level subunit2SQL uses alembic migrations to setup a DB schema that
can then be used by the :ref:`subunit2sql` tool to parse subunit streams and
populate the DB. Then there are tools for interacting with the stored data in
the :ref:`subunit2sql-graph` command as well as the :ref:`sql2subunit`
command to create a subunit stream from data in the database. Additionally,
subunit2sql provides a Python DB API that can be used to query information from
the stored data to build other tooling.

Usage
=====

DB Setup
--------

The usage of subunit2sql is split into 2 stages. First you need to prepare a
database with the proper schema; subunit2sql-db-manage should be used to do
this. The utility requires db connection info which can be specified on the
command or with a config file. Obviously the sql connector type, user,
password, address, and database name should be specific to your environment.
subunit2sql-db-manage will use alembic to setup the db schema. You can run the
db migrations with the command::

    subunit2sql-db-manage --database-connection mysql://subunit:pass@127.0.0.1/subunit upgrade head

or with a config file::

    subunit2sql-db-manage --config-file subunit2sql.conf upgrade head

This will bring the DB schema up to the latest version for subunit2sql. Also,
it is worth noting that the schema migrations used in subunit2sql do not
currently support sqlite. While it is possible to fix this, sqlite only
supports a subset of the necessary sql calls used by the migration scripts. As
such, maintaining support for sqlite will be a continual extra effort, so if
support is added back in the future, it is no guarantee that it will remain. In
addition, the performance of running, even in a testing capacity, subunit2sql
with MySQL or Postgres make it worth the effort of setting up one of them to
use subunit2sql.

.. _subunit2sql:

subunit2sql
-----------

Once you have a database setup with the proper database schema you can then use
the subunit2sql command to populate the database with data from your test runs.
subunit2sql takes in a subunit v2 either through stdin or by passing it file
paths as positional arguments to the script. If only a subunit v1 stream is
available, it can be converted to a subunit v2 stream using the subunit-1to2
utility.

There are several options for running subunit2sql, they can be listed with::

    subunit2sql --help

The only required options are the state_path and the database-connections.
These options and the other can either be used on the CLI, or put in a config
file. If a config file is used you need to specify the location on the CLI.

Most of the optional arguments deal with how subunit2sql interacts with the
SQL DB. However, it is worth pointing out that the artifacts option and the
run_meta option are used to pass additional metadata into the database for the
run(s) being added. The artifacts option should be used to pass in a url or
path that points to any logs or other external test artifacts related to the
run being added. The run_meta option takes in a dictionary which will be added
to the database as key value pairs associated with the run being added.

.. _sql2subunit:

sql2subunit
-----------

The sql2subunit utility is used for taking a run_id and creating a subunit
v2 stream from the data in the DB about that run. To create a new subunit
stream run::

    sql2subunit $RUN_ID

along with any options that you would normally use to either specify a config
file or the DB connection info. Running this command will print to stdout the
subunit v2 stream for the run specified by $RUN_ID, unless the --out_path
argument is specified to write it to a file instead.

Release Notes
=============

0.8.1
-----
 * Fix an issue with migration 1ff737bef438 which was failing on creating an
   index on mysql environments using multi-byte utf8.

0.8.0
-----
 * DB API improvements:
  * New methods to get runs by key value pair in run_metadata and get
    the run_metadata for a run
 * Documentation updates
 * A new migration is added to add additional indexes on common search
   patterns
 * Several bugfixes and code cleanups


0.7.0
-----
 * Initial external plugin support for the subunit2sql-graph command
 * Internal code cleanup around the use of the oslo namespace package
 * A temporary version cap on oslo.db limiting it to < 2.0.0 because of a
   subunit2sql dependency on an internal oslo.db interface (this will be removed
   in a future release)

0.6.0
-----
 * subunit2sql-graph improvements:
  * Use setuptools extras to list graph requirements
  * Adds documentation
  * New graph type to show daily test count over time
  * Graph cleanups
 * Start of attachments support
  * Adds a new table to store arbitrary attachments from a subunit stream
  * Support to the subunit2sql utility to store attachments in the attachments
    table

0.5.1
-----
* Remove matplotlib from requirements file to avoid requiring additional C
  dependencies in CI systems. (the next release will switch to using extras
  to articulate the additional dependencies for the graphing tool)

0.5.0
-----
 * Several new db api methods to:
   * Delete old runs and test_runs
   * Get a test status time series dict
   * Get a test uuid from a test_id
   * Get date bounded per status counts for a test
 * Adds a new subunit2sql-db-manage subcommand to expire runs and
   test_runs
 * Reworked subunit2sql-graph command to be modular extendable
 * Added 2 new graph types to subunit2sql-graph, agg_count and failures
 * Improved the formatting for the previously existing run_time graph

0.4.2
-----
 * Fixes an issue with the path finding in 1679b5bc102 which cause failures
   when running the migration from an installed version of subunit2sql

0.4.1
-----
 * Fixes an issue with running the 1679b5bc102 DB migration on large mysql
   databases running on trove by hand coding the SQL for running on MySQL

0.4.0
-----
 * Add a new tool, subunit2sql-graph, for graphing a test's run_time over time
 * Fix to ensure attrs are set in the output from sql2subunit
 * Add a new DB migration to separate microseconds for start and stop time in
   the test_runs table into separate columns
 * Add db api methods to get a time series of run_times for a specific test,
   to update an existing test_run row, and methods to get a list of recent run
   uuids
 * Several miscellaneous bug fixes

0.3.0
-----
 * Add new db api methods to extract more test information from a given run
 * Add a --average flah to sql2subunit for using the aggregate test data in
   the tests table to write a subunit stream
 * Bug and performance fixes around the sql2subunit command
 * Documentation updates

0.2.1
-----
 * Documentation Improvements
 * Fixed the output from the --version flag
 * Added an option to set the run_id when adding a new run to the db
 * Several code cleanups

0.2.0
-----
 * Adds 2 new commands sql2subunit, and subunit2sql-db-manage
 * Migration Testing improvements
 * Drops the state_path config option which was unused
 * Added sample config files and a method for generating up to date copies
 * Adds a migration to add a run_at column to the runs table
 * Adds a migration to populate the run_time column in the tests table for
   rows that do not have a value there
 * Several bug fixes and code cleanups


0.1
---
 * First release
