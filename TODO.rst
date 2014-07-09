Work Items for Subunit2SQL
==========================

Short Term
----------
 * Add more unit tests
   * Migration tests
   * DB API unit tests
 * Flesh out query side of DB API to make it useful for building additional
   tooling.
 * Investigate dropping oslo.db from requirements to enable using other
   config/cli tooling
 * Maybe use raw SQL queries instead of the ORM where it makes sense
 * Improve documentation

Longer Term
-----------
 * Add a method of taking a test_run from the DB and create a subunit file
 * Add tooling to pull the data and visualize it in fun ways
 * Add some statistics functions on top of the DB api to perform analysis
