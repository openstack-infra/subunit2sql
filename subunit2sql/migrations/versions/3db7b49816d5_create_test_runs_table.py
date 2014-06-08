"""create test_runs table

Revision ID: 3db7b49816d5
Revises: 1f92cfe8a6d3
Create Date: 2014-06-08 14:34:56.786781

"""

# revision identifiers, used by Alembic.
revision = '3db7b49816d5'
down_revision = '1f92cfe8a6d3'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('test_runs',
                    sa.Column('id', sa.String(36), primary_key=True),
                    sa.Column('test_id', sa.String(36),
                              sa.ForeignKey('tests.id'),
                              nullable=False, index=True),
                    sa.Column('run_id', sa.String(36),
                              sa.ForeignKey('runs.id'),
                              nullable=False, index=True),
                    sa.Column('status', sa.String(256)),
                    sa.Column('start_time', sa.DateTime()),
                    sa.Column('stop_time', sa.DateTime()),
                    mysql_engine='InnoDB')


def downgrade():
    op.drop_table('test_runs')
