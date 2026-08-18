"""worker capability and workspace control plane

Revision ID: 20260731_0002
Revises: 0001
Create Date: 2026-07-31 00:02:00.000000

Phase 26: worker_sessions / workspace_manifests / workspace_assignments
以及 jobs 表上的调度与 workspace pointer 列。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260731_0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # 先建 manifest 表，因为 jobs.workspace_manifest_id 最终引用它。
    op.create_table(
        "workspace_manifests",
        sa.Column("manifest_id", sa.Text(), nullable=False),
        sa.Column("manifest_hash", sa.Text(), nullable=False),
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("parent_manifest_id", sa.Text(), nullable=True),
        sa.Column("portable", sa.Boolean(), nullable=False),
        sa.Column("source_host_id", sa.Text(), nullable=False),
        sa.Column("source_worker_session_id", sa.Text(), nullable=True),
        sa.Column(
            "manifest_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "generation >= 0",
            name="ck_workspace_manifests_non_negative_generation",
        ),
        sa.PrimaryKeyConstraint(
            "manifest_id",
            name="pk_workspace_manifests",
        ),
        sa.UniqueConstraint(
            "manifest_hash",
            name="uq_workspace_manifests_manifest_hash",
        ),
        sa.UniqueConstraint(
            "job_id",
            "generation",
            name="uq_workspace_manifest_job_generation",
        ),
    )

    op.create_table(
        "worker_sessions",
        sa.Column("worker_session_id", sa.Text(), nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=False),
        sa.Column("host_id", sa.Text(), nullable=False),
        sa.Column("worker_pool", sa.Text(), nullable=False),
        sa.Column("workspace_root", sa.Text(), nullable=False),
        sa.Column("capabilities_json", postgresql.JSONB(), nullable=False),
        sa.Column("profile_ids_json", postgresql.JSONB(), nullable=False),
        sa.Column("profile_hashes_json", postgresql.JSONB(), nullable=False),
        sa.Column("backends_json", postgresql.JSONB(), nullable=False),
        sa.Column("labels_json", postgresql.JSONB(), nullable=False),
        sa.Column("workspace_free_bytes", sa.BigInteger(), nullable=False),
        sa.Column("gpu_count", sa.Integer(), nullable=False),
        sa.Column("cuda_major", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('active','draining','offline')",
            name="ck_worker_sessions_valid_status",
        ),
        sa.PrimaryKeyConstraint(
            "worker_session_id",
            name="pk_worker_sessions",
        ),
    )

    # 先用 nullable 列回填已有 Job，再收紧 NOT NULL。
    op.add_column(
        "jobs",
        sa.Column("requirements_json", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("required_worker_pool", sa.Text(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("required_profile_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("required_policy_hash", sa.Text(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("required_backend", sa.Text(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "min_workspace_free_bytes",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "min_gpu_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("required_cuda_major", sa.Integer(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "required_labels_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("affinity_host_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("workspace_manifest_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "workspace_manifest_generation",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "workspace_assignment_epoch",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column("jobs", sa.Column("worker_session_id", sa.Text()))
    op.add_column("jobs", sa.Column("worker_host_id", sa.Text()))
    op.add_column(
        "jobs",
        sa.Column("workspace_assignment_token", sa.Text()),
    )

    # 已有 Job 没有可验证 workspace manifest，绝不能伪造成 portable。
    # 生产 cutover 前应先完成旧 active Job；这里只给 terminal 历史行回填 legacy 标记。
    op.execute(
        """
        UPDATE jobs
        SET requirements_json = jsonb_build_object(
                'worker_pool', 'legacy',
                'execution_profile_id', request_json->>'execution_profile_id',
                'execution_backend', 'local',
                'min_workspace_free_bytes', 0,
                'min_gpu_count', 0,
                'cuda_major', NULL,
                'required_labels', jsonb_build_array('legacy-host-only')
            ),
            required_worker_pool = 'legacy',
            required_profile_id = request_json->>'execution_profile_id',
            required_policy_hash = repeat('0', 64),
            required_backend = 'local'
        """
    )

    # workspace_manifest_id 无法安全伪造；存在旧行时先阻断 migration。
    connection = op.get_bind()
    legacy_count = connection.execute(
        sa.text("SELECT count(*) FROM jobs")
    ).scalar_one()
    if legacy_count:
        raise RuntimeError(
            "Phase 26 migration 检测到旧 Job；请先执行显式 legacy backfill 工具"
        )

    op.alter_column("jobs", "requirements_json", nullable=False)
    op.alter_column("jobs", "required_worker_pool", nullable=False)
    op.alter_column("jobs", "required_profile_id", nullable=False)
    op.alter_column("jobs", "required_policy_hash", nullable=False)
    op.alter_column("jobs", "required_backend", nullable=False)
    op.alter_column("jobs", "workspace_manifest_id", nullable=False)

    op.create_foreign_key(
        "fk_jobs_workspace_manifest_id_workspace_manifests",
        "jobs",
        "workspace_manifests",
        ["workspace_manifest_id"],
        ["manifest_id"],
    )

    op.create_table(
        "workspace_assignments",
        sa.Column("assignment_id", sa.Text(), nullable=False),
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("assignment_epoch", sa.Integer(), nullable=False),
        sa.Column("assignment_token", sa.Text(), nullable=False),
        sa.Column("manifest_id", sa.Text(), nullable=False),
        sa.Column("manifest_hash", sa.Text(), nullable=False),
        sa.Column("manifest_generation", sa.Integer(), nullable=False),
        sa.Column("worker_session_id", sa.Text(), nullable=False),
        sa.Column("host_id", sa.Text(), nullable=False),
        sa.Column("workspace_root", sa.Text(), nullable=False),
        sa.Column("run_dir", sa.Text(), nullable=False),
        sa.Column("repo_path", sa.Text(), nullable=False),
        sa.Column("paper_path", sa.Text(), nullable=False),
        sa.Column("log_path", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('materializing','ready','released','failed',"
            "'garbage_collected')",
            name="ck_workspace_assignments_valid_status",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.job_id"],
            ondelete="CASCADE",
            name="fk_workspace_assignments_job_id_jobs",
        ),
        sa.ForeignKeyConstraint(
            ["manifest_id"],
            ["workspace_manifests.manifest_id"],
            name="fk_workspace_assignments_manifest_id_workspace_manifests",
        ),
        sa.PrimaryKeyConstraint(
            "assignment_id",
            name="pk_workspace_assignments",
        ),
        sa.UniqueConstraint(
            "assignment_token",
            name="uq_workspace_assignments_assignment_token",
        ),
        sa.UniqueConstraint(
            "job_id",
            "assignment_epoch",
            name="uq_workspace_assignment_job_epoch",
        ),
    )


def downgrade() -> None:
    raise RuntimeError(
        "Phase 26 downgrade 可能丢失 workspace fencing 历史；"
        "请从数据库备份恢复，不提供自动 downgrade"
    )
