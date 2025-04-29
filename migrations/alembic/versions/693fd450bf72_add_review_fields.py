"""add_review_fields

Revision ID: 693fd450bf72
Revises: 4ad3276a1a67
Create Date: 2025-04-28 17:24:51.059695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '693fd450bf72'
down_revision: Union[str, None] = '4ad3276a1a67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the enum types first
    review_status_enum = postgresql.ENUM('pending', 'approved', 'rejected', 'needs_revision', name='review_status')
    review_status_enum.create(op.get_bind())
    
    export_status_enum = postgresql.ENUM('pending_review', 'approved', 'rejected', 'needs_revision', name='export_status')
    export_status_enum.create(op.get_bind())
    
    # Add review fields to articles table
    op.add_column('articles', sa.Column('review_status', sa.Enum('pending', 'approved', 'rejected', 'needs_revision', name='review_status', create_type=False), nullable=True))
    op.add_column('articles', sa.Column('review_comments', sa.Text(), nullable=True))
    op.add_column('articles', sa.Column('reviewed_by', sa.String(255), nullable=True))
    op.add_column('articles', sa.Column('review_date', sa.DateTime(timezone=True), nullable=True))
    
    # Create article_exports table
    op.create_table('article_exports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('doc_id', sa.String(255), nullable=False),
        sa.Column('folder_id', sa.String(255), nullable=False),
        sa.Column('doc_url', sa.String(512), nullable=True),
        sa.Column('export_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('status', sa.Enum('pending_review', 'approved', 'rejected', 'needs_revision', name='export_status', create_type=False), nullable=True),
        sa.Column('review_comments', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.String(255), nullable=True),
        sa.Column('review_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop article_exports table
    op.drop_table('article_exports')
    
    # Drop review fields from articles table
    op.drop_column('articles', 'review_date')
    op.drop_column('articles', 'reviewed_by')
    op.drop_column('articles', 'review_comments')
    op.drop_column('articles', 'review_status')
    
    # Drop the enum types
    postgresql.ENUM(name='export_status').drop(op.get_bind())
    postgresql.ENUM(name='review_status').drop(op.get_bind())