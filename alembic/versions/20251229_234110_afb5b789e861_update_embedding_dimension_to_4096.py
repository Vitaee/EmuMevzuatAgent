"""Update embedding dimension to 4096

Revision ID: afb5b789e861
Revises: 3eaa6a7a367b
Create Date: 2025-12-29 23:41:10.267450

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'afb5b789e861'
down_revision: Union[str, None] = '3eaa6a7a367b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop and recreate the column with new dimension
    # (ALTER TYPE for vector columns with different dimensions requires drop/add)
    op.drop_column('reg_doc_chunk', 'embedding')
    op.add_column('reg_doc_chunk', sa.Column('embedding', Vector(4096), nullable=True))


def downgrade() -> None:
    op.drop_column('reg_doc_chunk', 'embedding')
    op.add_column('reg_doc_chunk', sa.Column('embedding', Vector(1536), nullable=True))
