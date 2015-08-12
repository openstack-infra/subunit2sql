Work Items for Subunit2SQL
==========================

 * Add attachments support to the sql2subunit utility
 * Enable sqlite support for the data migrations to enable using sqlite as
   a database backend
 * Add more unit tests
   * DB API unit tests
   * write_subunit module
 * Flesh out query side of DB API to make it useful for building additional
   tooling.
 * Investigate dropping oslo.db from requirements to enable using other
   config/cli tooling
 * Add a subunit2sql repository type to the testrepository project
