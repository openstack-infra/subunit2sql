Subunit2SQL Graphs
==================
subunit2sql includes a utilty to generate various graphs from the data in a
database. This is used to provide a more visual analysis of the data contained
in the DB.

Installing subunit2sql-graph
----------------------------
The subunit2sql-graph entry point will be installed when you run install on
the subunit2sql endpoint. However, there are a couple of additional dependencies
needed to use it. These are listed as setuptools extras as they are fairly
heavyweight and depend on several C libraries being present. To install the
additional dependencies to use the graph command you can use::

    pip install subunit2sql[graph]

or::

    pip install $PATH_TO_subuni2sql[graph]


Using subunit2sql-graph
-----------------------

After you install subunit2sql and the additional dependencies you invoke the
graph command with::

  subunit2sql-graph

It is required that you also specify a database to tell the graph command to
tell the graph command how to connect to the DB to use for generating the
graph. This is done using the same syntax as other subunit2sql commands::

  subunit2sql-graph --database-connection mysql://subunit:pass@127.0.0.1/subunit

The other common required argument is the output file which is **-o** or
**--output**. This arg is a straight passthrough to a matplotlib call which uses
the extension to generate the graph file. So make sure you're using the file
format extension you want the output to be generated in.

You then provide a graph subcommand to tell subunit2sql-graph which type of
graph to generate and provide any args needed to the command. Also, note that
graph specific args must come after the graph on the CLI and general args must
come before. This will likely change in the future, but at least for right now
it's an existing issue.

There are currently 3 graphs that it can generate:

Run Time
--------
This graph is used to show the run time of a single test over time. It generates
a line graph displaying the time series data for successful run times for the
specified test from the test_runs table.

For example running something like::

  subunit2sql-graph --database-connection mysql://test:test@localhost/subunit2sql --output test.png --title 'Test Run Times' run_time 0291fc87-1a6d-4c6b-91d2-00a7bb5c63e6

will generate a graph like:

.. image:: graph-run_time.png

you can refer to the help on the graph command for run_time to see the full
option list with something like::

  subunit2sql-graph run_time --help


Failures
--------
This graph is used to show the number of failures, successes, and skips of a
single test over time. It generates a line graph displaying the time series data
for each of these counts (grouped daily) as different line plots on the same graph.

For example running something like::

  subunit2sql-graph --database-connection mysql://test:test@localhost/subunit2sql --output test.png --title 'Test Failure Count' failures 0291fc87-1a6d-4c6b-91d2-00a7bb5c63e6

will generate a graph like:

.. image:: graph-failures.png

The command will also display the percentages of each status category, for
example with the above command something like::

  Fail Percentage: 0.2045%
  Success Percentage: 99.7955%
  Skip Percentage: 0.0000

will be printed to STDOUT.

You can refer to the help on the graph command for run_time to see the full
option list with something like::

  subunit2sql-graph failures --help


Aggregate Counts
-----------------

This graph is used to show the aggregate number of failures, successes, and
skips of multiple tests from the database. It a stacked bar graph showing
the count of each category for all the provided tests. If no tests are provided
this graph tries to use all the tests from the DB. (which depending on the
data set can be difficult to render)

For example running something like::

  subunit2sql-graph --database-connection mysql://test:test@localhost/subunit2sql --output test.png --title 'Test Failure Failures' agg_count

will generate a graph like:

.. image:: graph-count.png

you can refer to the help on the graph command for run_time to see the full
option list with something like::

  subunit2sql-graph failures --help
