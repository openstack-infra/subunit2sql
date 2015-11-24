==========================
The subunit2sql Data Model
==========================

The subunit2sql data model consists of 3 basic data types: runs, tests, and
test_runs. Each of these 3 types have an associated key value pair metadata table to store arbitrary metadata about any specific row.

Runs
----
Runs represent an individual test run, or in other words, a complete subunit
stream. They are used to track how many streams have been stored in the db and
high level information about them

Properties:

* **uuid**: A unique human-readable identifier for the run.
* **passes**: The total number of successful tests in the run.
* **fails**: The total number of failed tests during the run.
* **skips**: The total number of skipped tests during the run.
* **run_time**: The sum of the duration of executed tests during the run. Note,
  this is not the time it necessarily took for the run to finish. For
  example, the time for setUpClass and tearDownClass (assuming the
  stream is from a python unittest run) would not be factored in. (as
  they aren't stored in the subunit stream) Also, if the tests are
  being run in parallel since this is just a raw sum this is not
  factored in.
* **artifacts**: An optional link to where the logs or any other artifacts from
  the run are stored.
* **run_at**: The time at which the run was stored in the DB.

Tests
-----
Tests are the higher level grouping of unique tests across all runs. They are
used to aggregate the information about an individual tests from all the runs
stored in the db.

Properties:

* **test_id**: This would be normally be considered the test name, it is the id
  used in the subunit stream for an individual test
* **success**: The total number of times this test has been run successfully
* **failure**: The total number of times this test has failed
* **run_count**: The total number of times this test has been executed
  (obviously this excludes skips) it should be the sum of the success and
  failure columns
* **run_time**: The moving average of the total duration of each test execution



Test Runs
---------
Test runs represent the individual execution of a test as part of run. They are
used for recording all the information about a single test's run.

Properties:

* **test_id**: The id representing the test which was run. This correlates
               to the internal id column of the Tests table (And not the
               test_id column).
* **run_id**: The id representing the run which this was part of. This
              correlates to the internal id column of the Runs table (And not
              the uuid column).
* **status**: The outcome of the test. The valid values here are:
  exists, xfail, unxsuccess, success, fail, skip. You can refer to
  the `testtools documentation <http://testtools.readthedocs.org/en/latest/api.html#testtools.StreamResult.status>`_
  for the details on each status.
* **start_time**: The timestamp when test execution started
* **start_time_microsecond**: The microsecond component of the timestamp when
                              test execution started
* **stop_time**: The timestamp when the test finished executing
* **stop_time_microsecond**: The microsecond component of the timestamp when
                             test execution finished

Attachments
-----------
Attachments represent the file attachments in the subunit stream for a
particular test_run.

Properties:

* **test_run_id**: The id representing the test_run the attachment is
                   associated with. This correlates to the internal id column
                   of the the TestRuns table.
* **label**: The label for the attachment
* **attachment**: The actual attachment
