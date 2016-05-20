==================
subunit2SQL README
==================

.. image:: https://img.shields.io/pypi/v/subunit2sql.svg
    :target: https://pypi.python.org/pypi/subunit2sql/
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/dm/subunit2sql.svg
    :target: https://pypi.python.org/pypi/subunit2sql/
    :alt: Downloads

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
you don't have to worry about writing a tool like :ref:`subunit2sql` to use a
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

- Source: http://git.openstack.org/cgit/openstack-infra/subunit2sql
- Bugs, Stories: https://storyboard.openstack.org/#!/project/747

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

This will bring the DB schema up to the latest version for subunit2sql.

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

The only required option is --database-connection. The options can either be
used on the CLI, or put in a config file. If a config file is used you need to
specify the location on the CLI.

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

ChangeLog
=========

To see the release notes go here: `http://docs.openstack.org/releasenotes/subunit2sql/ <http://docs.openstack.org/releasenotes/subunit2sql/>`_
