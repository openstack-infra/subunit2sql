===========
Subunit2SQL
===========

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
the `testrepository`_ project which does a good job for centralizing the
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


.. toctree::
   :maxdepth: 2

   user/index
   reference/index
   cli/index
   contributor/index


.. rubric:: Indices and Tables

* :ref:`search`
