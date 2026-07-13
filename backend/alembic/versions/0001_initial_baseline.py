"""Establish an Alembic baseline before domain tables are introduced.

Revision ID: 0001
Revises: None
"""

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Record the initial schema boundary; no domain tables exist in this phase."""


def downgrade() -> None:
    """Remove the baseline revision marker."""
