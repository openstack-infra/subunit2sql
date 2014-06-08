subunit2SQL README
==================

subunit2SQL like it's name implies is a tool used for converting subunit
streams to data in a SQL database. The motivation is that for multiple 
distributed test runs that are generating subunit output it is useful to
store the results in a unified repository. This is the motivation for the
testrepository project which does a good job for centralizing the results from
multiple test runs.

Imagine something like the OpenStack CI system where the same basic test suite
is normally run several hundreds of times a day. To provide useful
introspection on the data from those runs and to build trends over time
the test results need to be stored in a format that allows for easy querying.
SQL databases make a lot of sense for doing this.

subunit2SQL uses alembic migrations to setup a DB schema that can then be used
by the subunit2sql binary to parse subunit streams and populate the DB. 
Additional it provides a DB API that can be used to query information from the
results stored to build other tooling.
