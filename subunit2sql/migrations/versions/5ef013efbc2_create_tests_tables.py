"""create tests tables

Revision ID: 5ef013efbc2
Revises: None
Create Date: 2014-06-08 11:18:41.529268

"""

# revision identifiers, used by Alembic.
revision = '5ef013efbc2'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('tests',
                    sa.Column('id', sa.String(36), primary_key=True),
                    sa.Column('test_id', sa.String(256)),
                    sa.Column('run_count', sa.Integer()),
                    sa.Column('success', sa.Integer()),
                    sa.Column('failure', sa.Integer()),
                    mysql_engine='InnoDB')


def downgrade():
    op.drop_table('tables')
