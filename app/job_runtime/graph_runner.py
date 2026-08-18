from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from langgraph.types import Command

from app.config import settings
from app.graph import build_graph
from app.job_runtime.heartbeat import (
    LeaseHeartbeat,
)
from app.job_runtime.schemas import (
    JobClaim,
    JobExecutionOutcome,
    JobInterrupt,
)
from app.observability.context import bind_telemetry_context
from app.observability.instrumentation import increment_counter_safe, record_span_exception_safe
from app.observability.runtime import build_telemetry_runtime as _build_tel
from app.observability.ports import TelemetryPort
from app.rerun.command_template import resolve_command_template
from app.schemas import ArtifactRecord
from app.workspace.rebind import (
    build_workspace_state_update,
)


class JobGraphStateError(RuntimeError):
    pass


def _bounded_preview(
    value: Any,
    *,
    max_chars: int,
) -> Any:
    """
    preview 必须可 JSON 序列化并有大小上限。

    超限时不截断 JSON 字符串再反解析，而是保存明确 summary。
    """

    serialized = json.dumps(
        value,
        ensure_ascii=False,
        default=str,
    )
    if len(serialized) <= max_chars:
        return json.loads(serialized)
    return {
        "truncated": True,
        "preview": serialized[:max_chars],
        "original_chars": len(serialized),
    }


def extract_snapshot_interrupts(
    snapshot: Any,
    *,
    max_preview_chars: int,
) -> list[JobInterrupt]:
    interruptions: list[JobInterrupt] = []

    for task in getattr(
        snapshot,
        "tasks",
        (),
    ):
        node_name = str(
            getattr(task, "name", "unknown")
        )
        for item in getattr(
            task,
            "interrupts",
            (),
        ):
            interrupt_id = getattr(
                item,
                "id",
                None,
            )
            interruptions.append(
                JobInterrupt(
                    node=node_name,
                    interrupt_id=(
                        str(interrupt_id)
                        if interrupt_id is not None
                        else None
                    ),
                    value_preview=_bounded_preview(
                        getattr(
                            item,
                            "value",
                            None,
                        ),
                        max_chars=(
                            max_preview_chars
                        ),
                    ),
                )
            )
    return interruptions


def _result_summary(
    *,
    claim: JobClaim,
    state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "job_id": claim.job.job_id,
        "thread_id": claim.job.thread_id,
        "run_id": state.get(
            "run_id",
            claim.job.run_id,
        ),
        "run_dir": state.get(
            "run_dir",
            claim.job.run_dir,
        ),
        "final_status": state.get(
            "final_status"
        ),
        "run_manifest_path": state.get(
            "run_manifest_path"
        ),
        "stage_error_count": len(
            state.get("stage_errors", [])
        ),
        "output_file_count": len(
            state.get("output_files", [])
        ),
    }


def _artifact_records(
    state: dict[str, Any],
    *,
    expected_run_id: str,
) -> list[ArtifactRecord]:
    """从 checkpoint 提取并验证本次 run 的 Artifact。"""

    records = [
        ArtifactRecord.model_validate(item)
        for item in state.get(
            "artifact_records",
            [],
        )
    ]
    for record in records:
        if record.run_id != expected_run_id:
            raise JobGraphStateError(
                "checkpoint Artifact run_id "
                "与 Job 不一致"
            )
    return records


class GraphJobRunner:
    def __init__(
        self,
        *,
        graph_factory: Callable[[], Any] = build_graph,
        interrupt_preview_chars: int | None = None,
        telemetry: TelemetryPort | None = None,
    ):
        self.graph_factory = graph_factory
        self.interrupt_preview_chars = (
            interrupt_preview_chars
            if interrupt_preview_chars is not None
            else settings.job_interrupt_preview_chars
        )
        try:
            self.telemetry: TelemetryPort = (
                telemetry if telemetry is not None else _build_tel().telemetry
            )
        except Exception:
            from app.observability.noop import NoOpTelemetry
            self.telemetry = NoOpTelemetry()

    def _config(
        self,
        thread_id: str,
    ) -> dict[str, Any]:
        return {
            "configurable": {
                "thread_id": thread_id,
            },
            # 修复闭环包含回边，显式预算比 LangGraph 默认值更稳妥。
            "recursion_limit": max(
                settings.max_steps * 3,
                60,
            ),
        }

    def _initial_state(
        self,
        claim: JobClaim,
    ) -> dict[str, Any]:
        request = claim.job.request
        binding = claim.workspace_binding
        if binding is None or binding.status != "ready":
            raise JobGraphStateError(
                "Graph 初始执行前 workspace 尚未 ready"
            )

        rerun_seed = None
        if request.derived_run is not None:
            resolved = resolve_command_template(
                template=request.derived_run.command_template,
                repo_path=binding.repo_path,
                run_dir=binding.run_dir,
                dataset_mounts=claim.worker.capabilities.dataset_mounts,
            )
            rerun_seed = {
                "proposal_id": request.derived_run.proposal_id,
                "proposal_hash": request.derived_run.proposal_hash,
                "source": request.derived_run.source.model_dump(mode="json"),
                "template_hash": request.derived_run.command_template.template_hash,
                "run_command": resolved,
            }

        return {
            "job_id": claim.job.job_id,
            "thread_id": claim.job.thread_id,
            "task_id": claim.job.thread_id,
            "run_id": claim.job.run_id,
            "run_dir": binding.run_dir,
            "paper_path": binding.paper_path,
            "repo_path": binding.repo_path,
            "log_path": binding.log_path,
            "workspace_binding": (
                binding.model_dump()
            ),
            "workspace_assignment_epoch": (
                binding.assignment_epoch
            ),
            "workspace_manifest_id": (
                binding.manifest_id
            ),
            "workspace_manifest_hash": (
                binding.manifest_hash
            ),
            "execution_profile_id": (
                request.execution_profile_id
            ),
            "experiment_goal": (
                request.experiment_goal
            ),
            "output_files": [],
            "artifact_records": [],
            "stage_errors": [],
            "inputs_validated": False,
            "step_count": 0,
            "max_steps": settings.max_steps,
            "rerun_seed": rerun_seed,
            "rerun_seed_path": None,
        }

    def _interrupts(
        self,
        snapshot: Any,
    ) -> list[JobInterrupt]:
        return extract_snapshot_interrupts(
            snapshot,
            max_preview_chars=(
                self.interrupt_preview_chars
            ),
        )

    def execute(
        self,
        claim: JobClaim,
        heartbeat: LeaseHeartbeat,
    ) -> JobExecutionOutcome:
        telemetry = self.telemetry
        try:
            graph_ctx = bind_telemetry_context(
                job_id=claim.job.job_id,
                run_id=claim.job.run_id,
                stage="graph_execute",
            )
        except Exception:
            graph_ctx = None

        def _run() -> JobExecutionOutcome:
            if graph_ctx is not None:
                graph_ctx.__enter__()
            graph = self.graph_factory()
            config = self._config(
                claim.job.thread_id
            )
            snapshot = graph.get_state(config)
            values = dict(
                getattr(snapshot, "values", {}) or {}
            )
            next_nodes = tuple(
                getattr(snapshot, "next", ()) or ()
            )
            interrupts = self._interrupts(snapshot)

            heartbeat.raise_if_unhealthy()

            if values:
                checkpoint_job_id = values.get(
                    "job_id"
                )
                checkpoint_run_id = values.get(
                    "run_id"
                )
                if (
                    checkpoint_job_id
                    != claim.job.job_id
                    or checkpoint_run_id
                    != claim.job.run_id
                ):
                    raise JobGraphStateError(
                        "thread_id 已绑定其他 checkpoint："
                        f"checkpoint_job_id={checkpoint_job_id!r}, "
                        f"checkpoint_run_id={checkpoint_run_id!r}"
                    )

            binding = claim.workspace_binding
            if binding is None or binding.status != "ready":
                raise JobGraphStateError(
                    "workspace binding 未 ready"
                )

            workspace_update = (
                build_workspace_state_update(
                    state=values,
                    new_binding=binding,
                )
                if values
                else {}
            )

            if values and not next_nodes:
                return JobExecutionOutcome(
                    status="succeeded",
                    result=_result_summary(
                        claim=claim,
                        state=values,
                    ),
                    artifact_records=_artifact_records(
                        values,
                        expected_run_id=claim.job.run_id,
                    ),
                    checkpoint_state=values,
                )

            if interrupts:
                if claim.resume_request is None:
                    return JobExecutionOutcome(
                        status="waiting_for_input",
                        result=_result_summary(
                            claim=claim,
                            state=values,
                        ),
                        interrupts=interrupts,
                        artifact_records=_artifact_records(
                            values,
                            expected_run_id=claim.job.run_id,
                        ),
                        checkpoint_state=values,
                    )

                current_nodes = {
                    item.node for item in interrupts
                }
                expected_node = (
                    claim.resume_request.expected_node
                )
                if expected_node not in current_nodes:
                    return JobExecutionOutcome(
                        status="waiting_for_input",
                        result=_result_summary(
                            claim=claim,
                            state=values,
                        ),
                        interrupts=interrupts,
                        artifact_records=_artifact_records(
                            values,
                            expected_run_id=claim.job.run_id,
                        ),
                        checkpoint_state=values,
                    )

                graph_input: (
                    dict[str, Any] | Command | None
                ) = Command(
                    resume=claim.resume_request.value,
                    update=workspace_update,
                )
            elif values:
                graph_input = Command(
                    update=workspace_update
                )
            else:
                if claim.resume_request is not None:
                    raise JobGraphStateError(
                        "没有 Graph checkpoint，"
                        "却存在 pending resume"
                    )
                graph_input = self._initial_state(claim)

            _graph_span = None
            try:
                with telemetry.span(
                    "graph.execute",
                    attributes={
                        "graph": "paper_reproduction",
                        "thread_id": claim.job.thread_id,
                    },
                ) as _graph_span_ref:
                    _graph_span = _graph_span_ref
                    for _chunk in graph.stream(
                        graph_input,
                        config=config,
                        stream_mode="updates",
                    ):
                        try:
                            if isinstance(_chunk, dict):
                                for node_name in _chunk.keys():
                                    node_str = str(node_name)
                                    try:
                                        with bind_telemetry_context(
                                            graph_node=node_str,
                                            stage="graph_node",
                                        ):
                                            increment_counter_safe(
                                                telemetry,
                                                "paper_copilot_nodes_entered_total",
                                                attributes={
                                                    "node": node_str,
                                                    "outcome": "succeeded",
                                                },
                                            )
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        heartbeat.raise_if_unhealthy()
            except Exception as exc:
                try:
                    if _graph_span is not None:
                        record_span_exception_safe(_graph_span, exc)
                except Exception:
                    pass
                raise

            heartbeat.raise_if_unhealthy()
            final_snapshot = graph.get_state(config)
            final_values = dict(
                getattr(
                    final_snapshot,
                    "values",
                    {},
                )
                or {}
            )
            final_next = tuple(
                getattr(
                    final_snapshot,
                    "next",
                    (),
                )
                or ()
            )
            final_interrupts = self._interrupts(
                final_snapshot
            )

            if final_interrupts:
                return JobExecutionOutcome(
                    status="waiting_for_input",
                    result=_result_summary(
                        claim=claim,
                        state=final_values,
                    ),
                    interrupts=final_interrupts,
                    artifact_records=_artifact_records(
                        final_values,
                        expected_run_id=claim.job.run_id,
                    ),
                    checkpoint_state=final_values,
                )

            if not final_next:
                return JobExecutionOutcome(
                    status="succeeded",
                    result=_result_summary(
                        claim=claim,
                        state=final_values,
                    ),
                    artifact_records=_artifact_records(
                        final_values,
                        expected_run_id=claim.job.run_id,
                    ),
                    checkpoint_state=final_values,
                )

            raise JobGraphStateError(
                "Graph stream 已返回，但 checkpoint "
                f"仍有 next={final_next} 且没有 interrupt"
            )

        try:
            with telemetry.span(
                "graph.run",
                attributes={"graph": "paper_reproduction"},
            ) as _outer_span:
                try:
                    return _run()
                except Exception as exc:
                    try:
                        record_span_exception_safe(_outer_span, exc)
                    except Exception:
                        pass
                    raise
        finally:
            if graph_ctx is not None:
                try:
                    graph_ctx.__exit__(None, None, None)
                except Exception:
                    pass
