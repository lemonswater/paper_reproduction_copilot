from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    """
    把常见环境变量字符串转换为 bool。

    接受：
    - true / false
    - 1 / 0
    - yes / no
    - on / off

    遇到无法识别的值时直接报错，避免配置悄悄失效。
    """
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"无效的布尔环境变量：{name}={raw_value!r}")


def _env_path(name: str) -> Path | None:
    raw_value = os.getenv(name, "").strip()
    return Path(raw_value) if raw_value else None


def _env_paths(
    name: str,
    default: str,
) -> tuple[Path, ...]:
    """解析由 os.pathsep 分隔的路径列表。

    Linux 的 os.pathsep 是 ``:``。这里不使用逗号，避免路径名中
    偶然出现逗号时产生歧义。空项会被忽略。
    """

    raw_value = os.getenv(name, default)
    values = tuple(
        Path(item.strip())
        for item in raw_value.split(os.pathsep)
        if item.strip()
    )
    if not values:
        raise ValueError(f"{name} 至少需要一个目录")
    return values


def _env_csv_values(
    name: str,
    default: str,
) -> frozenset[str]:
    """解析逗号分隔的稳定去重值；空字符串表示空集合。"""

    raw_value = os.getenv(name, default)
    return frozenset(
        item.strip()
        for item in raw_value.split(",")
        if item.strip()
    )


def _uses_mimo_provider() -> bool:
    """根据显式 Provider 地址或模型名选择 MiMo 兼容默认值。"""
    base_url = os.getenv("OPENAI_BASE_URL", "").strip().lower()
    model = os.getenv("OPENAI_MODEL", "mimo-v2.5-pro").strip().lower()
    return "xiaomimimo.com" in base_url or model.startswith("mimo")


_USES_MIMO_PROVIDER = _uses_mimo_provider()

# 所有运行时状态（SQLite 与模块状态目录）统一收敛到 state/ 下，
# 可通过 STATE_ROOT 环境变量整体重定位。
_state_root = Path(os.getenv("STATE_ROOT", "state"))


@dataclass
class Settings:
    # Phase 41：Settings 只保存 Vault 路径和 Secret 名称。
    # 不读取 OPENAI_API_KEY、EMBEDDING_API_KEY 等明文环境变量。
    secret_master_key_path: Path = Path(
        os.getenv(
            "SECRET_MASTER_KEY_PATH",
            str(_state_root / "secrets/master.key"),
        )
    )
    secret_vault_db_path: Path = Path(
        os.getenv(
            "SECRET_VAULT_DB_PATH",
            str(_state_root / "secrets/vault.sqlite"),
        )
    )

    openai_api_key_secret_name: str = os.getenv(
        "OPENAI_API_KEY_SECRET_NAME",
        "OPENAI_API_KEY",
    )
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
    openai_model: str = os.getenv("OPENAI_MODEL", "deepseek-v4-flash")
    # 未配置时仍回退到旧模型，使 off/shadow 不改变当前行为。
    openai_economy_model: str = os.getenv(
        "OPENAI_ECONOMY_MODEL",
        os.getenv("OPENAI_MODEL", "deepseek-v4-flash"),
    )
    openai_strong_model: str = os.getenv(
        "OPENAI_STRONG_MODEL",
        os.getenv("OPENAI_MODEL", "deepseek-v4-flash"),
    )
    # 显式给复杂结构化输出留出空间，避免兼容 Provider 使用过小默认值。
    openai_max_output_tokens: int = int(
        os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "32768")
    )
    # MiMo 默认开启深度思考；本项目默认关闭以保留结构化可见输出预算。
    # 其他 Provider 不注入该扩展参数。
    openai_thinking_mode: str | None = (
        os.getenv(
            "OPENAI_THINKING_MODE",
            "disabled" if _USES_MIMO_PROVIDER else "",
        ).strip().lower()
        or None
    )
    embedding_api_key_secret_name: str = os.getenv(
        "EMBEDDING_API_KEY_SECRET_NAME",
        "EMBEDDING_API_KEY",
    )
    embedding_base_url: str | None = os.getenv("EMBEDDING_BASE_URL")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "qwen-text-embedding-v4")
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
    runs_dir: Path = Path(os.getenv("RUNS_DIR", "runs"))
    allowed_root: Path = Path(
        os.getenv("ALLOWED_ROOT", "/data/tianshaoqi24")
    )
    checkpoint_db_path: Path = Path(
        os.getenv("CHECKPOINT_DB_PATH", str(_state_root / "checkpoints/langgraph.sqlite"))
    )
    max_steps: int = int(os.getenv("MAX_STEPS", "20"))

    execution_profiles_path: Path = Path(
        os.getenv(
            "EXECUTION_PROFILES_PATH",
            "config/execution_profiles.local.json"
        )
    )
    default_execution_profile: str = os.getenv(
        "DEFAULT_EXECUTION_PROFILE",
        "local",
    )

    smoke_test_timeout_seconds: int = int(
        os.getenv("SMOKE_TEST_TIMEOUT_SECONDS", "60")
    )

    max_repair_attempts: int = int(
        os.getenv("MAX_REPAIR_ATTEMPTS", "1")
    )

    # MiMo 官方兼容接口提供 json_object，而非 JSON Schema strict。
    # 其他 Provider 继续优先使用服务端原生 JSON Schema。
    structured_output_method: str = os.getenv(
        "STRUCTURED_OUTPUT_METHOD",
        "json_mode" if _USES_MIMO_PROVIDER else "json_schema",
    )

    # strict=True 时，服务端如果支持，会在生成阶段约束 JSON Schema。
    structured_output_strict: bool = _env_bool(
        "STRUCTURED_OUTPUT_STRICT",
        not _USES_MIMO_PROVIDER,
    )

    # 这里表示“第一次失败后额外重试几次”。
    # 设置为 2 时，总调用次数最多为 3 次。
    structured_output_max_retries: int = int(
        os.getenv("STRUCTURED_OUTPUT_MAX_RETRIES", "2")
    )

    # attempt artifact 只保存原始输出预览，避免文件无限增大。
    structured_output_raw_preview_chars: int = int(
        os.getenv("STRUCTURED_OUTPUT_RAW_PREVIEW_CHARS", "2000")
    )

    # Provider 瞬时传输错误额外重试次数，不包含第一次调用。
    provider_max_retries: int = int(
        os.getenv("PROVIDER_MAX_RETRIES", "2")
    )

    # 指数退避基础秒数：0.5、1.0、2.0 ...
    provider_retry_base_seconds: float = float(
        os.getenv("PROVIDER_RETRY_BASE_SECONDS", "0.5")
    )

    # 文件修复默认关闭。先通过单测和演示仓库验证，再在真实仓库中开启。
    enable_file_repair: bool = _env_bool(
        "ENABLE_FILE_REPAIR",
        False,
    )

    # 一次 proposal 最多修改两个文件，避免模型把重构包装成 bug fix。
    max_patch_files: int = int(
        os.getenv("MAX_PATCH_FILES", "2")
    )

    # 所有文件加起来最多执行四个精确文本替换。
    max_patch_replacements: int = int(
        os.getenv("MAX_PATCH_REPLACEMENTS", "4")
    )

    # 按 diff opcode 统计修改规模，超过后降级为人工处理。
    max_patch_changed_lines: int = int(
        os.getenv("MAX_PATCH_CHANGED_LINES", "80")
    )

    # 不把超大源码文件完整塞给模型，也不允许第一版 patch 它们。
    max_patch_file_bytes: int = int(
        os.getenv("MAX_PATCH_FILE_BYTES", str(512 * 1024))
    )

    # 隔离 worktree 中单个验证动作的超时时间。
    patch_verify_timeout_seconds: int = int(
        os.getenv("PATCH_VERIFY_TIMEOUT_SECONDS", "120")
    )

    # 第一版每个 graph run 最多尝试一次 file-level repair。
    max_file_repair_attempts: int = int(
        os.getenv("MAX_FILE_REPAIR_ATTEMPTS", "1")
    )

    patch_coordination_dir: Path = Path(
        os.getenv("PATCH_COORDINATION_DIR", "runs/.coordination")
    )

    patch_repo_lock_timeout_seconds: float = float(
        os.getenv("PATCH_REPO_LOCK_TIMEOUT_SECONDS", "2")
    )

    process_poll_interval_seconds: float = float(
        os.getenv("PROCESS_POLL_INTERVAL_SECONDS", "0.2")
    )

    process_terminate_grace_seconds: float = float(
        os.getenv("PROCESS_TERMINATE_GRACE_SECONDS", "5")
    )

    process_max_log_bytes_per_stream: int = int(
        os.getenv(
            "PROCESS_MAX_LOG_BYTES_PER_STREAM",
            str(16 * 1024 * 1024),
        )
    )

    process_max_preview_bytes: int = int(
        os.getenv(
            "PROCESS_MAX_PREVIEW_BYTES",
            str(64 * 1024),
        )
    )

    # 单个章节 chunk 允许交给模型的目标字符数。
    # chunker 不会从 block 中间切断，因此实际长度可能略大。
    paper_section_chunk_chars: int = int(
        os.getenv(
            "PAPER_SECTION_CHUNK_CHARS",
            "12000",
        )
    )

    # 防止异常 PDF 产生过多章节，导致一次运行发起无限 LLM 请求。
    paper_max_section_llm_calls: int = int(
        os.getenv(
            "PAPER_MAX_SECTION_LLM_CALLS",
            "12",
        )
    )

    # 分类代码映射先做确定性去重，再受总预算和分类预算双重限制。
    mapping_max_targets: int = int(
        os.getenv("MAPPING_MAX_TARGETS", "12")
    )
    mapping_max_core_method_targets: int = int(
        os.getenv(
            "MAPPING_MAX_CORE_METHOD_TARGETS",
            "6",
        )
    )
    mapping_max_data_pipeline_targets: int = int(
        os.getenv(
            "MAPPING_MAX_DATA_PIPELINE_TARGETS",
            "2",
        )
    )
    mapping_max_training_config_targets: int = int(
        os.getenv(
            "MAPPING_MAX_TRAINING_CONFIG_TARGETS",
            "1",
        )
    )
    mapping_max_evaluation_metric_targets: int = int(
        os.getenv(
            "MAPPING_MAX_EVALUATION_METRIC_TARGETS",
            "2",
        )
    )
    mapping_max_ablation_switch_targets: int = int(
        os.getenv(
            "MAPPING_MAX_ABLATION_SWITCH_TARGETS",
            "1",
        )
    )
    mapping_aliases_path: Path | None = _env_path(
        "MAPPING_ALIASES_PATH"
    )

    # 页面提取字符数低于该值时记录 EMPTY_TEXT/OCR_REQUIRED warning。
    paper_min_extracted_chars: int = 20

    # parser 规则变化时更新此版本，使旧缓存自然失效。
    paper_parser_version: str = "phase19-v1"

    # section prompt 或 schema 变化时更新此版本。
    paper_extraction_version: str = "phase18-v2"

    # RepositoryIndex 结构发生变化时更新。
    retrieval_index_version: str = os.getenv(
        "RETRIEVAL_INDEX_VERSION",
        "phase20-v3",
    )

    # 默认关闭：开启后会构造 semantic chunks。
    enable_dense_retrieval: bool = _env_bool(
        "ENABLE_DENSE_RETRIEVAL",
        False,
    )

    # required=true 时，Dense 失败不允许静默降级。
    dense_retrieval_required: bool = _env_bool(
        "DENSE_RETRIEVAL_REQUIRED",
        False,
    )

    # 远程源码上传必须单独明确授权。
    allow_code_embedding_upload: bool = _env_bool(
        "ALLOW_CODE_EMBEDDING_UPLOAD",
        False,
    )

    embedding_timeout_seconds: float = float(
        os.getenv(
            "EMBEDDING_TIMEOUT_SECONDS",
            "60",
        )
    )

    embedding_max_retries: int = int(
        os.getenv(
            "EMBEDDING_MAX_RETRIES",
            "2",
        )
    )

    embedding_batch_size: int = int(
        os.getenv(
            "EMBEDDING_BATCH_SIZE",
            "32",
        )
    )

    embedding_cache_db_path: Path = Path(
        os.getenv(
            "EMBEDDING_CACHE_DB_PATH",
            str(_state_root / "cache/embeddings.sqlite"),
        )
    )

    embedding_cache_version: str = os.getenv(
        "EMBEDDING_CACHE_VERSION",
        "phase21-v1",
    )

    semantic_chunk_policy_version: str = os.getenv(
        "SEMANTIC_CHUNK_POLICY_VERSION",
        "phase21-v3",
    )

    semantic_chunk_max_lines: int = int(
        os.getenv(
            "SEMANTIC_CHUNK_MAX_LINES",
            "80",
        )
    )

    semantic_chunk_overlap_lines: int = int(
        os.getenv(
            "SEMANTIC_CHUNK_OVERLAP_LINES",
            "16",
        )
    )

    semantic_max_chunks: int = int(
        os.getenv(
            "SEMANTIC_MAX_CHUNKS",
            "5000",
        )
    )

    semantic_query_max_chars: int = int(
        os.getenv(
            "SEMANTIC_QUERY_MAX_CHARS",
            "6000",
        )
    )

    dense_min_similarity: float = float(
        os.getenv(
            "DENSE_MIN_SIMILARITY",
            "0.20",
        )
    )

    dense_max_hits: int = int(
        os.getenv(
            "DENSE_MAX_HITS",
            "40",
        )
    )

    retrieval_max_file_bytes: int = int(
        os.getenv(
            "RETRIEVAL_MAX_FILE_BYTES",
            str(1024 * 1024),
        )
    )

    retrieval_top_k: int = int(
        os.getenv("RETRIEVAL_TOP_K", "8")
    )

    retrieval_context_lines: int = int(
        os.getenv(
            "RETRIEVAL_CONTEXT_LINES",
            "20",
        )
    )

    retrieval_max_span_lines: int = int(
        os.getenv(
            "RETRIEVAL_MAX_SPAN_LINES",
            "120",
        )
    )

    retrieval_rrf_k: int = int(
        os.getenv("RETRIEVAL_RRF_K", "60")
    )

    # Phase 47：默认 off，确保升级后检索结果完全兼容。
    retrieval_policy_mode: str = os.getenv(
        "RETRIEVAL_POLICY_MODE",
        "off",
    ).strip().lower()

    # Policy 是版本化本地配置，不由 LLM、Chat 或 Graph State 覆盖。
    retrieval_policy_path: Path = Path(
        os.getenv(
            "RETRIEVAL_POLICY_PATH",
            "config/retrieval_policy.json",
        )
    )

    # Job Runtime 与 LangGraph checkpoint 使用不同 SQLite 文件。
    # checkpoint 保存业务状态；job DB 保存排队和 worker ownership。
    job_db_path: Path = Path(
        os.getenv(
            "JOB_DB_PATH",
            str(_state_root / "jobs/runtime.sqlite"),
        )
    )

    # worker 没有续租超过该时间后，Job 才进入 reconcile。
    # 它必须明显大于 heartbeat 间隔。
    job_lease_seconds: float = float(
        os.getenv("JOB_LEASE_SECONDS", "30")
    )

    # heartbeat 在独立线程中运行，因此 Graph 卡在 LLM 或 subprocess 时
    # 仍然可以续租。
    job_heartbeat_seconds: float = float(
        os.getenv("JOB_HEARTBEAT_SECONDS", "5")
    )

    # 没有任务时 worker 的轮询间隔。
    job_poll_seconds: float = float(
        os.getenv("JOB_POLL_SECONDS", "1")
    )

    # 这里只限制 worker claim 次数，不替代节点内部 provider retry。
    job_max_attempts: int = int(
        os.getenv("JOB_MAX_ATTEMPTS", "3")
    )

    # show-job 只保存 bounded interrupt preview；完整大对象仍在 checkpoint
    # 或 run Artifact 中。
    job_interrupt_preview_chars: int = int(
        os.getenv(
            "JOB_INTERRUPT_PREVIEW_CHARS",
            "12000",
        )
    )

    # API 默认只监听本机。监听非 loopback 地址时必须配置 token。
    api_host: str = os.getenv(
        "AGENT_API_HOST",
        "127.0.0.1",
    )

    api_port: int = int(
        os.getenv(
            "AGENT_API_PORT",
            "8000",
        )
    )

    # Phase 41：API Token 由 SecretService 按名称解析。
    # 这里不能重新读取 AGENT_API_TOKEN 或 DATABASE_URL 明文。
    api_token_secret_name: str = os.getenv(
        "AGENT_API_TOKEN_SECRET_NAME",
        "AGENT_API_TOKEN",
    )

    # SSE 第一版轮询 SQLite。后续可由 EventBus 替换内部实现。
    api_event_poll_seconds: float = float(
        os.getenv(
            "AGENT_API_EVENT_POLL_SECONDS",
            "0.5",
        )
    )

    # 长时间没有业务事件时发送 SSE comment，防止代理关闭空闲连接。
    api_sse_heartbeat_seconds: float = float(
        os.getenv(
            "AGENT_API_SSE_HEARTBEAT_SECONDS",
            "15",
        )
    )

    api_max_page_size: int = int(
        os.getenv(
            "AGENT_API_MAX_PAGE_SIZE",
            "100",
        )
    )

    api_max_log_bytes: int = int(
        os.getenv(
            "AGENT_API_MAX_LOG_BYTES",
            str(256 * 1024),
        )
    )

        # Phase 24 只实现 sqlite JobStore，但业务层不再依赖具体类。
    job_store_backend: str = os.getenv(
        "JOB_STORE_BACKEND",
        "sqlite",
    )

    # local 用于离线测试和单机回退；s3 同时兼容 AWS S3 与 MinIO。
    artifact_blob_backend: str = os.getenv(
        "ARTIFACT_BLOB_BACKEND",
        "local",
    )

    artifact_catalog_db_path: Path = Path(
        os.getenv(
            "ARTIFACT_CATALOG_DB_PATH",
            str(_state_root / "storage/artifacts.sqlite"),
        )
    )

    artifact_local_store_dir: Path = Path(
        os.getenv(
            "ARTIFACT_LOCAL_STORE_DIR",
            str(_state_root / "storage/artifacts"),
        )
    )

    artifact_s3_endpoint_url: str | None = os.getenv(
        "ARTIFACT_S3_ENDPOINT_URL"
    )

    artifact_s3_bucket: str = os.getenv(
        "ARTIFACT_S3_BUCKET",
        "paper-reproduction-artifacts",
    )

    artifact_s3_region: str = os.getenv(
        "ARTIFACT_S3_REGION",
        "us-east-1",
    )

    artifact_s3_prefix: str = os.getenv(
        "ARTIFACT_S3_PREFIX",
        "copilot",
    ).strip("/")

    artifact_s3_force_path_style: bool = _env_bool(
        "ARTIFACT_S3_FORCE_PATH_STYLE",
        True,
    )

    # 生产 bucket 应由 IaC 创建；只在本机 MinIO 手工验收时开启。
    artifact_s3_auto_create_bucket: bool = _env_bool(
        "ARTIFACT_S3_AUTO_CREATE_BUCKET",
        False,
    )

    artifact_s3_connect_timeout_seconds: float = float(
        os.getenv(
            "ARTIFACT_S3_CONNECT_TIMEOUT_SECONDS",
            "5",
        )
    )

    artifact_s3_read_timeout_seconds: float = float(
        os.getenv(
            "ARTIFACT_S3_READ_TIMEOUT_SECONDS",
            "60",
        )
    )

    artifact_s3_max_attempts: int = int(
        os.getenv(
            "ARTIFACT_S3_MAX_ATTEMPTS",
            "3",
        )
    )

    artifact_stream_chunk_bytes: int = int(
        os.getenv(
            "ARTIFACT_STREAM_CHUNK_BYTES",
            str(1024 * 1024),
        )
    )

    # Phase 34：预览只读取有界文本，不允许大 Artifact 全量进内存。
    artifact_preview_max_bytes: int = int(
        os.getenv(
            "ARTIFACT_PREVIEW_MAX_BYTES",
            str(256 * 1024),
        )
    )

    # 导出 staging 位于项目目录内，不依赖系统 /tmp。
    job_export_allowed_root: Path = Path(
        os.getenv(
            "JOB_EXPORT_ALLOWED_ROOT",
            str(Path(__file__).resolve().parents[1]),
        )
    )

    job_export_staging_root: Path = Path(
        os.getenv(
            "JOB_EXPORT_STAGING_ROOT",
            "exports/.staging",
        )
    )

    job_export_max_artifacts: int = int(
        os.getenv(
            "JOB_EXPORT_MAX_ARTIFACTS",
            "500",
        )
    )

    job_export_max_uncompressed_bytes: int = int(
        os.getenv(
            "JOB_EXPORT_MAX_UNCOMPRESSED_BYTES",
            str(1024 * 1024 * 1024),
        )
    )

    job_export_max_archive_bytes: int = int(
        os.getenv(
            "JOB_EXPORT_MAX_ARCHIVE_BYTES",
            str(512 * 1024 * 1024),
        )
    )

    job_export_staging_ttl_seconds: int = int(
        os.getenv(
            "JOB_EXPORT_STAGING_TTL_SECONDS",
            "3600",
        )
    )

    # Phase 41：DATABASE_URL 由 SecretService 按名称解析。
    database_url_secret_name: str = os.getenv(
        "DATABASE_URL_SECRET_NAME",
        "DATABASE_URL",
    )

    database_pool_size: int = int(
        os.getenv("DATABASE_POOL_SIZE", "5")
    )
    database_max_overflow: int = int(
        os.getenv("DATABASE_MAX_OVERFLOW", "5")
    )
    database_pool_timeout_seconds: float = float(
        os.getenv(
            "DATABASE_POOL_TIMEOUT_SECONDS",
            "10",
        )
    )
    database_statement_timeout_ms: int = int(
        os.getenv(
            "DATABASE_STATEMENT_TIMEOUT_MS",
            "30000",
        )
    )
    database_lock_timeout_ms: int = int(
        os.getenv(
            "DATABASE_LOCK_TIMEOUT_MS",
            "5000",
        )
    )

    checkpoint_backend: str = os.getenv(
        "CHECKPOINT_BACKEND",
        "sqlite",
    )
    checkpoint_postgres_pool_min_size: int = int(
        os.getenv(
            "CHECKPOINT_POSTGRES_POOL_MIN_SIZE",
            "1",
        )
    )
    checkpoint_postgres_pool_max_size: int = int(
        os.getenv(
            "CHECKPOINT_POSTGRES_POOL_MAX_SIZE",
            "5",
        )
    )

    # Phase 26 Worker identity / workspace materialization
    # host_id 是运维配置的稳定主机身份，不能由 LLM 或 Job request 指定。
    worker_host_id: str = os.getenv(
        "WORKER_HOST_ID",
        "local-host",
    ).strip()

    worker_pool: str = os.getenv(
        "WORKER_POOL",
        "default",
    ).strip()

    # 每个 Worker 只允许在自己的 root 下创建 job/epoch workspace。
    worker_workspace_root: Path = Path(
        os.getenv(
            "WORKER_WORKSPACE_ROOT",
            "worker_workspaces/local-host",
        )
    )

    worker_capabilities_path: Path = Path(
        os.getenv(
            "WORKER_CAPABILITIES_PATH",
            "config/worker_capabilities.local.json",
        )
    )

    worker_session_lease_seconds: float = float(
        os.getenv("WORKER_SESSION_LEASE_SECONDS", "30")
    )

    worker_session_heartbeat_seconds: float = float(
        os.getenv("WORKER_SESSION_HEARTBEAT_SECONDS", "5")
    )

    # Repo bundle 和临时下载必须放在项目受控目录，不使用 /tmp。
    workspace_staging_root: Path = Path(
        os.getenv(
            "WORKSPACE_STAGING_ROOT",
            "workspace_staging",
        )
    )

    workspace_max_file_bytes: int = int(
        os.getenv(
            "WORKSPACE_MAX_FILE_BYTES",
            str(2 * 1024 * 1024 * 1024),
        )
    )

    workspace_max_manifest_bytes: int = int(
        os.getenv(
            "WORKSPACE_MAX_MANIFEST_BYTES",
            str(4 * 1024 * 1024),
        )
    )

    workspace_max_total_bytes: int = int(
        os.getenv(
            "WORKSPACE_MAX_TOTAL_BYTES",
            str(8 * 1024 * 1024 * 1024),
        )
    )

    workspace_git_timeout_seconds: float = float(
        os.getenv("WORKSPACE_GIT_TIMEOUT_SECONDS", "120")
    )

    workspace_gc_min_age_seconds: float = float(
        os.getenv("WORKSPACE_GC_MIN_AGE_SECONDS", "86400")
    )

    # Phase 27 OCI 容器执行配置。
    # 第一版只支持 rootless Podman CLI。
    container_runtime: str = os.getenv(
        "CONTAINER_RUNTIME", "podman"
    ).strip()

    # 所有容器都带此前缀，reconcile/GC 仍必须同时校验 label。
    container_name_prefix: str = os.getenv(
        "CONTAINER_NAME_PREFIX", "prc"
    ).strip()

    # stop 先给容器正常退出时间，超时后 runtime 才强制终止。
    container_stop_timeout_seconds: float = float(
        os.getenv("CONTAINER_STOP_TIMEOUT_SECONDS", "10")
    )

    # 默认不删除失败容器，先保留 inspect 证据；由受控 GC 处理。
    container_remove_succeeded: bool = (
        os.getenv("CONTAINER_REMOVE_SUCCEEDED", "true").lower()
        == "true"
    )
    container_remove_failed: bool = (
        os.getenv("CONTAINER_REMOVE_FAILED", "false").lower()
        == "true"
    )

    # 真实 runtime 测试默认关闭，避免普通 pytest 操作宿主机容器。
    enable_container_integration_tests: bool = (
        os.getenv("ENABLE_CONTAINER_INTEGRATION_TESTS", "false").lower()
        == "true"
    )

    # Phase 28 Observability
    observability_backend: str = os.getenv(
        "OBSERVABILITY_BACKEND", "in_memory"
    ).strip()
    otlp_http_endpoint: str | None = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    telemetry_environment: str = os.getenv(
        "TELEMETRY_ENVIRONMENT", "development"
    ).strip()
    otel_trace_enabled: bool = _env_bool("OTEL_TRACE_ENABLED", True)
    otel_metric_enabled: bool = _env_bool("OTEL_METRIC_ENABLED", True)
    structured_logging_enabled: bool = _env_bool(
        "STRUCTURED_LOGGING_ENABLED", True
    )
    readiness_timeout_seconds: float = float(
        os.getenv("READINESS_TIMEOUT_SECONDS", "2")
    )
    readiness_cache_ttl_seconds: float = float(
        os.getenv("READINESS_CACHE_TTL_SECONDS", "1")
    )
    readiness_probe_workers: int = int(
        os.getenv("READINESS_PROBE_WORKERS", "4")
    )

    # Phase 29 Controlled Resource Acquisition & Supply Chain Safety
    # 所有 root 必须位于 allowed_root 下；不使用系统 /tmp。
    resource_staging_root: Path = Path(
        os.getenv(
            "RESOURCE_STAGING_ROOT",
            str(_state_root / "resources/.staging"),
        )
    )
    resource_materialized_root: Path = Path(
        os.getenv(
            "RESOURCE_MATERIALIZED_ROOT",
            str(_state_root / "resources/materialized"),
        )
    )
    resource_allowed_hosts: tuple[str, ...] = tuple(
        item.strip().lower()
        for item in os.getenv(
            "RESOURCE_ALLOWED_HOSTS",
            "arxiv.org,export.arxiv.org,github.com,codeload.github.com",
        ).split(",")
        if item.strip()
    )
    resource_max_redirects: int = int(
        os.getenv("RESOURCE_MAX_REDIRECTS", "5")
    )
    resource_connect_timeout_seconds: float = float(
        os.getenv("RESOURCE_CONNECT_TIMEOUT_SECONDS", "10")
    )
    resource_read_timeout_seconds: float = float(
        os.getenv("RESOURCE_READ_TIMEOUT_SECONDS", "30")
    )
    resource_total_timeout_seconds: float = float(
        os.getenv("RESOURCE_TOTAL_TIMEOUT_SECONDS", "300")
    )
    resource_pdf_max_bytes: int = int(
        os.getenv(
            "RESOURCE_PDF_MAX_BYTES",
            str(100 * 1024 * 1024),
        )
    )
    resource_checkpoint_max_bytes: int = int(
        os.getenv(
            "RESOURCE_CHECKPOINT_MAX_BYTES",
            str(20 * 1024 * 1024 * 1024),
        )
    )
    resource_git_timeout_seconds: float = float(
        os.getenv("RESOURCE_GIT_TIMEOUT_SECONDS", "600")
    )
    resource_lease_seconds: float = float(
        os.getenv("RESOURCE_LEASE_SECONDS", "120")
    )
    resource_heartbeat_seconds: float = float(
        os.getenv("RESOURCE_HEARTBEAT_SECONDS", "30")
    )
    # true 时未配置 egress guard 的 Worker 必须 not_ready。
    resource_require_network_guard: bool = _env_bool(
        "RESOURCE_REQUIRE_NETWORK_GUARD", False
    )
    resource_network_guard_configured: bool = _env_bool(
        "RESOURCE_NETWORK_GUARD_CONFIGURED", False
    )
    resource_db_path: Path = Path(
        os.getenv(
            "RESOURCE_DB_PATH",
            str(_state_root / "resources/catalog.sqlite"),
        )
    )

    # Phase 30 Conversational Web Console
    # Vite 生产构建输出目录，由 FastAPI 同源托管。
    web_dist_dir: Path = Path(
        os.getenv("WEB_DIST_DIR", "web/dist")
    )
    # true 时缺少前端构建会让 API 启动失败。
    web_ui_required: bool = _env_bool(
        "WEB_UI_REQUIRED", False
    )
    # serve-stack 中 Resource Worker 的轮询间隔。
    resource_poll_seconds: float = float(
        os.getenv("RESOURCE_POLL_SECONDS", "1")
    )

    # Phase 31 Artifact-Grounded Chat Agent
    # 默认关闭，完成数据库和 API 接线后在部署环境显式开启。
    chat_enabled: bool = _env_bool(
        "CHAT_ENABLED", False
    )
    chat_db_path: Path = Path(
        os.getenv("CHAT_DB_PATH", str(_state_root / "chat/chat.sqlite"))
    )
    chat_history_messages: int = int(
        os.getenv("CHAT_HISTORY_MESSAGES", "12")
    )
    chat_artifacts_to_open: int = int(
        os.getenv("CHAT_ARTIFACTS_TO_OPEN", "12")
    )
    chat_source_limit: int = int(
        os.getenv("CHAT_SOURCE_LIMIT", "8")
    )
    chat_artifact_max_bytes: int = int(
        os.getenv("CHAT_ARTIFACT_MAX_BYTES", "12000")
    )
    chat_total_context_chars: int = int(
        os.getenv("CHAT_TOTAL_CONTEXT_CHARS", "48000")
    )
    chat_log_max_bytes: int = int(
        os.getenv("CHAT_LOG_MAX_BYTES", "8000")
    )

    # Phase 36：当前 Job 内会话记忆，不是跨 Job 用户长期记忆。
    chat_recent_messages: int = int(
        os.getenv(
            "CHAT_RECENT_MESSAGES",
            os.getenv("CHAT_HISTORY_MESSAGES", "12"),
        )
    )
    chat_compaction_enabled: bool = _env_bool(
        "CHAT_COMPACTION_ENABLED", True
    )
    chat_compaction_min_messages: int = int(
        os.getenv("CHAT_COMPACTION_MIN_MESSAGES", "12")
    )
    chat_compaction_max_messages: int = int(
        os.getenv("CHAT_COMPACTION_MAX_MESSAGES", "80")
    )
    chat_compaction_max_input_chars: int = int(
        os.getenv("CHAT_COMPACTION_MAX_INPUT_CHARS", "30000")
    )
    chat_memory_max_chars: int = int(
        os.getenv("CHAT_MEMORY_MAX_CHARS", "10000")
    )
    chat_history_max_chars: int = int(
        os.getenv("CHAT_HISTORY_MAX_CHARS", "12000")
    )
    chat_prompt_max_chars: int = int(
        os.getenv("CHAT_PROMPT_MAX_CHARS", "60000")
    )
    chat_memory_prompt_version: str = os.getenv(
        "CHAT_MEMORY_PROMPT_VERSION",
        "phase36-v1",
    ).strip()

    # Phase 52 Bounded Tool Calling；第一轮部署保持 false。
    chat_tool_calling_enabled: bool = _env_bool(
        "CHAT_TOOL_CALLING_ENABLED",
        False,
    )
    chat_tool_max_model_rounds: int = int(
        os.getenv("CHAT_TOOL_MAX_MODEL_ROUNDS", "4")
    )
    chat_tool_max_calls: int = int(
        os.getenv("CHAT_TOOL_MAX_CALLS", "3")
    )
    chat_tool_max_arguments_bytes: int = int(
        os.getenv("CHAT_TOOL_MAX_ARGUMENTS_BYTES", "8000")
    )
    chat_tool_max_result_chars: int = int(
        os.getenv("CHAT_TOOL_MAX_RESULT_CHARS", "12000")
    )
    chat_tool_total_result_chars: int = int(
        os.getenv("CHAT_TOOL_TOTAL_RESULT_CHARS", "24000")
    )

    # Phase 53：MCP 只读互操作网关。默认关闭。
    mcp_gateway_enabled: bool = _env_bool(
        "MCP_GATEWAY_ENABLED",
        False,
    )
    mcp_gateway_policy_path: Path = Path(
        os.getenv(
            "MCP_GATEWAY_POLICY_PATH",
            "config/mcp_gateway_policy.local.json",
        )
    )
    mcp_gateway_db_path: Path = Path(
        os.getenv(
            "MCP_GATEWAY_DB_PATH",
            str(_state_root / "control/mcp_gateway.sqlite"),
        )
    )
    mcp_gateway_total_timeout_seconds: float = float(
        os.getenv("MCP_GATEWAY_TOTAL_TIMEOUT_SECONDS", "15")
    )
    mcp_gateway_max_tools: int = int(
        os.getenv("MCP_GATEWAY_MAX_TOOLS", "64")
    )
    mcp_gateway_max_schema_bytes: int = int(
        os.getenv("MCP_GATEWAY_MAX_SCHEMA_BYTES", "20000")
    )
    mcp_gateway_max_result_bytes: int = int(
        os.getenv("MCP_GATEWAY_MAX_RESULT_BYTES", "20000")
    )

    # Phase 54：本项目作为 MCP Server 时的独立开关。
    mcp_export_enabled: bool = _env_bool(
        "MCP_EXPORT_ENABLED",
        False,
    )
    # 第一版只允许字面量 IPv4 loopback，不能配置 0.0.0.0 或主机名。
    mcp_export_host: str = os.getenv(
        "MCP_EXPORT_HOST",
        "127.0.0.1",
    )
    mcp_export_port: int = int(
        os.getenv("MCP_EXPORT_PORT", "8770")
    )
    # 这里只保存 Secret 的逻辑名称，不保存 Token 明文。
    mcp_export_token_secret_name: str = os.getenv(
        "MCP_EXPORT_TOKEN_SECRET_NAME",
        "PAPER_COPILOT_MCP_EXPORT_TOKEN",
    )
    mcp_export_audit_db_path: Path = Path(
        os.getenv(
            "MCP_EXPORT_AUDIT_DB_PATH",
            str(_state_root / "control/mcp_export_audit.sqlite"),
        )
    )
    mcp_export_max_artifacts: int = int(
        os.getenv("MCP_EXPORT_MAX_ARTIFACTS", "50")
    )
    mcp_export_max_report_chars: int = int(
        os.getenv("MCP_EXPORT_MAX_REPORT_CHARS", "50000")
    )
    mcp_export_max_calls_per_minute: int = int(
        os.getenv("MCP_EXPORT_MAX_CALLS_PER_MINUTE", "60")
    )

    # Phase 55：MCP 公开契约 Golden、Client Profile 和评测产物。
    mcp_contract_baseline_path: Path = Path(
        os.getenv(
            "MCP_CONTRACT_BASELINE_PATH",
            "config/mcp_export_contract_baseline.json",
        )
    )
    mcp_client_profiles_path: Path = Path(
        os.getenv(
            "MCP_CLIENT_PROFILES_PATH",
            "config/mcp_client_profiles.local.json",
        )
    )
    mcp_contract_report_root: Path = Path(
        os.getenv(
            "MCP_CONTRACT_REPORT_ROOT",
            "analysis/mcp_contract_eval",
        )
    )
    mcp_contract_timeout_seconds: float = float(
        os.getenv("MCP_CONTRACT_TIMEOUT_SECONDS", "15")
    )

    # Phase 56：MCP handler 有界执行、Runtime Policy 和派生报告。
    mcp_export_handler_workers: int = int(
        os.getenv("MCP_EXPORT_HANDLER_WORKERS", "4")
    )
    mcp_export_handler_queue: int = int(
        os.getenv("MCP_EXPORT_HANDLER_QUEUE", "8")
    )
    mcp_export_handler_timeout_seconds: float = float(
        os.getenv("MCP_EXPORT_HANDLER_TIMEOUT_SECONDS", "10")
    )
    mcp_runtime_policy_path: Path = Path(
        os.getenv(
            "MCP_RUNTIME_POLICY_PATH",
            "config/mcp_runtime_policy.json",
        )
    )
    mcp_runtime_report_root: Path = Path(
        os.getenv(
            "MCP_RUNTIME_REPORT_ROOT",
            "analysis/mcp_runtime",
        )
    )

    # Phase 38：独立 Run Comparison 派生资源。
    comparison_root: Path = Path(
        os.getenv("COMPARISON_ROOT", "comparisons")
    )
    comparison_manifest_max_bytes: int = int(
        os.getenv("COMPARISON_MANIFEST_MAX_BYTES", str(4 * 1024 * 1024))
    )
    comparison_report_max_bytes: int = int(
        os.getenv("COMPARISON_REPORT_MAX_BYTES", str(4 * 1024 * 1024))
    )
    comparison_max_artifacts: int = int(
        os.getenv("COMPARISON_MAX_ARTIFACTS", "1000")
    )
    comparison_max_changes: int = int(
        os.getenv("COMPARISON_MAX_CHANGES", "1000")
    )
    comparison_list_scan_limit: int = int(
        os.getenv("COMPARISON_LIST_SCAN_LIMIT", "1000")
    )
    comparison_staging_ttl_seconds: int = int(
        os.getenv("COMPARISON_STAGING_TTL_SECONDS", "3600")
    )
    comparison_chat_limit: int = int(
        os.getenv("COMPARISON_CHAT_LIMIT", "3")
    )
    comparison_chat_max_chars: int = int(
        os.getenv("COMPARISON_CHAT_MAX_CHARS", "12000")
    )

    # Phase 39：可信重跑提案。
    rerun_db_path: Path = Path(
        os.getenv("RERUN_DB_PATH", str(_state_root / "rerun/rerun.sqlite"))
    )
    rerun_proposal_ttl_seconds: int = int(
        os.getenv("RERUN_PROPOSAL_TTL_SECONDS", "86400")
    )
    rerun_max_command_chars: int = int(
        os.getenv("RERUN_MAX_COMMAND_CHARS", "8192")
    )
    rerun_max_argv_items: int = int(
        os.getenv("RERUN_MAX_ARGV_ITEMS", "256")
    )
    rerun_max_edits: int = int(
        os.getenv("RERUN_MAX_EDITS", "16")
    )

    # Phase 35：单机 retention 与容量保护。
    retention_enabled: bool = _env_bool(
        "RETENTION_ENABLED", True
    )
    retention_db_path: Path = Path(
        os.getenv(
            "RETENTION_DB_PATH",
            str(_state_root / "retention/retention.sqlite"),
        )
    )
    retention_job_days: int = int(
        os.getenv("RETENTION_JOB_DAYS", "14")
    )
    retention_plan_max_jobs: int = int(
        os.getenv("RETENTION_PLAN_MAX_JOBS", "20")
    )
    retention_plan_ttl_seconds: int = int(
        os.getenv(
            "RETENTION_PLAN_TTL_SECONDS",
            "1800",
        )
    )
    retention_local_blob_delete_enabled: bool = _env_bool(
        "RETENTION_LOCAL_BLOB_DELETE_ENABLED",
        True,
    )
    storage_soft_limit_bytes: int = int(
        os.getenv("STORAGE_SOFT_LIMIT_BYTES", "0")
    )
    storage_hard_limit_bytes: int = int(
        os.getenv("STORAGE_HARD_LIMIT_BYTES", "0")
    )
    storage_min_free_bytes: int = int(
        os.getenv(
            "STORAGE_MIN_FREE_BYTES",
            str(5 * 1024 * 1024 * 1024),
        )
    )
    storage_inventory_max_warnings: int = int(
        os.getenv(
            "STORAGE_INVENTORY_MAX_WARNINGS",
            "100",
        )
    )

    # Phase 44：单机持久通知 Materialized View。
    notification_db_path: Path = Path(
        os.getenv(
            "NOTIFICATION_DB_PATH",
            str(_state_root / "notifications/notifications.sqlite"),
        )
    )

    notification_projection_batch_size: int = int(
        os.getenv(
            "NOTIFICATION_PROJECTION_BATCH_SIZE",
            "200",
        )
    )

    notification_projection_max_batches: int = int(
        os.getenv(
            "NOTIFICATION_PROJECTION_MAX_BATCHES",
            "50",
        )
    )

    # Phase 45：单机 Verified Failure Memory。
    failure_memory_enabled: bool = _env_bool(
        "FAILURE_MEMORY_ENABLED",
        True,
    )
    failure_memory_db_path: Path = Path(
        os.getenv(
            "FAILURE_MEMORY_DB_PATH",
            str(_state_root / "failure_memory/failure_memory.sqlite"),
        )
    )
    failure_memory_max_json_bytes: int = int(
        os.getenv(
            "FAILURE_MEMORY_MAX_JSON_BYTES",
            str(2 * 1024 * 1024),
        )
    )
    failure_memory_max_log_bytes: int = int(
        os.getenv(
            "FAILURE_MEMORY_MAX_LOG_BYTES",
            str(2 * 1024 * 1024),
        )
    )
    failure_memory_candidate_limit: int = int(
        os.getenv("FAILURE_MEMORY_CANDIDATE_LIMIT", "200")
    )
    failure_memory_top_k: int = int(
        os.getenv("FAILURE_MEMORY_TOP_K", "5")
    )
    failure_memory_minimum_score: float = float(
        os.getenv("FAILURE_MEMORY_MINIMUM_SCORE", "0.35")
    )

    # Phase 46：单机项目级长期事实。
    project_memory_enabled: bool = _env_bool(
        "PROJECT_MEMORY_ENABLED",
        True,
    )
    project_memory_db_path: Path = Path(
        os.getenv(
            "PROJECT_MEMORY_DB_PATH",
            str(_state_root / "project_memory/project_memory.sqlite"),
        )
    )
    project_memory_top_k: int = int(
        os.getenv("PROJECT_MEMORY_TOP_K", "20")
    )
    project_memory_pack_max_chars: int = int(
        os.getenv("PROJECT_MEMORY_PACK_MAX_CHARS", "12000")
    )

    # Phase 48：受控 Agent Skill / Plugin Package。
    agent_skills_enabled: bool = _env_bool(
        "AGENT_SKILLS_ENABLED",
        False,
    )
    agent_skill_package_dir: Path = Path(
        os.getenv(
            "AGENT_SKILL_PACKAGE_DIR",
            "agent_skills",
        )
    )
    agent_skill_enabled_ids: frozenset[str] = _env_csv_values(
        "AGENT_SKILL_ENABLED_IDS",
        "cuda_build_diagnosis",
    )
    agent_skill_granted_capabilities: frozenset[str] = _env_csv_values(
        "AGENT_SKILL_GRANTED_CAPABILITIES",
        (
            "filesystem.read.workspace,"
            "filesystem.read.run,"
            "process.spawn.rg"
        ),
    )

    # Phase 50：确定性模型路由、预算预留和调用审计。
    # off 保持旧行为，shadow 只观测，active 强制路由和预算。
    model_routing_mode: str = os.getenv(
        "MODEL_ROUTING_MODE",
        "off",
    ).strip().lower()
    model_routing_policy_path: Path = Path(
        os.getenv(
            "MODEL_ROUTING_POLICY_PATH",
            "config/model_routing_policy.json",
        )
    )
    model_routing_db_path: Path = Path(
        os.getenv(
            "MODEL_ROUTING_DB_PATH",
            str(_state_root / "control/model_usage.sqlite"),
        )
    )

    # Phase 51：受限研究浏览默认关闭，启用后才解析 Policy 和 Search Secret。
    research_browser_enabled: bool = _env_bool(
        "RESEARCH_BROWSER_ENABLED",
        False,
    )
    research_browser_policy_path: Path = Path(
        os.getenv(
            "RESEARCH_BROWSER_POLICY_PATH",
            "config/research_browser_policy.json",
        )
    )
    research_browser_db_path: Path = Path(
        os.getenv(
            "RESEARCH_BROWSER_DB_PATH",
            str(_state_root / "control/research_browser.sqlite"),
        )
    )
    research_search_api_key_secret_name: str = os.getenv(
        "RESEARCH_SEARCH_API_KEY_SECRET_NAME",
        "RESEARCH_SEARCH_API_KEY",
    )
    research_search_timeout_seconds: float = float(
        os.getenv("RESEARCH_SEARCH_TIMEOUT_SECONDS", "15")
    )
    research_browser_lease_seconds: int = int(
        os.getenv("RESEARCH_BROWSER_LEASE_SECONDS", "300")
    )
    # application_only 表示仅有应用层 DNS/URL 检查；生产环境应改为 egress_proxy。
    research_browser_network_guard: str = os.getenv(
        "RESEARCH_BROWSER_NETWORK_GUARD",
        "application_only",
    ).strip().lower()

    # Phase 49：完成专项测试前默认关闭，不影响现有 Graph/Chat。
    knowledge_base_enabled: bool = _env_bool(
        "KNOWLEDGE_BASE_ENABLED",
        False,
    )
    knowledge_db_path: Path = Path(
        os.getenv(
            "KNOWLEDGE_DB_PATH",
            str(_state_root / "knowledge/knowledge.sqlite"),
        )
    )
    knowledge_max_artifact_bytes: int = int(
        os.getenv("KNOWLEDGE_MAX_ARTIFACT_BYTES", str(16 * 1024 * 1024))
    )
    knowledge_max_sections: int = int(
        os.getenv("KNOWLEDGE_MAX_SECTIONS", "2000")
    )
    knowledge_max_facts: int = int(
        os.getenv("KNOWLEDGE_MAX_FACTS", "10000")
    )
    knowledge_max_mappings: int = int(
        os.getenv("KNOWLEDGE_MAX_MAPPINGS", "2000")
    )
    knowledge_minimum_equivalence_score: float = float(
        os.getenv("KNOWLEDGE_MINIMUM_EQUIVALENCE_SCORE", "0.65")
    )
    knowledge_chat_max_entities: int = int(
        os.getenv("KNOWLEDGE_CHAT_MAX_ENTITIES", "12")
    )
    knowledge_chat_max_relations: int = int(
        os.getenv("KNOWLEDGE_CHAT_MAX_RELATIONS", "24")
    )
    knowledge_chat_max_chars: int = int(
        os.getenv("KNOWLEDGE_CHAT_MAX_CHARS", "16000")
    )

settings = Settings()

if settings.retrieval_policy_mode not in {
    "off",
    "shadow",
    "active",
}:
    raise ValueError(
        "RETRIEVAL_POLICY_MODE 必须是 off、shadow 或 active"
    )

settings.runs_dir.mkdir(
    parents=True,
    exist_ok=True,
)
settings.checkpoint_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)
settings.patch_coordination_dir.mkdir(
    parents=True,
    exist_ok=True,
)
settings.embedding_cache_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)
settings.job_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)
settings.artifact_catalog_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)
settings.resource_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

# Phase 31 Chat DB path 校验与目录创建
chat_db_path = settings.chat_db_path.expanduser().resolve()
allowed_root = settings.allowed_root.expanduser().resolve()
if (
    chat_db_path == allowed_root
    or allowed_root not in chat_db_path.parents
):
    raise ValueError(
        "CHAT_DB_PATH 必须是 ALLOWED_ROOT 内的文件路径"
    )
settings.chat_db_path = chat_db_path
settings.chat_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

if settings.chat_history_messages < 0:
    raise ValueError("CHAT_HISTORY_MESSAGES 不能小于 0")
if settings.chat_artifacts_to_open < 1:
    raise ValueError("CHAT_ARTIFACTS_TO_OPEN 必须至少为 1")
if settings.chat_source_limit < 1:
    raise ValueError("CHAT_SOURCE_LIMIT 必须至少为 1")
if settings.chat_artifact_max_bytes < 1024:
    raise ValueError("CHAT_ARTIFACT_MAX_BYTES 不能小于 1024")
if settings.chat_total_context_chars < settings.chat_artifact_max_bytes:
    raise ValueError(
        "CHAT_TOTAL_CONTEXT_CHARS 不能小于 CHAT_ARTIFACT_MAX_BYTES"
    )
if settings.chat_log_max_bytes < 1024:
    raise ValueError("CHAT_LOG_MAX_BYTES 不能小于 1024")

# Phase 36 Memory config validation
if settings.chat_recent_messages < 2:
    raise ValueError("CHAT_RECENT_MESSAGES 必须至少为 2")
if settings.chat_recent_messages % 2 != 0:
    raise ValueError("CHAT_RECENT_MESSAGES 必须为偶数")
if settings.chat_compaction_min_messages < 2:
    raise ValueError("CHAT_COMPACTION_MIN_MESSAGES 必须至少为 2")
if settings.chat_compaction_min_messages % 2 != 0:
    raise ValueError("CHAT_COMPACTION_MIN_MESSAGES 必须为偶数")
if settings.chat_compaction_max_messages < settings.chat_compaction_min_messages:
    raise ValueError(
        "CHAT_COMPACTION_MAX_MESSAGES 不能小于 MIN_MESSAGES"
    )
if settings.chat_compaction_max_messages % 2 != 0:
    raise ValueError("CHAT_COMPACTION_MAX_MESSAGES 必须为偶数")
if settings.chat_compaction_max_messages > 500:
    raise ValueError("CHAT_COMPACTION_MAX_MESSAGES 不能超过 Store 上限 500")
if settings.chat_compaction_max_input_chars < 4000:
    raise ValueError("CHAT_COMPACTION_MAX_INPUT_CHARS 不能小于 4000")
if settings.chat_memory_max_chars < 2000:
    raise ValueError("CHAT_MEMORY_MAX_CHARS 不能小于 2000")
if settings.chat_history_max_chars < 1000:
    raise ValueError("CHAT_HISTORY_MAX_CHARS 不能小于 1000")
if settings.chat_prompt_max_chars <= (
    settings.chat_memory_max_chars
    + settings.chat_history_max_chars
):
    raise ValueError(
        "CHAT_PROMPT_MAX_CHARS 必须为 Grounding Sources 留出空间"
    )
if not settings.chat_memory_prompt_version:
    raise ValueError("CHAT_MEMORY_PROMPT_VERSION 不能为空")

if not 1 <= settings.chat_tool_max_model_rounds <= 6:
    raise ValueError("CHAT_TOOL_MAX_MODEL_ROUNDS 超出范围 1..6")
if not 1 <= settings.chat_tool_max_calls <= 3:
    raise ValueError("CHAT_TOOL_MAX_CALLS 超出范围 1..3")
if settings.chat_tool_max_model_rounds < settings.chat_tool_max_calls:
    raise ValueError("Tool Model Round 不能小于 Tool Call 上限")
if not 1024 <= settings.chat_tool_max_arguments_bytes <= 20000:
    raise ValueError("CHAT_TOOL_MAX_ARGUMENTS_BYTES 超出范围")
if not 2000 <= settings.chat_tool_max_result_chars <= 20000:
    raise ValueError("CHAT_TOOL_MAX_RESULT_CHARS 超出范围")
if (
    settings.chat_tool_total_result_chars
    < settings.chat_tool_max_result_chars
):
    raise ValueError("Tool 累计结果预算不能小于单次预算")
if settings.chat_tool_total_result_chars > 40000:
    raise ValueError("Tool 累计结果预算不能超过 40000 字符")

# Phase 38 Comparison 只允许写入项目受控根目录。
settings.comparison_root = settings.comparison_root.expanduser().resolve()
comparison_allowed_root = settings.job_export_allowed_root.expanduser().resolve()
if (
    settings.comparison_root == comparison_allowed_root
    or comparison_allowed_root not in settings.comparison_root.parents
):
    raise ValueError("COMPARISON_ROOT 必须是项目允许根目录内的子目录")
settings.comparison_root.mkdir(parents=True, exist_ok=True)

if min(
    settings.comparison_manifest_max_bytes,
    settings.comparison_report_max_bytes,
    settings.comparison_max_artifacts,
    settings.comparison_max_changes,
    settings.comparison_list_scan_limit,
    settings.comparison_staging_ttl_seconds,
    settings.comparison_chat_limit,
    settings.comparison_chat_max_chars,
) < 1:
    raise ValueError("Phase 38 Comparison limits 必须全部大于 0")

if settings.openai_max_output_tokens < 1:
    raise ValueError(
        "OPENAI_MAX_OUTPUT_TOKENS 必须至少为 1"
    )

if settings.paper_section_chunk_chars < 1:
    raise ValueError(
        "PAPER_SECTION_CHUNK_CHARS 必须至少为 1"
    )

if settings.paper_max_section_llm_calls < 1:
    raise ValueError(
        "PAPER_MAX_SECTION_LLM_CALLS 必须至少为 1"
    )

if settings.mapping_max_targets < 1:
    raise ValueError(
        "MAPPING_MAX_TARGETS 必须至少为 1"
    )

for mapping_limit_name, mapping_limit in {
    "MAPPING_MAX_CORE_METHOD_TARGETS": (
        settings.mapping_max_core_method_targets
    ),
    "MAPPING_MAX_DATA_PIPELINE_TARGETS": (
        settings.mapping_max_data_pipeline_targets
    ),
    "MAPPING_MAX_TRAINING_CONFIG_TARGETS": (
        settings.mapping_max_training_config_targets
    ),
    "MAPPING_MAX_EVALUATION_METRIC_TARGETS": (
        settings.mapping_max_evaluation_metric_targets
    ),
    "MAPPING_MAX_ABLATION_SWITCH_TARGETS": (
        settings.mapping_max_ablation_switch_targets
    ),
}.items():
    if mapping_limit < 0:
        raise ValueError(
            f"{mapping_limit_name} 必须大于或等于 0"
        )

if settings.openai_thinking_mode not in {
    None,
    "enabled",
    "disabled",
}:
    raise ValueError(
        "OPENAI_THINKING_MODE 只能是 enabled、disabled 或空值"
    )

if settings.job_heartbeat_seconds <= 0:
    raise ValueError(
        "JOB_HEARTBEAT_SECONDS 必须大于 0"
    )

if (
    settings.job_lease_seconds
    <= settings.job_heartbeat_seconds * 2
):
    raise ValueError(
        "JOB_LEASE_SECONDS 必须大于 "
        "2 * JOB_HEARTBEAT_SECONDS"
    )

if settings.job_max_attempts < 1:
    raise ValueError(
        "JOB_MAX_ATTEMPTS 必须至少为 1"
    )

if not 1 <= settings.api_port <= 65535:
    raise ValueError(
        "AGENT_API_PORT 必须位于 1..65535"
    )

if settings.api_event_poll_seconds <= 0:
    raise ValueError(
        "AGENT_API_EVENT_POLL_SECONDS 必须大于 0"
    )

if settings.api_sse_heartbeat_seconds <= 0:
    raise ValueError(
        "AGENT_API_SSE_HEARTBEAT_SECONDS 必须大于 0"
    )

if settings.api_max_page_size < 1:
    raise ValueError(
        "AGENT_API_MAX_PAGE_SIZE 必须至少为 1"
    )

if settings.api_max_log_bytes < 1024:
    raise ValueError(
        "AGENT_API_MAX_LOG_BYTES 必须至少为 1024"
    )
if settings.artifact_blob_backend not in {
    "local",
    "s3",
}:
    raise ValueError(
        "ARTIFACT_BLOB_BACKEND 必须是 local 或 s3"
    )

if not settings.artifact_s3_bucket.strip():
    raise ValueError(
        "ARTIFACT_S3_BUCKET 不能为空"
    )

if settings.artifact_s3_max_attempts < 1:
    raise ValueError(
        "ARTIFACT_S3_MAX_ATTEMPTS 必须至少为 1"
    )

if settings.artifact_stream_chunk_bytes < 64 * 1024:
    raise ValueError(
        "ARTIFACT_STREAM_CHUNK_BYTES 不能小于 64 KiB"
    )

if not 1024 <= settings.artifact_preview_max_bytes <= 4 * 1024 * 1024:
    raise ValueError(
        "ARTIFACT_PREVIEW_MAX_BYTES 必须位于 1 KiB..4 MiB"
    )

if settings.job_export_max_artifacts < 1:
    raise ValueError(
        "JOB_EXPORT_MAX_ARTIFACTS 必须至少为 1"
    )

if settings.job_export_max_uncompressed_bytes < 1024:
    raise ValueError(
        "JOB_EXPORT_MAX_UNCOMPRESSED_BYTES 必须至少为 1 KiB"
    )

if settings.job_export_max_archive_bytes < 1024:
    raise ValueError(
        "JOB_EXPORT_MAX_ARCHIVE_BYTES 必须至少为 1 KiB"
    )

if settings.job_export_staging_ttl_seconds < 60:
    raise ValueError(
        "JOB_EXPORT_STAGING_TTL_SECONDS 不能小于 60 秒"
    )

if settings.job_store_backend not in {
    "sqlite",
    "postgresql",
}:
    raise ValueError(
        "JOB_STORE_BACKEND 必须是 sqlite 或 postgresql"
    )

if settings.checkpoint_backend not in {
    "sqlite",
    "postgresql",
}:
    raise ValueError(
        "CHECKPOINT_BACKEND 必须是 sqlite 或 postgresql"
    )

uses_postgres = (
    settings.job_store_backend == "postgresql"
    or settings.checkpoint_backend == "postgresql"
)
if uses_postgres and not settings.database_url_secret_name.strip():
    raise ValueError(
        "PostgreSQL backend 需要 DATABASE_URL_SECRET_NAME"
    )

if settings.database_pool_size < 1:
    raise ValueError(
        "DATABASE_POOL_SIZE 必须至少为 1"
    )

if (
    settings.checkpoint_postgres_pool_min_size < 1
    or settings.checkpoint_postgres_pool_max_size
    < settings.checkpoint_postgres_pool_min_size
):
    raise ValueError(
        "Checkpoint pool min/max 配置无效"
    )

# Phase 26 workspace / worker 校验与受控目录
settings.worker_workspace_root.mkdir(
    parents=True,
    exist_ok=True,
)
settings.workspace_staging_root.mkdir(
    parents=True,
    exist_ok=True,
)

if not settings.worker_host_id:
    raise ValueError("WORKER_HOST_ID 不能为空")
if not settings.worker_pool:
    raise ValueError("WORKER_POOL 不能为空")
if (
    settings.worker_session_lease_seconds
    <= settings.worker_session_heartbeat_seconds * 2
):
    raise ValueError(
        "WORKER_SESSION_LEASE_SECONDS 必须大于 heartbeat 的 2 倍"
    )
if settings.workspace_max_file_bytes <= 0:
    raise ValueError("WORKSPACE_MAX_FILE_BYTES 必须大于 0")
if (
    settings.worker_workspace_root.expanduser().resolve()
    == settings.allowed_root.expanduser().resolve()
):
    raise ValueError(
        "WORKER_WORKSPACE_ROOT 不能直接等于 ALLOWED_ROOT"
    )

# Phase 29 资源受控目录：staging/materialized 必须存在且位于 allowed_root。
settings.resource_staging_root.mkdir(
    parents=True,
    exist_ok=True,
)
settings.resource_materialized_root.mkdir(
    parents=True,
    exist_ok=True,
)
if settings.resource_max_redirects < 0:
    raise ValueError(
        "RESOURCE_MAX_REDIRECTS 必须大于或等于 0"
    )
if settings.resource_connect_timeout_seconds <= 0:
    raise ValueError(
        "RESOURCE_CONNECT_TIMEOUT_SECONDS 必须大于 0"
    )
if settings.resource_read_timeout_seconds <= 0:
    raise ValueError(
        "RESOURCE_READ_TIMEOUT_SECONDS 必须大于 0"
    )
if settings.resource_total_timeout_seconds <= 0:
    raise ValueError(
        "RESOURCE_TOTAL_TIMEOUT_SECONDS 必须大于 0"
    )
if settings.resource_pdf_max_bytes <= 0:
    raise ValueError("RESOURCE_PDF_MAX_BYTES 必须大于 0")
if settings.resource_checkpoint_max_bytes <= 0:
    raise ValueError(
        "RESOURCE_CHECKPOINT_MAX_BYTES 必须大于 0"
    )
if settings.resource_git_timeout_seconds <= 0:
    raise ValueError(
        "RESOURCE_GIT_TIMEOUT_SECONDS 必须大于 0"
    )
if not settings.resource_allowed_hosts:
    raise ValueError(
        "RESOURCE_ALLOWED_HOSTS 不能为空"
    )
if (
    settings.resource_lease_seconds
    <= settings.resource_heartbeat_seconds * 2
):
    raise ValueError(
        "RESOURCE_LEASE_SECONDS 必须大于 "
        "2 * RESOURCE_HEARTBEAT_SECONDS"
    )

# Phase 35 retention DB path 校验与目录创建
settings.retention_db_path = (
    settings.retention_db_path.expanduser().resolve()
)
retention_allowed_root = settings.job_export_allowed_root.expanduser().resolve()
if (
    settings.retention_db_path == retention_allowed_root
    or retention_allowed_root not in settings.retention_db_path.parents
):
    raise ValueError(
        "RETENTION_DB_PATH 必须位于项目允许根目录内"
    )
settings.retention_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

if settings.retention_job_days < 1:
    raise ValueError(
        "RETENTION_JOB_DAYS 必须 >= 1；"
        "测试请直接注入 RetentionPolicy"
    )
if not 1 <= settings.retention_plan_max_jobs <= 100:
    raise ValueError(
        "RETENTION_PLAN_MAX_JOBS 必须为 1..100"
    )
if settings.retention_plan_ttl_seconds < 60:
    raise ValueError(
        "RETENTION_PLAN_TTL_SECONDS 必须 >= 60"
    )
if min(
    settings.storage_soft_limit_bytes,
    settings.storage_hard_limit_bytes,
    settings.storage_min_free_bytes,
) < 0:
    raise ValueError("storage limit 不能为负数")
if (
    settings.storage_soft_limit_bytes
    and settings.storage_hard_limit_bytes
    and settings.storage_soft_limit_bytes
    > settings.storage_hard_limit_bytes
):
    raise ValueError(
        "STORAGE_SOFT_LIMIT_BYTES 不能大于 HARD limit"
    )

# Phase 39 rerun DB path 校验与目录创建
settings.rerun_db_path = settings.rerun_db_path.expanduser().resolve()

rerun_allowed_root = settings.job_export_allowed_root.expanduser().resolve()
if (
    settings.rerun_db_path == rerun_allowed_root
    or rerun_allowed_root not in settings.rerun_db_path.parents
):
    raise ValueError("RERUN_DB_PATH 必须位于受控项目数据根目录内")

settings.rerun_db_path.parent.mkdir(parents=True, exist_ok=True)

for name, value in {
    "RERUN_PROPOSAL_TTL_SECONDS": settings.rerun_proposal_ttl_seconds,
    "RERUN_MAX_COMMAND_CHARS": settings.rerun_max_command_chars,
    "RERUN_MAX_ARGV_ITEMS": settings.rerun_max_argv_items,
    "RERUN_MAX_EDITS": settings.rerun_max_edits,
}.items():
    if value <= 0:
        raise ValueError(f"{name} 必须大于 0")

# Phase 44 notification DB path 校验与目录创建
notification_db_path = (
    settings.notification_db_path.expanduser().resolve()
)
if (
    notification_db_path == allowed_root
    or allowed_root not in notification_db_path.parents
):
    raise ValueError(
        "NOTIFICATION_DB_PATH 必须是 ALLOWED_ROOT 内的文件路径"
    )
settings.notification_db_path = notification_db_path
settings.notification_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

if settings.notification_projection_batch_size < 1:
    raise ValueError(
        "NOTIFICATION_PROJECTION_BATCH_SIZE 必须至少为 1"
    )
if settings.notification_projection_max_batches < 1:
    raise ValueError(
        "NOTIFICATION_PROJECTION_MAX_BATCHES 必须至少为 1"
    )

# Phase 45 Failure Memory DB 必须位于受控数据根目录内。
failure_memory_db_path = (
    settings.failure_memory_db_path.expanduser().resolve()
)
if (
    failure_memory_db_path == allowed_root
    or allowed_root not in failure_memory_db_path.parents
):
    raise ValueError(
        "FAILURE_MEMORY_DB_PATH 必须是 ALLOWED_ROOT 内的文件路径"
    )
settings.failure_memory_db_path = failure_memory_db_path
settings.failure_memory_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

for name, value in {
    "FAILURE_MEMORY_MAX_JSON_BYTES": (
        settings.failure_memory_max_json_bytes
    ),
    "FAILURE_MEMORY_MAX_LOG_BYTES": (
        settings.failure_memory_max_log_bytes
    ),
    "FAILURE_MEMORY_CANDIDATE_LIMIT": (
        settings.failure_memory_candidate_limit
    ),
    "FAILURE_MEMORY_TOP_K": settings.failure_memory_top_k,
}.items():
    if value < 1:
        raise ValueError(f"{name} 必须至少为 1")

if not 0.0 <= settings.failure_memory_minimum_score <= 1.0:
    raise ValueError(
        "FAILURE_MEMORY_MINIMUM_SCORE 必须位于 0..1"
    )
if (
    settings.failure_memory_top_k
    > settings.failure_memory_candidate_limit
):
    raise ValueError(
        "FAILURE_MEMORY_TOP_K 不能大于 CANDIDATE_LIMIT"
    )

# Phase 46 Project Memory DB path 校验与目录创建
project_memory_db_path = (
    settings.project_memory_db_path.expanduser().resolve()
)
if (
    project_memory_db_path == allowed_root
    or allowed_root not in project_memory_db_path.parents
):
    raise ValueError(
        "PROJECT_MEMORY_DB_PATH 必须是 ALLOWED_ROOT 内的文件路径"
    )
settings.project_memory_db_path = project_memory_db_path
settings.project_memory_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

if not 1 <= settings.project_memory_top_k <= 100:
    raise ValueError("PROJECT_MEMORY_TOP_K 必须为 1..100")
if not 2000 <= settings.project_memory_pack_max_chars <= 100000:
    raise ValueError("PROJECT_MEMORY_PACK_MAX_CHARS 必须为 2000..100000")

# Phase 41 Secret 路径校验
settings.secret_master_key_path = (
    Path(
        os.path.abspath(
            settings.secret_master_key_path.expanduser()
        )
    )
)
settings.secret_vault_db_path = (
    Path(
        os.path.abspath(
            settings.secret_vault_db_path.expanduser()
        )
    )
)

if (
    settings.secret_master_key_path.parent
    != settings.secret_vault_db_path.parent
):
    raise ValueError(
        "第一版要求 Master Key 与 Vault 位于同一受控 secrets 目录"
    )

secret_root = settings.secret_master_key_path.parent
allowed_root = Path(
    os.path.abspath(settings.allowed_root.expanduser())
)
if not secret_root.is_relative_to(allowed_root):
    raise ValueError(
        "Secret 路径必须位于 ALLOWED_ROOT 内"
    )

for secret_name in (
    settings.openai_api_key_secret_name,
    settings.embedding_api_key_secret_name,
    settings.database_url_secret_name,
    settings.api_token_secret_name,
):
    if not secret_name.strip():
        raise ValueError("Secret name 配置不能为空")

# Phase 48 Skill Package Root 校验。
skill_package_input = settings.agent_skill_package_dir.expanduser()
if skill_package_input.is_symlink():
    raise ValueError("AGENT_SKILL_PACKAGE_DIR 不能是符号链接")

skill_package_root = skill_package_input.resolve()
allowed_root = settings.allowed_root.expanduser().resolve()
if (
    skill_package_root == allowed_root
    or allowed_root not in skill_package_root.parents
):
    raise ValueError(
        "AGENT_SKILL_PACKAGE_DIR 必须是 ALLOWED_ROOT 内的独立目录"
    )
settings.agent_skill_package_dir = skill_package_root

allowed_skill_capabilities = {
    "filesystem.read.workspace",
    "filesystem.read.run",
    "process.spawn.rg",
}
unknown_skill_capabilities = (
    set(settings.agent_skill_granted_capabilities)
    - allowed_skill_capabilities
)
if unknown_skill_capabilities:
    raise ValueError(
        "AGENT_SKILL_GRANTED_CAPABILITIES 包含第一版不允许的能力："
        f"{sorted(unknown_skill_capabilities)}"
    )

# Phase 49 Knowledge Base DB path 校验与目录创建
knowledge_db_path = settings.knowledge_db_path.expanduser().resolve()
allowed_root = settings.allowed_root.expanduser().resolve()
if (
    knowledge_db_path == allowed_root
    or allowed_root not in knowledge_db_path.parents
):
    raise ValueError("KNOWLEDGE_DB_PATH 必须位于 ALLOWED_ROOT 内")
settings.knowledge_db_path = knowledge_db_path
settings.knowledge_db_path.parent.mkdir(parents=True, exist_ok=True)

if not 1024 <= settings.knowledge_max_artifact_bytes <= 64 * 1024 * 1024:
    raise ValueError("KNOWLEDGE_MAX_ARTIFACT_BYTES 超出范围")
if not 1 <= settings.knowledge_max_sections <= 10000:
    raise ValueError("KNOWLEDGE_MAX_SECTIONS 超出范围")
if not 1 <= settings.knowledge_max_facts <= 50000:
    raise ValueError("KNOWLEDGE_MAX_FACTS 超出范围")
if not 1 <= settings.knowledge_max_mappings <= 10000:
    raise ValueError("KNOWLEDGE_MAX_MAPPINGS 超出范围")
if not 0.0 <= settings.knowledge_minimum_equivalence_score <= 1.0:
    raise ValueError("KNOWLEDGE_MINIMUM_EQUIVALENCE_SCORE 超出范围")
if not 1 <= settings.knowledge_chat_max_entities <= 50:
    raise ValueError("KNOWLEDGE_CHAT_MAX_ENTITIES 超出范围")
if not 1 <= settings.knowledge_chat_max_relations <= 100:
    raise ValueError("KNOWLEDGE_CHAT_MAX_RELATIONS 超出范围")
if not 2000 <= settings.knowledge_chat_max_chars <= 50000:
    raise ValueError("KNOWLEDGE_CHAT_MAX_CHARS 超出范围")

# Phase 50 Model Routing 校验
if settings.model_routing_mode not in {"off", "shadow", "active"}:
    raise ValueError(
        "MODEL_ROUTING_MODE 必须是 off、shadow 或 active"
    )

model_policy_path = (
    settings.model_routing_policy_path.expanduser().resolve()
)
model_allowed_root = settings.allowed_root.expanduser().resolve()
if (
    model_policy_path == model_allowed_root
    or model_allowed_root not in model_policy_path.parents
):
    raise ValueError(
        "MODEL_ROUTING_POLICY_PATH 必须位于 ALLOWED_ROOT 内"
    )
settings.model_routing_policy_path = model_policy_path

model_db_path = settings.model_routing_db_path.expanduser().resolve()
if (
    model_db_path == model_allowed_root
    or model_allowed_root not in model_db_path.parents
):
    raise ValueError(
        "MODEL_ROUTING_DB_PATH 必须是 ALLOWED_ROOT 内的文件路径"
    )
settings.model_routing_db_path = model_db_path
settings.model_routing_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

if not settings.openai_economy_model.strip():
    raise ValueError("OPENAI_ECONOMY_MODEL 不能为空")
if not settings.openai_strong_model.strip():
    raise ValueError("OPENAI_STRONG_MODEL 不能为空")

# Phase 51 Research Browser 校验
if not 1.0 <= settings.research_search_timeout_seconds <= 60.0:
    raise ValueError("RESEARCH_SEARCH_TIMEOUT_SECONDS 超出范围")
if not 30 <= settings.research_browser_lease_seconds <= 3600:
    raise ValueError("RESEARCH_BROWSER_LEASE_SECONDS 超出范围")
if settings.research_browser_network_guard not in {
    "application_only",
    "egress_proxy",
}:
    raise ValueError(
        "RESEARCH_BROWSER_NETWORK_GUARD 必须是 "
        "application_only 或 egress_proxy"
    )
if not settings.research_search_api_key_secret_name.strip():
    raise ValueError("RESEARCH_SEARCH_API_KEY_SECRET_NAME 不能为空")

for field_name, configured_path in (
    ("RESEARCH_BROWSER_POLICY_PATH", settings.research_browser_policy_path),
    ("RESEARCH_BROWSER_DB_PATH", settings.research_browser_db_path),
):
    resolved_path = configured_path.expanduser().resolve()
    if (
        resolved_path == model_allowed_root
        or model_allowed_root not in resolved_path.parents
    ):
        raise ValueError(f"{field_name} 必须位于 ALLOWED_ROOT 内")
    if field_name == "RESEARCH_BROWSER_POLICY_PATH":
        settings.research_browser_policy_path = resolved_path
    else:
        settings.research_browser_db_path = resolved_path

settings.research_browser_db_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

# Phase 54 MCP Export 校验
if settings.mcp_export_host != "127.0.0.1":
    raise ValueError(
        "Phase 54 MCP Export 只允许监听 127.0.0.1"
    )
if not 1024 <= settings.mcp_export_port <= 65535:
    raise ValueError(
        "MCP_EXPORT_PORT 必须位于 1024..65535"
    )
if not 1 <= settings.mcp_export_max_artifacts <= 100:
    raise ValueError(
        "MCP_EXPORT_MAX_ARTIFACTS 必须位于 1..100"
    )
if not 1000 <= settings.mcp_export_max_report_chars <= 100000:
    raise ValueError(
        "MCP_EXPORT_MAX_REPORT_CHARS 必须位于 1000..100000"
    )
if not 1 <= settings.mcp_export_max_calls_per_minute <= 600:
    raise ValueError(
        "MCP_EXPORT_MAX_CALLS_PER_MINUTE 必须位于 1..600"
    )

# Phase 55 MCP Contract 路径必须全部位于项目 ALLOWED_ROOT 内。
for field_name, configured_path in (
    ("MCP_CONTRACT_BASELINE_PATH", settings.mcp_contract_baseline_path),
    ("MCP_CLIENT_PROFILES_PATH", settings.mcp_client_profiles_path),
    ("MCP_CONTRACT_REPORT_ROOT", settings.mcp_contract_report_root),
):
    resolved_path = configured_path.expanduser().resolve()
    if (
        resolved_path == model_allowed_root
        or model_allowed_root not in resolved_path.parents
    ):
        raise ValueError(f"{field_name} 必须位于 ALLOWED_ROOT 内")
    if field_name == "MCP_CONTRACT_BASELINE_PATH":
        settings.mcp_contract_baseline_path = resolved_path
    elif field_name == "MCP_CLIENT_PROFILES_PATH":
        settings.mcp_client_profiles_path = resolved_path
    else:
        settings.mcp_contract_report_root = resolved_path

if not 1 <= settings.mcp_contract_timeout_seconds <= 60:
    raise ValueError("MCP_CONTRACT_TIMEOUT_SECONDS 必须位于 1..60")

settings.mcp_contract_report_root.mkdir(
    parents=True,
    exist_ok=True,
)

# Phase 56 MCP handler 和 Runtime Policy 校验。
if not 1 <= settings.mcp_export_handler_workers <= 16:
    raise ValueError("MCP_EXPORT_HANDLER_WORKERS 必须位于 1..16")
if not 0 <= settings.mcp_export_handler_queue <= 64:
    raise ValueError("MCP_EXPORT_HANDLER_QUEUE 必须位于 0..64")
if not 0.1 <= settings.mcp_export_handler_timeout_seconds <= 60:
    raise ValueError(
        "MCP_EXPORT_HANDLER_TIMEOUT_SECONDS 必须位于 0.1..60"
    )

for field_name, configured_path in (
    ("MCP_RUNTIME_POLICY_PATH", settings.mcp_runtime_policy_path),
    ("MCP_RUNTIME_REPORT_ROOT", settings.mcp_runtime_report_root),
):
    resolved_path = configured_path.expanduser().resolve()
    if (
        resolved_path == model_allowed_root
        or model_allowed_root not in resolved_path.parents
    ):
        raise ValueError(f"{field_name} 必须位于 ALLOWED_ROOT 内")
    if field_name == "MCP_RUNTIME_POLICY_PATH":
        settings.mcp_runtime_policy_path = resolved_path
    else:
        settings.mcp_runtime_report_root = resolved_path

settings.mcp_runtime_report_root.mkdir(
    parents=True,
    exist_ok=True,
)
