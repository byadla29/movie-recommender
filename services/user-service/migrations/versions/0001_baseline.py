"""Baseline: empty schema. Real tables arrive in Phase 2.

Having a baseline revision lets /ready verify "migrations at head" from day one, and gives
every later migration a parent.

Revision ID: 0001
Revises:
Create Date: 2026-11-18
"""

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
