Work Items for Subunit2SQL
==========================

Short Term
----------
 * Add a new metadata table for each existing table (run_metadata,
   test_metadata, test_run_metadata) to store extra info from stream like
   tags, or attrs and other information about runs like job name.
 * Add average runtime column to tests table to keep running average of
   how long the test takes to run.
 * Add artifacts option to CLI on subunit2sql to store log links in runs table
 * Add unit tests

Longer Term
-----------
 * Add tooling to pull the data and visualize it in fun ways
 * Add some statistics functions on top of the DB api to perform analysis
