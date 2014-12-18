Work Items for Subunit2SQL
==========================

Short Term
----------
 * Add more unit tests
   * DB API unit tests
   * write_subunit module
 * Flesh out query side of DB API to make it useful for building additional
   tooling.
 * Investigate dropping oslo.db from requirements to enable using other
   config/cli tooling
 * Maybe use raw SQL queries instead of the ORM where it makes sense
 * Improve documentation
   * More usage examples

Longer Term
-----------
 * Add tooling to pull the data and visualize it in fun ways
 * Add some statistics functions on top of the DB api to perform analysis
 * Add a subunit2sql repository type to the testrepository project
