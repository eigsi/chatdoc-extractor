"""add save state in comments

Revision ID: 96d26b15a881
Revises: 33788268fd4e
Create Date: 2025-05-22 16:35:13.113471

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96d26b15a881'
down_revision: Union[str, None] = '33788268fd4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('comments', sa.Column('save', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('comments', 'save')
    # ### end Alembic commands ###
