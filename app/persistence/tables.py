from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": (
        "fk_%(table_name)s_%(column_0_name)s_"
        "%(referred_table_name)s"
    ),
    "pk": "pk_%(table_name)s",
}

metadata = sa.MetaData(
    naming_convention=NAMING_CONVENTION
)


jobs = sa.Table(
    "jobs",
    metadata,
    sa.Column("job_id", sa.Text, primary_key=True),
    sa.Column(
        "idempotency_key",
        sa.Text,
        nullable=False,
        unique=True,
    ),
    sa.Column("request_hash", sa.Text, nullable=False),
    sa.Column("thread_id", sa.Text, nullable=False, unique=True),
    sa.Column("run_id", sa.Text, nullable=False, unique=True),
    sa.Column("run_dir", sa.Text, nullable=False, unique=True),
    sa.Column("request_json", JSONB, nullable=False),
    sa.Column(
        "requirements_json",
        JSONB,
        nullable=False,
    ),
    # 高频 claim 字段同时规范化，避免每次都做复杂 JSON cast。
    sa.Column("required_worker_pool", sa.Text, nullable=False),
    sa.Column("required_profile_id", sa.Text, nullable=False),
    sa.Column("required_policy_hash", sa.Text, nullable=False),
    sa.Column("required_backend", sa.Text, nullable=False),
    sa.Column(
        "min_workspace_free_bytes",
        sa.BigInteger,
        nullable=False,
        server_default="0",
    ),
    sa.Column(
        "min_gpu_count",
        sa.Integer,
        nullable=False,
        server_default="0",
    ),
    sa.Column("required_cuda_major", sa.Integer),
    sa.Column(
        "required_labels_json",
        JSONB,
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    ),
    sa.Column("affinity_host_id", sa.Text),
    sa.Column("workspace_manifest_id", sa.Text, nullable=False),
    sa.Column(
        "workspace_manifest_generation",
        sa.Integer,
        nullable=False,
        server_default="0",
    ),
    sa.Column(
        "workspace_assignment_epoch",
        sa.Integer,
        nullable=False,
        server_default="0",
    ),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("version", sa.Integer, nullable=False, server_default="0"),
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
    sa.Column("worker_session_id", sa.Text),
    sa.Column("worker_host_id", sa.Text),
    sa.Column("workspace_assignment_token", sa.Text),
    sa.Column("claim_token", sa.Text),
    sa.Column("claimed_at", sa.DateTime(timezone=True)),
    sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
    sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
    sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column(
        "interrupt_nodes_json",
        JSONB,
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    ),
    sa.Column(
        "interrupts_json",
        JSONB,
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
    sa.Column("result_json", JSONB),
    sa.Column("error_json", JSONB),
    sa.Column("reconciliation_json", JSONB),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint(
        "status IN ('queued','running','waiting_for_input',"
        "'cancelling','succeeded','failed','cancelled',"
        "'reconciliation_required')",
        name="valid_status",
    ),
)

sa.Index(
    "ix_jobs_claim",
    jobs.c.status,
    jobs.c.cancel_requested,
    jobs.c.available_at,
    jobs.c.created_at,
)
sa.Index(
    "ix_jobs_lease",
    jobs.c.status,
    jobs.c.lease_expires_at,
)


job_resumes = sa.Table(
    "job_resumes",
    metadata,
    sa.Column("resume_id", sa.Text, primary_key=True),
    sa.Column(
        "job_id",
        sa.Text,
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("wait_generation", sa.Integer, nullable=False),
    sa.Column("idempotency_key", sa.Text, nullable=False, unique=True),
    sa.Column("expected_node", sa.Text, nullable=False),
    sa.Column("value_json", JSONB, nullable=False),
    sa.Column("value_hash", sa.Text, nullable=False),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("consumed_at", sa.DateTime(timezone=True)),
    sa.UniqueConstraint(
        "job_id",
        "wait_generation",
        name="uq_job_resumes_job_generation",
    ),
    sa.CheckConstraint(
        "status IN ('pending','consumed')",
        name="valid_status",
    ),
)


job_events = sa.Table(
    "job_events",
    metadata,
    sa.Column(
        "event_id",
        sa.BigInteger,
        sa.Identity(),
        primary_key=True,
    ),
    sa.Column(
        "job_id",
        sa.Text,
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("event_type", sa.Text, nullable=False),
    sa.Column("actor", sa.Text, nullable=False),
    sa.Column("payload_json", JSONB, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)
sa.Index(
    "ix_job_events_job_event",
    job_events.c.job_id,
    job_events.c.event_id,
)


job_commands = sa.Table(
    "job_commands",
    metadata,
    sa.Column("command_id", sa.Text, primary_key=True),
    sa.Column(
        "job_id",
        sa.Text,
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("command_type", sa.Text, nullable=False),
    sa.Column("idempotency_key", sa.Text, nullable=False, unique=True),
    sa.Column("request_hash", sa.Text, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint(
        "command_type IN ('cancel')",
        name="valid_type",
    ),
)
sa.Index(
    "ix_job_commands_job_command",
    job_commands.c.job_id,
    job_commands.c.command_id,
)


artifact_versions = sa.Table(
    "artifact_versions",
    metadata,
    sa.Column("artifact_id", sa.Text, primary_key=True),
    sa.Column("sha256", sa.Text, primary_key=True),
    sa.Column("backend", sa.Text, primary_key=True),
    sa.Column("job_id", sa.Text, nullable=False),
    sa.Column("run_id", sa.Text, nullable=False),
    sa.Column("layer", sa.Text, nullable=False),
    sa.Column("relative_path", sa.Text, nullable=False),
    sa.Column("media_type", sa.Text, nullable=False),
    sa.Column("size_bytes", sa.BigInteger, nullable=False),
    sa.Column("producer_node", sa.Text, nullable=False),
    sa.Column("artifact_created_at", sa.Text, nullable=False),
    sa.Column("object_key", sa.Text, nullable=False),
    sa.Column("etag", sa.Text),
    sa.Column("object_version_id", sa.Text),
    sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint(
        "size_bytes >= 0",
        name="non_negative_size",
    ),
)


artifact_heads = sa.Table(
    "artifact_heads",
    metadata,
    sa.Column("artifact_id", sa.Text, primary_key=True),
    sa.Column("job_id", sa.Text, nullable=False),
    sa.Column("run_id", sa.Text, nullable=False),
    sa.Column("relative_path", sa.Text, nullable=False),
    sa.Column("current_sha256", sa.Text, nullable=False),
    sa.Column("current_backend", sa.Text, nullable=False),
    sa.Column("revision", sa.Integer, nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
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
        name="positive_revision",
    ),
)
sa.Index(
    "ix_artifact_heads_job_artifact",
    artifact_heads.c.job_id,
    artifact_heads.c.artifact_id,
)


worker_sessions = sa.Table(
    "worker_sessions",
    metadata,
    sa.Column("worker_session_id", sa.Text, primary_key=True),
    sa.Column("worker_id", sa.Text, nullable=False),
    sa.Column("host_id", sa.Text, nullable=False),
    sa.Column("worker_pool", sa.Text, nullable=False),
    sa.Column("workspace_root", sa.Text, nullable=False),
    sa.Column("capabilities_json", JSONB, nullable=False),
    sa.Column("profile_ids_json", JSONB, nullable=False),
    sa.Column("profile_hashes_json", JSONB, nullable=False),
    sa.Column("backends_json", JSONB, nullable=False),
    sa.Column("labels_json", JSONB, nullable=False),
    sa.Column("workspace_free_bytes", sa.BigInteger, nullable=False),
    sa.Column("gpu_count", sa.Integer, nullable=False),
    sa.Column("cuda_major", sa.Integer),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint(
        "status IN ('active','draining','offline')",
        name="valid_status",
    ),
)

sa.Index(
    "ix_worker_sessions_schedulable",
    worker_sessions.c.status,
    worker_sessions.c.worker_pool,
    worker_sessions.c.lease_expires_at,
)


workspace_manifests = sa.Table(
    "workspace_manifests",
    metadata,
    sa.Column("manifest_id", sa.Text, primary_key=True),
    sa.Column("manifest_hash", sa.Text, nullable=False, unique=True),
    sa.Column("job_id", sa.Text, nullable=False),
    sa.Column("run_id", sa.Text, nullable=False),
    sa.Column("generation", sa.Integer, nullable=False),
    sa.Column("parent_manifest_id", sa.Text),
    sa.Column("portable", sa.Boolean, nullable=False),
    sa.Column("source_host_id", sa.Text, nullable=False),
    sa.Column("source_worker_session_id", sa.Text),
    sa.Column("manifest_json", JSONB, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint(
        "job_id",
        "generation",
        name="uq_workspace_manifest_job_generation",
    ),
    sa.CheckConstraint(
        "generation >= 0",
        name="non_negative_generation",
    ),
)

sa.Index(
    "ix_workspace_manifests_job_generation",
    workspace_manifests.c.job_id,
    workspace_manifests.c.generation,
)


workspace_assignments = sa.Table(
    "workspace_assignments",
    metadata,
    sa.Column("assignment_id", sa.Text, primary_key=True),
    sa.Column(
        "job_id",
        sa.Text,
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    ),
    # run_id 是稳定的业务运行标识；job_id 是队列调度标识，二者不能混用。
    sa.Column("run_id", sa.Text, nullable=False),
    sa.Column("assignment_epoch", sa.Integer, nullable=False),
    sa.Column("assignment_token", sa.Text, nullable=False, unique=True),
    sa.Column("manifest_id", sa.Text, nullable=False),
    sa.Column("manifest_hash", sa.Text, nullable=False),
    sa.Column("manifest_generation", sa.Integer, nullable=False),
    sa.Column("worker_session_id", sa.Text, nullable=False),
    sa.Column("host_id", sa.Text, nullable=False),
    sa.Column("workspace_root", sa.Text, nullable=False),
    sa.Column("run_dir", sa.Text, nullable=False),
    sa.Column("repo_path", sa.Text, nullable=False),
    sa.Column("paper_path", sa.Text, nullable=False),
    sa.Column("log_path", sa.Text),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("error_code", sa.Text),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint(
        "job_id",
        "assignment_epoch",
        name="uq_workspace_assignment_job_epoch",
    ),
    sa.CheckConstraint(
        "status IN ('materializing','ready','released','failed',"
        "'garbage_collected')",
        name="valid_status",
    ),
)

sa.Index(
    "ix_workspace_assignments_job_epoch",
    workspace_assignments.c.job_id,
    workspace_assignments.c.assignment_epoch,
)


# Phase 29：受控资源获取与供应链安全。
# claim_token 只保存 SHA-256 hash（claim_token_hash），原始 token 永不入库。
# 表结构由 alembic migration 20260803_0003 管理，这里注册进 metadata
# 以便 autogenerate 与一致性检查。
resources = sa.Table(
    "resources",
    metadata,
    sa.Column("resource_id", sa.Text, primary_key=True),
    sa.Column(
        "idempotency_key",
        sa.Text,
        nullable=False,
        unique=True,
    ),
    sa.Column("request_sha256", sa.Text, nullable=False),
    sa.Column("request_json", JSONB, nullable=False),
    sa.Column("approval_json", JSONB, nullable=True),
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
    sa.Column("worker_id", sa.Text),
    # 原始 claim_token 永不入库；只保存 SHA-256 hash。
    sa.Column("claim_token_hash", sa.Text),
    sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
    sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
    sa.Column("manifest_json", JSONB),
    sa.Column("error_json", JSONB),
    sa.Column(
        "available_at",
        sa.DateTime(timezone=True),
        nullable=False,
    ),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint(
        "status IN ('awaiting_approval','queued','fetching',"
        "'validating','published','rejected','cancelled',"
        "'failed_retryable','failed_terminal',"
        "'reconciliation_required')",
        name="valid_status",
    ),
)

sa.Index(
    "ix_resources_claim",
    resources.c.status,
    resources.c.available_at,
    resources.c.created_at,
)
sa.Index(
    "ix_resources_lease",
    resources.c.status,
    resources.c.lease_expires_at,
)


resource_events = sa.Table(
    "resource_events",
    metadata,
    sa.Column(
        "event_id",
        sa.BigInteger,
        sa.Identity(),
        primary_key=True,
    ),
    sa.Column(
        "resource_id",
        sa.Text,
        sa.ForeignKey(
            "resources.resource_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    ),
    sa.Column("event_type", sa.Text, nullable=False),
    sa.Column("actor", sa.Text, nullable=False),
    sa.Column("payload_json", JSONB, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)
sa.Index(
    "ix_resource_events_resource_event",
    resource_events.c.resource_id,
    resource_events.c.event_id,
)
