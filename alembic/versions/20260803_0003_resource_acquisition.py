"""resource acquisition and supply chain safety

Revision ID: 20260803_0003
Revises: 20260731_0002
Create Date: 2026-08-03 00:03:00.000000

Phase 29: resources / resource_events 表。

claim_token 只保存 SHA-256 hash（claim_token_hash），原始 token 永不入库，
也不写入 event payload。状态机校验由 CHECK constraint 保护。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260803_0003"
down_revision: str | None = "20260731_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resources",
        sa.Column("resource_id", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("request_sha256", sa.Text(), nullable=False),
        sa.Column(
            "request_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "approval_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=True),
        # 原始 claim_token 永不入库；只保存 SHA-256 hash。
        sa.Column("claim_token_hash", sa.Text(), nullable=True),
        sa.Column(
            "heartbeat_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "manifest_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "error_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('awaiting_approval','queued','fetching',"
            "'validating','published','rejected','cancelled',"
            "'failed_retryable','failed_terminal',"
            "'reconciliation_required')",
            name="ck_resources_valid_status",
        ),
        sa.PrimaryKeyConstraint(
            "resource_id",
            name="pk_resources",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_resources_idempotency_key",
        ),
    )

    op.create_index(
        "ix_resources_claim",
        "resources",
        ["status", "available_at", "created_at"],
    )
    op.create_index(
        "ix_resources_lease",
        "resources",
        ["status", "lease_expires_at"],
    )

    op.create_table(
        "resource_events",
        sa.Column(
            "event_id",
            sa.BigInteger(),
            sa.Identity(),
            nullable=False,
        ),
        sa.Column("resource_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["resources.resource_id"],
            ondelete="CASCADE",
            name="fk_resource_events_resource_id_resources",
        ),
        sa.PrimaryKeyConstraint(
            "event_id",
            name="pk_resource_events",
        ),
    )

    op.create_index(
        "ix_resource_events_resource_event",
        "resource_events",
        ["resource_id", "event_id"],
    )


def downgrade() -> None:
    raise RuntimeError(
        "Phase 29 downgrade 可能丢失 resource 审批/获取历史；"
        "请从数据库备份恢复，不提供自动 downgrade"
    )
