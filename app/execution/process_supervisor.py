from __future__ import annotations

import os
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import psutil

from app.execution.cancellation import (
    atomic_write_json,
    read_cancel_request,
    write_runtime_record,
)
from app.schemas import (
    ExecutionResult,
    ProcessRecord,
    ResourceBudget,
    ResourceUsage,
)
from app.secrets.redaction import (
    SecretRedactor,
    StreamingSecretRedactor,
)

SENSITIVE_ARG_NAMES = {
    "--api-key",
    "--api_key",
    "--token",
    "--password",
    "--secret",
}


def _redact_command_tokens(tokens: list[str]) -> list[str]:
    """Process Record 保留命令结构，但隐藏常见 secret 参数值。"""

    result: list[str] = []
    redact_next = False
    for token in tokens:
        lowered = token.lower()
        if redact_next:
            result.append("<redacted>")
            redact_next = False
            continue

        if lowered in SENSITIVE_ARG_NAMES:
            result.append(token)
            redact_next = True
            continue

        matched_assignment = False
        for name in SENSITIVE_ARG_NAMES:
            prefix = name + "="
            if lowered.startswith(prefix):
                result.append(token[: len(prefix)] + "<redacted>")
                matched_assignment = True
                break
        if not matched_assignment:
            result.append(token)

    return result


def _process_group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # PGID 存在但当前用户无法发信号，也不能假装已经结束。
        return True
    return True


def _terminate_process_group_final(
    *,
    process: subprocess.Popen[bytes],
    pgid: int,
    selector: selectors.BaseSelector,
    sinks: dict[str, BoundedLogSink],
    combined_sink: BoundedLogSink,
    grace_seconds: float,
) -> bool:
    """
    即使 group leader 已经退出，也检查并终止仍存活的 PGID。

    返回 True 表示最终使用了 SIGKILL。
    """

    if not _process_group_exists(pgid):
        return False

    _signal_process_group(pgid, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while _process_group_exists(pgid) and time.monotonic() < deadline:
        _drain_ready_streams(
            selector=selector,
            sinks=sinks,
            combined_sink=combined_sink,
            timeout=0.05,
        )
        if process.poll() is None:
            process.poll()

    if not _process_group_exists(pgid):
        return False

    _signal_process_group(pgid, signal.SIGKILL)
    return True

@dataclass(frozen=True)
class SupervisedExecutionRequest:
    host_command: list[str]
    cwd: Path
    env: dict[str, str]
    run_dir: Path
    action_id: str
    stage: str
    profile_id: str
    backend: str
    budget: ResourceBudget
    execution_id: str


class ProcessTreeSampler:
    """
    采样 root process 及其递归子进程。

    CPU 和 write bytes 按 (pid, create_time) 保存历史最大值，避免短命子进程
    退出后累计量突然下降，也避免 PID 复用混在同一条记录里。
    """

    def __init__(self) -> None:
        self.peak_rss_bytes = 0
        self.peak_process_count = 0
        self._cpu_by_identity: dict[
            tuple[int, float], float
        ] = {}
        self._write_by_identity: dict[
            tuple[int, float], int
        ] = {}
        self.samples = 0

    def sample(self, root_pid: int) -> ResourceUsage:
        try:
            root = psutil.Process(root_pid)
            processes = [root, *root.children(recursive=True)]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            processes = []

        current_rss = 0
        current_count = 0
        for process in processes:
            try:
                identity = (
                    process.pid,
                    process.create_time(),
                )
                current_rss += process.memory_info().rss
                current_count += 1

                cpu = process.cpu_times()
                cpu_seconds = float(cpu.user + cpu.system)
                self._cpu_by_identity[identity] = max(
                    self._cpu_by_identity.get(identity, 0.0),
                    cpu_seconds,
                )

                try:
                    write_bytes = int(
                        process.io_counters().write_bytes
                    )
                except (AttributeError, NotImplementedError):
                    write_bytes = 0
                self._write_by_identity[identity] = max(
                    self._write_by_identity.get(identity, 0),
                    write_bytes,
                )
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

        self.peak_rss_bytes = max(
            self.peak_rss_bytes,
            current_rss,
        )
        self.peak_process_count = max(
            self.peak_process_count,
            current_count,
        )
        self.samples += 1

        return ResourceUsage(
            peak_rss_bytes=self.peak_rss_bytes,
            peak_process_count=self.peak_process_count,
            total_cpu_seconds=sum(self._cpu_by_identity.values()),
            total_write_bytes=sum(
                self._write_by_identity.values()
            ),
            peak_gpu_memory_bytes=None,
            samples=self.samples,
        )


def budget_end_reason(
    usage: ResourceUsage,
    budget: ResourceBudget,
) -> str | None:
    if (
        budget.max_memory_bytes is not None
        and usage.peak_rss_bytes > budget.max_memory_bytes
    ):
        return "memory_limit"

    if usage.peak_process_count > budget.max_processes:
        return "process_limit"

    if (
        budget.max_cpu_seconds is not None
        and usage.total_cpu_seconds > budget.max_cpu_seconds
    ):
        return "cpu_limit"

    if (
        budget.max_write_bytes is not None
        and usage.total_write_bytes > budget.max_write_bytes
    ):
        return "write_limit"

    return None

class BoundedLogSink:
    """统计原始字节，但只持久化脱敏后的有界内容。"""

    def __init__(
        self,
        *,
        path: Path,
        max_file_bytes: int,
        max_preview_bytes: int,
        stream_redactor: StreamingSecretRedactor | None = None,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.max_file_bytes = max_file_bytes
        self.max_preview_bytes = max_preview_bytes
        self.bytes_seen = 0
        self.bytes_written = 0
        self.preview = bytearray()
        self.truncated = False
        self._redactor = stream_redactor
        self._file = path.open("wb")

    def _write_safe(self, data: bytes) -> None:
        if not data:
            return
        preview_remaining = (
            self.max_preview_bytes - len(self.preview)
        )
        if preview_remaining > 0:
            self.preview.extend(data[:preview_remaining])

        file_remaining = self.max_file_bytes - self.bytes_written
        if file_remaining > 0:
            chunk = data[:file_remaining]
            self._file.write(chunk)
            self.bytes_written += len(chunk)

    def consume(self, data: bytes) -> None:
        if not data:
            return
        self.bytes_seen += len(data)
        safe = (
            self._redactor.feed(data)
            if self._redactor is not None
            else data
        )
        self._write_safe(safe)
        if self.bytes_seen > self.max_file_bytes:
            self.truncated = True

    def close(self) -> None:
        if self._file.closed:
            return
        if self._redactor is not None:
            self._write_safe(self._redactor.flush())
        self._file.flush()
        os.fsync(self._file.fileno())
        self._file.close()

    def preview_text(self) -> str:
        return bytes(self.preview).decode(
            "utf-8",
            errors="replace",
        )

def _signal_process_group(pgid: int, sig: int) -> None:
    """只接受 Supervisor 自己创建并记录的 PGID。"""

    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        return


def _drain_ready_streams(
    *,
    selector: selectors.BaseSelector,
    sinks: dict[str, BoundedLogSink],
    combined_sink: BoundedLogSink,
    timeout: float,
) -> None:
    for key, _ in selector.select(timeout):
        stream_name = str(key.data)
        try:
            data = os.read(key.fd, 64 * 1024)
        except BlockingIOError:
            continue

        if not data:
            try:
                selector.unregister(key.fileobj)
            except KeyError:
                pass
            continue

        sinks[stream_name].consume(data)
        combined_sink.consume(
            f"[{stream_name}]\n".encode() + data
        )

def _terminate_process_group(
    *,
    process: subprocess.Popen[bytes],
    pgid: int,
    selector: selectors.BaseSelector,
    sinks: dict[str, BoundedLogSink],
    combined_sink: BoundedLogSink,
    grace_seconds: float,
) -> bool:
    """
    先 SIGTERM，继续 drain 日志；宽限期后仍存活则 SIGKILL。

    返回 True 表示使用过 hard kill。
    """

    if process.poll() is not None:
        return False

    _signal_process_group(pgid, signal.SIGTERM)
    deadline = time.monotonic() + grace_seconds
    while process.poll() is None and time.monotonic() < deadline:
        _drain_ready_streams(
            selector=selector,
            sinks=sinks,
            combined_sink=combined_sink,
            timeout=0.05,
        )

    if process.poll() is not None:
        return False

    _signal_process_group(pgid, signal.SIGKILL)
    return True

class ProcessSupervisor:
    """在当前 Agent 进程中同步监管一个独立进程组。"""

    def execute(
        self,
        request: SupervisedExecutionRequest,
        *,
        inherited_env_keys: list[str] | None = None,
        profile_env_keys: list[str] | None = None,
        action_env_keys: list[str] | None = None,
        secret_env_keys: list[str] | None = None,
        redactor: SecretRedactor | None = None,
    ) -> ExecutionResult:
        if os.name != "posix":
            raise RuntimeError(
                "Phase 16 ProcessSupervisor 第一版只支持 POSIX"
            )
        if not request.host_command:
            raise ValueError("host_command 不能为空")
        if not request.stage.replace("_", "").isalnum():
            raise ValueError(f"无效执行 stage：{request.stage}")

        execution_id = request.execution_id
        run_root = request.run_dir.resolve()
        attempt_dir = (
            run_root
            / "execution"
            / "attempts"
            / execution_id
        ).resolve()
        if run_root not in attempt_dir.parents:
            raise ValueError("execution attempt 目录逃逸当前 run")
        attempt_dir.mkdir(parents=True, exist_ok=False)

        stdout_path = attempt_dir / "stdout.log"
        stderr_path = attempt_dir / "stderr.log"
        combined_path = attempt_dir / "combined.log"
        process_record_path = attempt_dir / "process_record.json"

        stdout_sink = BoundedLogSink(
            path=stdout_path,
            max_file_bytes=(
                request.budget.max_log_bytes_per_stream
            ),
            max_preview_bytes=request.budget.max_preview_bytes,
            stream_redactor=(
                redactor.stream() if redactor else None
            ),
        )
        stderr_sink = BoundedLogSink(
            path=stderr_path,
            max_file_bytes=(
                request.budget.max_log_bytes_per_stream
            ),
            max_preview_bytes=request.budget.max_preview_bytes,
            stream_redactor=(
                redactor.stream() if redactor else None
            ),
        )
        combined_sink = BoundedLogSink(
            path=combined_path,
            max_file_bytes=(
                request.budget.max_log_bytes_per_stream * 2
            ),
            max_preview_bytes=(
                request.budget.max_preview_bytes * 2
            ),
            stream_redactor=(
                redactor.stream() if redactor else None
            ),
        )
        sinks = {
            "stdout": stdout_sink,
            "stderr": stderr_sink,
        }

        started_wall = time.monotonic()
        started_at = datetime.now(timezone.utc).isoformat()
        record = ProcessRecord(
            execution_id=execution_id,
            action_id=request.action_id,
            stage=request.stage,
            profile_id=request.profile_id,
            backend=request.backend,
            host_command_preview=_redact_command_tokens(
                request.host_command
            ),
            cwd=str(request.cwd),
            started_at=started_at,
            status="starting",
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            combined_log_path=str(combined_path),
            resource_budget=request.budget,
            inherited_env_keys=sorted(
                inherited_env_keys or []
            ),
            profile_env_keys=sorted(profile_env_keys or []),
            action_env_keys=sorted(action_env_keys or []),
            secret_env_keys=sorted(secret_env_keys or []),
        )
        write_runtime_record(
            run_dir=run_root,
            execution_id=execution_id,
            payload=record.model_dump(),
        )

        process: subprocess.Popen[bytes] | None = None
        selector = selectors.DefaultSelector()
        sampler = ProcessTreeSampler()
        usage = ResourceUsage()
        end_reason = "supervisor_error"
        cancellation_reason: str | None = None
        hard_kill_used = False
        termination_signal: int | None = None

        try:
            process = subprocess.Popen(
                request.host_command,
                cwd=str(request.cwd),
                env=request.env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                bufsize=0,
                shell=False,
                close_fds=True,
                start_new_session=True,
            )
            assert process.stdout is not None
            assert process.stderr is not None

            os.set_blocking(process.stdout.fileno(), False)
            os.set_blocking(process.stderr.fileno(), False)
            selector.register(
                process.stdout,
                selectors.EVENT_READ,
                data="stdout",
            )
            selector.register(
                process.stderr,
                selectors.EVENT_READ,
                data="stderr",
            )

            pgid = os.getpgid(process.pid)
            create_time = psutil.Process(
                process.pid
            ).create_time()
            record = record.model_copy(
                update={
                    "pid": process.pid,
                    "pgid": pgid,
                    "process_create_time": create_time,
                    "status": "running",
                }
            )
            write_runtime_record(
                run_dir=run_root,
                execution_id=execution_id,
                payload=record.model_dump(),
            )

            parent_exit_seen_at: float | None = None
            while True:
                _drain_ready_streams(
                    selector=selector,
                    sinks=sinks,
                    combined_sink=combined_sink,
                    timeout=(
                        request.budget.sample_interval_seconds
                    ),
                )

                returncode = process.poll()
                group_alive = _process_group_exists(pgid)

                if returncode is not None:
                    if not group_alive:
                        end_reason = "exited"
                        break

                    if parent_exit_seen_at is None:
                        parent_exit_seen_at = time.monotonic()
                    elif (
                        time.monotonic() - parent_exit_seen_at
                        >= request.budget.terminate_grace_seconds
                    ):
                        end_reason = "orphan_cleanup"
                        break

                if returncode is None:
                    usage = sampler.sample(process.pid)
                    limited = budget_end_reason(
                        usage,
                        request.budget,
                    )
                    if limited is not None:
                        end_reason = limited
                        break

                cancel_request = read_cancel_request(
                    run_dir=run_root,
                    execution_id=execution_id,
                )
                if cancel_request is not None:
                    end_reason = "cancelled"
                    cancellation_reason = cancel_request.reason
                    break

                elapsed = time.monotonic() - started_wall
                if (
                    elapsed
                    > request.budget.max_wall_time_seconds
                ):
                    end_reason = "timeout"
                    break

            if (
                end_reason != "exited"
                and _process_group_exists(pgid)
            ):
                record = record.model_copy(
                    update={"status": "terminating"}
                )
                write_runtime_record(
                    run_dir=run_root,
                    execution_id=execution_id,
                    payload=record.model_dump(),
                )
                hard_kill_used = _terminate_process_group_final(
                    process=process,
                    pgid=pgid,
                    selector=selector,
                    sinks=sinks,
                    combined_sink=combined_sink,
                    grace_seconds=(
                        request.budget.terminate_grace_seconds
                    ),
                )
                termination_signal = (
                    signal.SIGKILL
                    if hard_kill_used
                    else signal.SIGTERM
                )

            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                if _process_group_exists(pgid):
                    _signal_process_group(pgid, signal.SIGKILL)
                    hard_kill_used = True
                    termination_signal = signal.SIGKILL
                process.wait(timeout=2)

            # 进程结束后再短暂 drain，拿到 pipe 中已经产生的尾部日志。
            drain_deadline = time.monotonic() + 1.0
            while selector.get_map() and time.monotonic() < drain_deadline:
                _drain_ready_streams(
                    selector=selector,
                    sinks=sinks,
                    combined_sink=combined_sink,
                    timeout=0.05,
                )

            usage = sampler.sample(process.pid)

        except KeyboardInterrupt:
            end_reason = "interrupted"
            cancellation_reason = "Agent received KeyboardInterrupt"
            if process is not None and process.pid:
                try:
                    pgid = os.getpgid(process.pid)
                except ProcessLookupError:
                    pgid = process.pid
                hard_kill_used = _terminate_process_group_final(
                    process=process,
                    pgid=pgid,
                    selector=selector,
                    sinks=sinks,
                    combined_sink=combined_sink,
                    grace_seconds=(
                        request.budget.terminate_grace_seconds
                    ),
                )
                termination_signal = (
                    signal.SIGKILL
                    if hard_kill_used
                    else signal.SIGTERM
                )

        except OSError as exc:
            end_reason = "launch_error"
            error_bytes = str(exc).encode(
                "utf-8",
                errors="replace",
            )
            stderr_sink.consume(error_bytes)
            combined_sink.consume(b"[stderr]\n" + error_bytes)

        except Exception as exc:  # noqa: BLE001
            # Supervisor 自己失败也必须先清理已启动的进程组。
            end_reason = "supervisor_error"
            error_bytes = (
                f"{type(exc).__name__}: {exc}"
            ).encode("utf-8", errors="replace")
            stderr_sink.consume(error_bytes)
            combined_sink.consume(b"[stderr]\n" + error_bytes)

            if process is not None and process.poll() is None:
                try:
                    pgid = os.getpgid(process.pid)
                except ProcessLookupError:
                    pgid = process.pid
                hard_kill_used = _terminate_process_group_final(
                    process=process,
                    pgid=pgid,
                    selector=selector,
                    sinks=sinks,
                    combined_sink=combined_sink,
                    grace_seconds=(
                        request.budget.terminate_grace_seconds
                    ),
                )
                termination_signal = (
                    signal.SIGKILL
                    if hard_kill_used
                    else signal.SIGTERM
                )

        finally:
            selector.close()
            for sink in (
                stdout_sink,
                stderr_sink,
                combined_sink,
            ):
                sink.close()

        finished_at = datetime.now(timezone.utc).isoformat()
        duration = time.monotonic() - started_wall
        returncode = (
            process.returncode
            if process is not None
            else None
        )
        if process is not None and usage.samples == 0:
            usage = sampler.sample(process.pid)

        record = record.model_copy(
            update={
                "status": "finished",
                "finished_at": finished_at,
                "duration_seconds": duration,
                "end_reason": end_reason,
                "returncode": returncode,
                "termination_signal": termination_signal,
                "hard_kill_used": hard_kill_used,
                "stdout_bytes_seen": stdout_sink.bytes_seen,
                "stderr_bytes_seen": stderr_sink.bytes_seen,
                "stdout_bytes_written": stdout_sink.bytes_written,
                "stderr_bytes_written": stderr_sink.bytes_written,
                "stdout_truncated": stdout_sink.truncated,
                "stderr_truncated": stderr_sink.truncated,
                "cancellation_requested": (
                    end_reason in {"cancelled", "interrupted"}
                ),
                "cancellation_reason": cancellation_reason,
                "resource_usage": usage,
            }
        )

        atomic_write_json(
            process_record_path,
            record.model_dump(),
        )
        write_runtime_record(
            run_dir=run_root,
            execution_id=execution_id,
            payload=record.model_dump(),
        )

        stdout_preview = stdout_sink.preview_text()
        stderr_preview = stderr_sink.preview_text()
        combined_preview = combined_sink.preview_text()
        ok = end_reason == "exited" and returncode == 0

        return ExecutionResult(
            ok=ok,
            returncode=returncode,
            end_reason=end_reason,
            stdout=stdout_preview,
            stderr=stderr_preview,
            combined_output=combined_preview,
            timeout=end_reason == "timeout",
            cancelled=end_reason in {"cancelled", "interrupted"},
            cancellation_reason=cancellation_reason,
            log_truncated=(
                stdout_sink.truncated
                or stderr_sink.truncated
                or combined_sink.truncated
            ),
            execution_id=execution_id,
            execution_profile_id=request.profile_id,
            execution_backend=request.backend,
            cwd=str(request.cwd),
            process_record_path=str(process_record_path),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            combined_log_path=str(combined_path),
            resource_usage=usage,
        )