=====
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

If you want to use a subunit stream with non-subunit data mixed in you can do
this with the optional argument --non_subunit_name. This will treat all the
non-subunit data as a file attachment with the specified name.

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
