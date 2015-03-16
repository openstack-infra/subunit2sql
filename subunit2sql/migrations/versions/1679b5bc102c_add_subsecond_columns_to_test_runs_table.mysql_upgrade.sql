--
-- This file is necessary because of an issue with a large MySQL DB having
-- issues with the alter table to add a column
--

CREATE TABLE test_runs_migration LIKE test_runs;
ALTER TABLE test_runs_migration ADD COLUMN start_time_microsecond INTEGER default 0;
ALTER TABLE test_runs_migration ADD COLUMN stop_time_microsecond INTEGER default 0;
LOCK TABLES test_runs write, test_runs_migration write, test_run_metadata write;
INSERT INTO test_runs_migration SELECT id, test_id, run_id, status, start_time, stop_time, MICROSECOND(start_time), MICROSECOND(stop_time) from test_runs;
ALTER TABLE test_run_metadata drop foreign key test_run_metadata_ibfk_1;
UNLOCK TABLES;
-- race condition here - but at worst you'll lose a microsecond of data as rename is very fast and atomic
RENAME TABLE test_runs to test_runs_old, test_runs_migration to test_runs;
ALTER TABLE test_run_metadata ADD CONSTRAINT test_run_metadata_ibfk_1 FOREIGN KEY(test_run_id) REFERENCES test_runs(id);
DROP TABLE test_runs_old;
