"""create runs table

Revision ID: 1f92cfe8a6d3
Revises: 5ef013efbc2
Create Date: 2014-06-08 14:29:17.622700

"""

# revision identifiers, used by Alembic.
revision = '1f92cfe8a6d3'
down_revision = '5ef013efbc2'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('runs',
                    sa.Column('id', sa.String(36), primary_key=True),
                    sa.Column('skips', sa.Integer()),
                    sa.Column('fails', sa.Integer()),
                    sa.Column('pass', sa.Integer()),
                    sa.Column('run_time', sa.Integer()),
                    sa.Column('artifacts', sa.Text()),
                    mysql_engine=True)


def downgrade():
    op.drop_table('runs')
