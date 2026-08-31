import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import type {
  ArtifactPreview,
  ArtifactView,
  JobStatus,
  JobView,
} from "../api/types";
import { ArtifactPreviewPanel } from "./ArtifactPreviewPanel";
import { StatusBadge } from "./StatusBadge";

type Tab = "overview" | "artifacts" | "logs";
type CopyStatus = "idle" | "copied" | "failed";

const ACTIVE_STATUSES = new Set<JobStatus>([
  "queued",
  "running",
  "waiting_for_input",
  "cancelling",
]);

type Props = {
  job: JobView | null;
  onMutation: (action: () => Promise<unknown>) => Promise<void>;
};

export function RunContextPanel({ job, onMutation }: Props) {
  const [tab, setTab] = useState<Tab>("overview");
  const [artifacts, setArtifacts] = useState<ArtifactView[]>([]);
  const [preview, setPreview] = useState<ArtifactPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [log, setLog] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [copyStatus, setCopyStatus] = useState<CopyStatus>("idle");
  const currentJobId = useRef(job?.job_id);

  // 切换 Job 时不能继续显示上一个 Job 的预览或错误。
  useEffect(() => {
    currentJobId.current = job?.job_id;
    setArtifacts([]);
    setPreview(null);
    setPreviewLoading(false);
    setLog("");
    setError(null);
    setCopyStatus("idle");
  }, [job?.job_id]);

  useEffect(() => {
    if (!job || tab !== "artifacts") return;
    let disposed = false;
    setError(null);
    void api.artifacts(job.job_id)
      .then((items) => {
        if (!disposed) setArtifacts(items);
      })
      .catch((caught) => {
        if (!disposed) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Artifact 加载失败",
          );
        }
      });
    return () => {
      disposed = true;
    };
  }, [job?.job_id, tab]);

  useEffect(() => {
    if (!job || tab !== "logs") return;
    let disposed = false;
    async function refreshLog() {
      try {
        const result = await api.log(job!.job_id);
        if (!disposed) setLog(result.content);
      } catch (caught) {
        if (!disposed) {
          setError(
            caught instanceof Error
              ? caught.message
              : "日志加载失败",
          );
        }
      }
    }

    void refreshLog();
    const timer = ACTIVE_STATUSES.has(job.status)
      ? window.setInterval(() => void refreshLog(), 2000)
      : null;
    return () => {
      disposed = true;
      if (timer !== null) window.clearInterval(timer);
    };
  }, [job?.job_id, job?.status, tab]);

  async function openPreview(artifact: ArtifactView) {
    if (!job) return;
    const requestedJobId = job.job_id;
    setPreviewLoading(true);
    setError(null);
    try {
      const result = await api.artifactPreview(
        requestedJobId,
        artifact.artifact_id,
      );
      if (currentJobId.current === requestedJobId) {
        setPreview(result);
      }
    } catch (caught) {
      if (currentJobId.current === requestedJobId) {
        setError(
          caught instanceof Error
            ? caught.message
            : "Artifact 预览失败",
        );
      }
    } finally {
      if (currentJobId.current === requestedJobId) {
        setPreviewLoading(false);
      }
    }
  }

  async function copyJobId() {
    if (!job) return;
    const requestedJobId = job.job_id;
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("Clipboard API unavailable");
      }
      await navigator.clipboard.writeText(requestedJobId);
      if (currentJobId.current === requestedJobId) {
        setCopyStatus("copied");
      }
    } catch {
      if (currentJobId.current === requestedJobId) {
        setCopyStatus("failed");
      }
    }
  }

  if (!job) {
    return (
      <aside className="run-context">
        <p>Select a session.</p>
      </aside>
    );
  }

  const canCancel = job.allowed_operations.some(
    (item) => item.kind === "cancel",
  );
  const operatorOperation = job.allowed_operations.find(
    (item) => item.kind === "operator_reconciliation_required",
  );

  return (
    <aside className="run-context">
      <header>
        <p className="eyebrow">Run context</p>
        <StatusBadge status={job.status} />
      </header>
      <nav className="context-tabs" aria-label="Run context">
        {(["overview", "artifacts", "logs"] as Tab[]).map((name) => (
          <button
            key={name}
            aria-pressed={tab === name}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </nav>

      {error && (
        <p className="inline-error" role="alert">{error}</p>
      )}

      {tab === "overview" && (
        <dl className="run-overview">
          <dt>Paper</dt><dd>{job.input.paper_name}</dd>
          <dt>Repository</dt><dd>{job.input.repo_name}</dd>
          <dt>Profile</dt><dd>{job.input.execution_profile_id}</dd>
          <dt>Attempt</dt><dd>{job.attempt_count} / {job.max_attempts}</dd>
          <dt>Job ID</dt>
          <dd className="run-identity">
            <code title={job.job_id}>{job.job_id}</code>
            <button
              type="button"
              className="copy-identity-button"
              aria-label={
                copyStatus === "copied"
                  ? "Job ID copied"
                  : "Copy Job ID"
              }
              onClick={() => void copyJobId()}
            >
              {copyStatus === "copied" ? "Copied" : "Copy"}
            </button>
          </dd>
          <dt>Thread ID</dt>
          <dd className="run-identity">
            <code title={job.thread_id}>{job.thread_id}</code>
          </dd>
          <dt>Run ID</dt>
          <dd className="run-identity">
            <code title={job.run_id}>{job.run_id}</code>
          </dd>
          {copyStatus === "failed" && (
            <>
              <dt className="identity-status-label">Copy status</dt>
              <dd className="identity-copy-error" role="status">
                Clipboard unavailable. Copy the Job ID manually.
              </dd>
            </>
          )}
        </dl>
      )}

      {tab === "artifacts" && (
        <section className="artifact-section">
          <div className="artifact-toolbar">
            <strong>{artifacts.length} artifacts</strong>
            <a
              className="artifact-export-link"
              href={api.jobExportUrl(job.job_id)}
            >
              Export job (.zip)
            </a>
          </div>

          {preview && (
            <ArtifactPreviewPanel
              preview={preview}
              onClose={() => setPreview(null)}
            />
          )}

          {artifacts.length === 0 ? (
            <p>No artifacts published yet.</p>
          ) : (
            <ul className="artifact-list">
              {artifacts.map((artifact) => (
                <li key={artifact.artifact_id}>
                  <strong>{artifact.relative_path}</strong>
                  <small>
                    {artifact.media_type} / {artifact.size_bytes} bytes
                  </small>
                  <div className="artifact-actions">
                    {artifact.preview_supported && (
                      <button
                        type="button"
                        disabled={previewLoading}
                        onClick={() => void openPreview(artifact)}
                      >
                        Preview
                      </button>
                    )}
                    <a
                      href={api.artifactDownloadUrl(
                        job.job_id,
                        artifact.artifact_id,
                      )}
                    >
                      Download
                    </a>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === "logs" && (
        <pre className="log-tail">{log || "No log output yet."}</pre>
      )}

      {operatorOperation && (
        <p className="operator-note">{operatorOperation.detail}</p>
      )}
      {canCancel && (
        <button
          className="danger-action"
          onClick={() => void onMutation(() => api.cancel(job))}
        >
          Cancel session
        </button>
      )}
    </aside>
  );
}
