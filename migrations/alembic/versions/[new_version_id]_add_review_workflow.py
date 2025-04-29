# Create file: migrations/alembic/versions/[new_version_id]_add_review_workflow.py

"""add_review_workflow

Revision ID: [new_version_id]
Revises: 693fd450bf72
Create Date: [current_date]

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '[new_version_id]'
down_revision: Union[str, None] = '693fd450bf72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add review fields to articles table
    op.add_column('articles', sa.Column('review_status', sa.Enum('pending', 'approved', 'rejected', 'needs_revision', name='review_status'), nullable=True))
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
        sa.Column('status', sa.Enum('pending_review', 'approved', 'rejected', 'needs_revision', name='export_status'), nullable=True),
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