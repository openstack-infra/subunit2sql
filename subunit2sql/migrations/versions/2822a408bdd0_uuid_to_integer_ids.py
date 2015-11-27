# Copyright 2015 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""uuid to integer ids

Revision ID: 2822a408bdd0
Revises: b96122f780
Create Date: 2015-10-14 14:18:18.820521

"""

# revision identifiers, used by Alembic.
revision = '2822a408bdd0'
down_revision = 'b96122f780'

from alembic import context
from alembic import op
import sqlalchemy as sa


def upgrade():
    migration_context = context.get_context()
    if migration_context.dialect.name == 'sqlite':
        new_id_type = sa.Integer
    else:
        new_id_type = sa.BigInteger
    # Create new tests table
    op.create_table('tests_new',
                    sa.Column('id', sa.String(36)),
                    sa.Column('new_id', new_id_type, primary_key=True,
                              autoincrement=True, nullable=False),
                    sa.Column('test_id', sa.String(256), nullable=False),
                    sa.Column('run_count', sa.Integer()),
                    sa.Column('success', sa.Integer()),
                    sa.Column('failure', sa.Integer()),
                    sa.Column('run_time', sa.Float(), nullable=True),
                    mysql_engine='InnoDB')

    # Create new test_runs table
    op.create_table('test_runs_new',
                    sa.Column('id', sa.String(36)),
                    sa.Column('new_id', new_id_type, primary_key=True,
                              nullable=False),
                    sa.Column('test_id', sa.String(36), nullable=False),
                    sa.Column('new_test_id', new_id_type),
                    sa.Column('run_id', sa.String(36), nullable=False),
                    sa.Column('new_run_id', new_id_type),
                    sa.Column('status', sa.String(256)),
                    sa.Column('start_time', sa.DateTime()),
                    sa.Column('stop_time', sa.DateTime()),
                    sa.Column('start_time_microsecond', sa.Integer(),
                              default=0),
                    sa.Column('stop_time_microsecond', sa.Integer(),
                              default=0),
                    mysql_engine='InnoDB')

    # Create new runs table
    op.create_table('runs_new',
                    sa.Column('id', sa.String(36)),
                    sa.Column('new_id', new_id_type(), primary_key=True,
                              nullable=False, autoincrement=True),
                    sa.Column('skips', sa.Integer()),
                    sa.Column('fails', sa.Integer()),
                    sa.Column('passes', sa.Integer()),
                    sa.Column('run_time', sa.Float()),
                    sa.Column('artifacts', sa.Text()),
                    sa.Column('run_at', sa.DateTime()),
                    mysql_engine='InnoDB')

    # Create new run_metadata table
    op.create_table('run_metadata_new',
                    sa.Column('id', sa.String(36),
                              nullable=False),
                    sa.Column('new_id', new_id_type(), nullable=False,
                              primary_key=True, autoincrement=True),
                    sa.Column('key', sa.String(255)),
                    sa.Column('value', sa.String(255)),
                    sa.Column('run_id', sa.String(36), nullable=False),
                    sa.Column('new_run_id', new_id_type),
                    mysql_engine='InnoDB')

    # Create new test runs metadata table
    op.create_table('test_run_metadata_new',
                    sa.Column('id', sa.String(36), nullable=False),
                    sa.Column('new_id', new_id_type, primary_key=True,
                              nullable=False, autoincrement=True),
                    sa.Column('key', sa.String(255)),
                    sa.Column('value', sa.String(255)),
                    sa.Column('test_run_id', sa.String(36),
                              nullable=False),
                    sa.Column('new_test_run_id', new_id_type),
                    mysql_engine='InnoDB')

    # Create new test metadata table
    op.create_table('test_metadata_new',
                    sa.Column('id', sa.String(36),
                              nullable=False),
                    sa.Column('new_id', new_id_type, primary_key=True,
                              nullable=False, autoincrement=True),
                    sa.Column('key', sa.String(255)),
                    sa.Column('value', sa.String(255)),
                    sa.Column('test_id', sa.String(36), nullable=False),
                    sa.Column('new_test_id', new_id_type),
                    mysql_engine='InnoDB')
    # Create new tests attachments table
    op.create_table('attachments_new',
                    sa.Column('id', sa.String(36), nullable=False),
                    sa.Column('new_id', new_id_type, primary_key=True,
                              nullable=False, autoincrement=True),
                    sa.Column('test_run_id', sa.String(36), nullable=False),
                    sa.Column('new_test_run_id', new_id_type),
                    sa.Column('label', sa.String(255)),
                    sa.Column('attachment', sa.LargeBinary()),
                    mysql_engine='InnoDB')

    # Now populate new tables
    if migration_context.dialect.name == 'postgresql':
        key_word = 'key'
    else:
        key_word = '`key`'
    op.execute('INSERT INTO tests_new (id, test_id, run_count, success, '
               'failure, run_time) SELECT id, test_id, run_count, success, '
               'failure, run_time FROM tests')
    op.execute('INSERT INTO runs_new (id, skips, fails, passes, run_time, '
               'artifacts, run_at) SELECT id, skips, fails, passes, run_time, '
               'artifacts, run_at FROM runs')
    op.execute('INSERT INTO test_runs_new (id, test_id, new_test_id, run_id, '
               'new_run_id, status, start_time, stop_time, '
               'start_time_microsecond, stop_time_microsecond) SELECT tr.id, '
               'tr.test_id, tn.new_id, tr.run_id, rn.new_id, status, '
               'start_time, stop_time, start_time_microsecond, '
               'stop_time_microsecond FROM test_runs tr INNER JOIN runs_new '
               'rn ON rn.id = tr.run_id INNER JOIN tests_new tn '
               'ON tn.id=tr.test_id')
    op.execute('INSERT INTO test_metadata_new (id, {}, value, test_id, '
               'new_test_id) SELECT tm.id, tm.key, tm.value, tm.test_id, '
               'tn.new_id FROM test_metadata tm INNER JOIN tests_new tn '
               'ON tn.id = tm.test_id'.format(key_word))
    op.execute('INSERT INTO test_run_metadata_new (id, {}, value, '
               'test_run_id, new_test_run_id) SELECT trm.id, trm.key, '
               'trm.value, trm.test_run_id, trn.new_id FROM test_run_metadata '
               'trm INNER JOIN test_runs_new trn ON trm.test_run_id = '
               'trn.id'.format(key_word))
    op.execute('INSERT INTO attachments_new (id, test_run_id, '
               'new_test_run_id, label, attachment) SELECT a.id, '
               'a.test_run_id, trn.new_id, a.label, a.attachment FROM '
               'attachments a INNER JOIN test_runs_new trn '
               'ON a.test_run_id = trn.id')
    op.execute('INSERT INTO run_metadata_new (id, {}, value, run_id, '
               'new_run_id) SELECT rm.id, rm.key, rm.value, rm.run_id, '
               'rn.new_id FROM run_metadata rm INNER JOIN runs_new rn '
               'ON rm.run_id = rn.id'.format(key_word))

    # Switch columns
    if migration_context.dialect.name == 'postgresql':

        op.drop_column('attachments_new', 'id')
        op.alter_column('attachments_new', 'new_id', new_column_name='id',
                        existing_type=new_id_type,
                        autoincrement=True)
        op.drop_column('attachments_new', 'test_run_id')
        op.alter_column('attachments_new', 'new_test_run_id',
                        new_column_name='test_run_id')
        op.drop_column('test_run_metadata_new', 'id')
        op.alter_column('test_run_metadata_new', 'new_id',
                        new_column_name='id',
                        existing_type=new_id_type,
                        autoincrement=True)
        op.drop_column('test_run_metadata_new', 'test_run_id')
        op.alter_column('test_run_metadata_new', 'new_test_run_id',
                        new_column_name='test_run_id',
                        existing_type=new_id_type)
        op.drop_column('run_metadata_new', 'id')
        op.alter_column('run_metadata_new', 'new_id',
                        new_column_name='id')
        op.drop_column('run_metadata_new', 'run_id')
        op.alter_column('run_metadata_new', 'new_run_id',
                        new_column_name='run_id',
                        existing_type=new_id_type)
        op.drop_column('test_metadata_new', 'id')
        op.alter_column('test_metadata_new', 'new_id',
                        new_column_name='id')
        op.drop_column('test_metadata_new', 'test_id')
        op.alter_column('test_metadata_new', 'new_test_id',
                        new_column_name='test_id',
                        existing_type=new_id_type)
        op.drop_column('test_runs_new', 'id')
        op.alter_column('test_runs_new', 'new_id',
                        new_column_name='id')
        op.drop_column('test_runs_new', 'test_id')
        op.alter_column('test_runs_new', 'new_test_id',
                        new_column_name='test_id',
                        existing_type=new_id_type)
        op.drop_column('test_runs_new', 'run_id')
        op.alter_column('test_runs_new', 'new_run_id',
                        new_column_name='run_id',
                        existing_type=new_id_type)
        op.drop_column('tests_new', 'id')
        op.alter_column('tests_new', 'new_id',
                        new_column_name='id')
        op.alter_column('runs_new', 'id',
                        new_column_name='uuid')
        op.alter_column('runs_new', 'new_id',
                        new_column_name='id')
    else:
        # http://dev.mysql.com/doc/refman/5.7/en/innodb-online-ddl-syntax.html
        # Ths is a specific workaround for limited tmpdir space in the
        # OpenStack infra MySQL server. With old_alter_table=OFF, mysql creates
        # temporary files that are very large while building the new table.
        # So generally, while the old method is less desirable for concurrency,
        # it is safer, and we don't need online DDL since this migration
        # uses a _new table anyway.
        if migration_context.dialect.name == 'mysql':
            op.execute('SET SESSION old_alter_table=ON')
        with op.batch_alter_table("attachments_new") as batch_op:
            batch_op.drop_column('id')
            batch_op.alter_column('new_id', new_column_name='id',
                                  primary_key=True,
                                  existing_type=new_id_type,
                                  autoincrement=True)
            batch_op.drop_column('test_run_id')
            batch_op.alter_column('new_test_run_id',
                                  new_column_name='test_run_id',
                                  existing_type=new_id_type)
        with op.batch_alter_table("test_run_metadata_new") as batch_op:
            batch_op.drop_column('id')
            batch_op.alter_column('new_id', new_column_name='id',
                                  primary_key=True,
                                  existing_type=new_id_type,
                                  autoincrement=True)
            batch_op.drop_column('test_run_id')
            batch_op.alter_column('new_test_run_id',
                                  new_column_name='test_run_id',
                                  existing_type=new_id_type)
        with op.batch_alter_table("run_metadata_new") as batch_op:
            batch_op.drop_column('id')
            batch_op.alter_column('new_id', new_column_name='id',
                                  primary_key=True,
                                  existing_type=new_id_type,
                                  autoincrement=True)
            batch_op.drop_column('run_id')
            batch_op.alter_column('new_run_id', new_column_name='run_id',
                                  existing_type=new_id_type)
        with op.batch_alter_table("test_metadata_new") as batch_op:
            batch_op.drop_column('id')
            batch_op.alter_column('new_id', new_column_name='id',
                                  primary_key=True,
                                  existing_type=new_id_type,
                                  autoincrement=True)
            batch_op.drop_column('test_id')
            batch_op.alter_column('new_test_id', new_column_name='test_id',
                                  existing_type=new_id_type)
        with op.batch_alter_table("test_runs_new") as batch_op:
            batch_op.drop_column('id')
            batch_op.alter_column('new_id', new_column_name='id',
                                  primary_key=True,
                                  existing_type=new_id_type,
                                  autoincrement=True)
            batch_op.drop_column('test_id')
            batch_op.alter_column('new_test_id', new_column_name='test_id',
                                  existing_type=new_id_type)
            batch_op.drop_column('run_id')
            batch_op.alter_column('new_run_id', new_column_name='run_id',
                                  existing_type=new_id_type)
        with op.batch_alter_table("tests_new") as batch_op:
            batch_op.drop_column('id')
            batch_op.alter_column('new_id', new_column_name='id',
                                  primary_key=True,
                                  existing_type=new_id_type,
                                  autoincrement=True)
        with op.batch_alter_table("runs_new") as batch_op:
            batch_op.alter_column('id', new_column_name='uuid',
                                  existing_type=sa.VARCHAR(36))
            batch_op.alter_column('new_id', new_column_name='id',
                                  primary_key=True,
                                  existing_type=new_id_type,
                                  autoincrement=True)

    # Sanity checks
    errors = []
    for table in ('tests', 'runs', 'test_runs', 'test_metadata',
                  'test_run_metadata', 'run_metadata', 'attachments'):
        old_count = op.get_bind().execute(
            "SELECT COUNT(id) FROM {}".format(table)).first()[0]
        new_count = op.get_bind().execute(
            "SELECT COUNT(id) FROM {}_new".format(table)).first()[0]
        if old_count != new_count:
            errors.append("{} has {} rows and {}_new has {} rows".format(
                table, old_count, table, new_count))
    if errors:
        raise RuntimeError("Failed count checks: {}".format(','.join(errors)))

    # Rename tables
    op.rename_table("tests", "tests_old")
    op.rename_table("runs", "runs_old")
    op.rename_table("test_runs", "test_runs_old")
    op.rename_table("test_metadata", "test_metadata_old")
    op.rename_table("test_run_metadata", "test_run_metadata_old")
    op.rename_table("run_metadata", "run_metadata_old")
    op.rename_table("attachments", "attachments_old")
    op.rename_table("tests_new", "tests")
    op.rename_table("runs_new", "runs")
    op.rename_table("test_runs_new", "test_runs")
    op.rename_table("test_metadata_new", "test_metadata")
    op.rename_table("test_run_metadata_new", "test_run_metadata")
    op.rename_table("run_metadata_new", "run_metadata")
    op.rename_table("attachments_new", "attachments")

    # Drop olds
    op.drop_table("test_run_metadata_old")
    op.drop_table("attachments_old")
    op.drop_table("test_metadata_old")
    op.drop_table("run_metadata_old")
    op.drop_table("test_runs_old")
    op.drop_table("runs_old")
    op.drop_table("tests_old")

    # Create indexes -- sqlite keeps the old ones around for some reason
    if migration_context.dialect.name != 'sqlite':
        op.create_index('ix_test_ids', 'tests', ['id', 'test_id'],
                        mysql_length={'test_id': 30})
        op.create_index('ix_test_key_value', 'test_metadata',
                        ['key', 'value'])
        op.create_index('ix_test_run_key_value', 'test_run_metadata',
                        ['key', 'value'])
        op.create_index('ix_run_key_value', 'run_metadata',
                        ['key', 'value'])
        op.create_index('ix_test_id_status', 'test_runs',
                        ['test_id', 'status'], mysql_length={'status': 30})
        op.create_index('ix_test_id_start_time', 'test_runs',
                        ['test_id', 'start_time'])
        op.create_unique_constraint('uq_test_runs', 'test_runs',
                                    ['test_id', 'run_id'])
    op.create_index('ix_run_uuid', 'runs', ['uuid'])
    op.create_index('ix_tests_test_id', 'tests', ['test_id'], mysql_length=30)
    op.create_index('ix_test_runs_test_id', 'test_runs', ['test_id'])
    op.create_index('ix_test_runs_run_id', 'test_runs', ['run_id'])
    op.create_index('ix_test_runs_start_time', 'test_runs', ['start_time'])
    op.create_index('ix_test_runs_stop_time', 'test_runs', ['stop_time'])


def downgrade():
    raise NotImplementedError()
