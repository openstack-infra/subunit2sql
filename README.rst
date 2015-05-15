==================
subunit2SQL README
==================

subunit2SQL like it's name implies is a tool used for converting subunit
streams to data in a SQL database. The motivation is that for multiple
distributed test runs that are generating subunit output it is useful to
store the results in a unified repository. This is the motivation for the
testrepository project which does a good job for centralizing the results from
multiple test runs.

However, imagine something like the OpenStack CI system where the same basic
test suite is normally run several hundreds of times a day. To provide useful
introspection on the data from those runs and to build trends over time
the test results need to be stored in a format that allows for easy querying.
Using a SQL database makes a lot of sense for doing this.

subunit2SQL uses alembic migrations to setup a DB schema that can then be used
by the subunit2sql binary to parse subunit streams and populate the DB.
Additionally, it provides a DB API that can be used to query information from
the results stored to build other tooling.

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

Running subunit2sql
-------------------

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

Creating a v2 Subunit Stream from the DB
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The sql2subunit utility is used for taking a run_id and creating a subunit
v2 stream from the data in the DB about that run. To create a new subunit
stream run::

    sql2subunit $RUN_ID

along with any options that you would normally use to either specify a config
file or the DB connection info. Running this command will print to stdout the
subunit v2 stream for the run specified by $RUN_ID, unless the --out_path
argument is specified to write it to a file instead.

Installation Notes
==================

To use the subunit2sql-graph command you need to install matplotlib, the graph
generation will not work without it installed. However it's not included in the
requirements file as a temporary measure to avoid some additional C dependencies
in CI. This will be corrected in a future bug fix release, but for the time
being this is a constraint.


Release Notes
=============

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
