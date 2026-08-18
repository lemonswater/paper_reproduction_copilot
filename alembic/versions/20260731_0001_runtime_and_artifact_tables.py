"""runtime and artifact tables

Revision ID: 0001
Revises:
Create Date: 2026-07-31 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("job_id", sa.Text, nullable=False),
        sa.Column(
            "idempotency_key",
            sa.Text,
            nullable=False,
        ),
        sa.Column("request_hash", sa.Text, nullable=False),
        sa.Column("thread_id", sa.Text, nullable=False),
        sa.Column("run_id", sa.Text, nullable=False),
        sa.Column("run_dir", sa.Text, nullable=False),
        sa.Column(
            "request_json",
            postgresql.JSONB,
            nullable=False,
        ),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column(
            "version",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "attempt_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column("max_attempts", sa.Integer, nullable=False),
        sa.Column(
            "wait_generation",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column("worker_id", sa.Text),
        sa.Column("claim_token", sa.Text),
        sa.Column(
            "claimed_at",
            sa.DateTime(timezone=True),
        ),
        sa.Column(
            "heartbeat_at",
            sa.DateTime(timezone=True),
        ),
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "interrupt_nodes_json",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "interrupts_json",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("pending_resume_id", sa.Text),
        sa.Column(
            "cancel_requested",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("cancellation_reason", sa.Text),
        sa.Column("result_json", postgresql.JSONB),
        sa.Column("error_json", postgresql.JSONB),
        sa.Column("reconciliation_json", postgresql.JSONB),
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
        sa.PrimaryKeyConstraint("job_id", name="pk_jobs"),
        sa.CheckConstraint(
            "status IN ('queued','running','waiting_for_input',"
            "'cancelling','succeeded','failed','cancelled',"
            "'reconciliation_required')",
            name="ck_jobs_valid_status",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_jobs_idempotency_key",
        ),
        sa.UniqueConstraint("thread_id", name="uq_jobs_thread_id"),
        sa.UniqueConstraint("run_id", name="uq_jobs_run_id"),
        sa.UniqueConstraint("run_dir", name="uq_jobs_run_dir"),
    )
    op.create_index(
        "ix_jobs_claim",
        "jobs",
        [
            "status",
            "cancel_requested",
            "available_at",
            "created_at",
        ],
    )
    op.create_index(
        "ix_jobs_lease",
        "jobs",
        ["status", "lease_expires_at"],
    )

    op.create_table(
        "job_resumes",
        sa.Column("resume_id", sa.Text, nullable=False),
        sa.Column("job_id", sa.Text, nullable=False),
        sa.Column(
            "wait_generation",
            sa.Integer,
            nullable=False,
        ),
        sa.Column(
            "idempotency_key",
            sa.Text,
            nullable=False,
        ),
        sa.Column("expected_node", sa.Text, nullable=False),
        sa.Column(
            "value_json",
            postgresql.JSONB,
            nullable=False,
        ),
        sa.Column("value_hash", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("resume_id", name="pk_job_resumes"),
        sa.UniqueConstraint(
            "job_id",
            "wait_generation",
            name="uq_job_resumes_job_generation",
        ),
        sa.CheckConstraint(
            "status IN ('pending','consumed')",
            name="ck_job_resumes_valid_status",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.job_id"],
            ondelete="CASCADE",
            name="fk_job_resumes_job_id_jobs",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_job_resumes_idempotency_key",
        ),
    )

    op.create_table(
        "job_events",
        sa.Column(
            "event_id",
            sa.BigInteger,
            sa.Identity(),
            nullable=False,
        ),
        sa.Column("job_id", sa.Text, nullable=False),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("actor", sa.Text, nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event_id", name="pk_job_events"),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.job_id"],
            ondelete="CASCADE",
            name="fk_job_events_job_id_jobs",
        ),
    )
    op.create_index(
        "ix_job_events_job_event",
        "job_events",
        ["job_id", "event_id"],
    )

    op.create_table(
        "job_commands",
        sa.Column("command_id", sa.Text, nullable=False),
        sa.Column("job_id", sa.Text, nullable=False),
        sa.Column("command_type", sa.Text, nullable=False),
        sa.Column(
            "idempotency_key",
            sa.Text,
            nullable=False,
        ),
        sa.Column("request_hash", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "command_id",
            name="pk_job_commands",
        ),
        sa.CheckConstraint(
            "command_type IN ('cancel')",
            name="ck_job_commands_valid_type",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.job_id"],
            ondelete="CASCADE",
            name="fk_job_commands_job_id_jobs",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_job_commands_idempotency_key",
        ),
    )
    op.create_index(
        "ix_job_commands_job_command",
        "job_commands",
        ["job_id", "command_id"],
    )

    op.create_table(
        "artifact_versions",
        sa.Column("artifact_id", sa.Text, nullable=False),
        sa.Column("sha256", sa.Text, nullable=False),
        sa.Column("backend", sa.Text, nullable=False),
        sa.Column("job_id", sa.Text, nullable=False),
        sa.Column("run_id", sa.Text, nullable=False),
        sa.Column("layer", sa.Text, nullable=False),
        sa.Column("relative_path", sa.Text, nullable=False),
        sa.Column("media_type", sa.Text, nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("producer_node", sa.Text, nullable=False),
        sa.Column(
            "artifact_created_at",
            sa.Text,
            nullable=False,
        ),
        sa.Column("object_key", sa.Text, nullable=False),
        sa.Column("etag", sa.Text),
        sa.Column("object_version_id", sa.Text),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "artifact_id",
            "sha256",
            "backend",
            name="pk_artifact_versions",
        ),
        sa.CheckConstraint(
            "size_bytes >= 0",
            name="ck_artifact_versions_non_negative_size",
        ),
    )

    op.create_table(
        "artifact_heads",
        sa.Column("artifact_id", sa.Text, nullable=False),
        sa.Column("job_id", sa.Text, nullable=False),
        sa.Column("run_id", sa.Text, nullable=False),
        sa.Column("relative_path", sa.Text, nullable=False),
        sa.Column("current_sha256", sa.Text, nullable=False),
        sa.Column("current_backend", sa.Text, nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "artifact_id",
            name="pk_artifact_heads",
        ),
        sa.ForeignKeyConstraint(
            [
                "artifact_id",
                "current_sha256",
                "current_backend",
            ],
            [
                "artifact_versions.artifact_id",
                "artifact_versions.sha256",
                "artifact_versions.backend",
            ],
            name="fk_artifact_heads_current_version",
        ),
        sa.UniqueConstraint(
            "job_id",
            "relative_path",
            name="uq_artifact_heads_job_path",
        ),
        sa.CheckConstraint(
            "revision >= 1",
            name="ck_artifact_heads_positive_revision",
        ),
    )
    op.create_index(
        "ix_artifact_heads_job_artifact",
        "artifact_heads",
        ["job_id", "artifact_id"],
    )


def downgrade() -> None:
    # 按外键依赖反序删除；DROP TABLE 会级联删除对应索引。
    op.drop_table("artifact_heads")
    op.drop_table("artifact_versions")
    op.drop_table("job_commands")
    op.drop_table("job_events")
    op.drop_table("job_resumes")
    op.drop_table("jobs")
