import { useEffect, useEffectEvent } from "react";

const JOB_EVENT_TYPES = [
  "job_submitted",
  "job_claimed",
  "workspace_materializing",
  "workspace_ready",
  "workspace_materialization_failed",
  "job_waiting_for_input",
  "job_resume_queued",
  "job_retry_scheduled",
  "job_lease_requeued",
  "job_cancel_requested",
  "job_succeeded",
  "job_failed",
  "job_cancelled",
  "job_reconciliation_required",
  "job_reconciliation_resolved",
  "workspace_sealed",
  "workspace_portability_blocked",
] as const;

export function useJobStream(
  jobId: string | null,
  afterEventId: number,
  refresh: () => void,
) {
  const onServerUpdate = useEffectEvent(() => {
    refresh();
  });

  useEffect(() => {
    if (!jobId) return;

    const encoded = encodeURIComponent(jobId);
    const source = new EventSource(
      `/v1/jobs/${encoded}/events/stream?after=${afterEventId}`,
    );
    const handler = () => onServerUpdate();
    for (const type of JOB_EVENT_TYPES) {
      source.addEventListener(type, handler);
    }

    // 兜底处理未来新增但前端尚未登记的事件。
    const fallback = window.setInterval(() => onServerUpdate(), 15_000);
    return () => {
      window.clearInterval(fallback);
      for (const type of JOB_EVENT_TYPES) {
        source.removeEventListener(type, handler);
      }
      source.close();
    };
  }, [jobId, afterEventId]);
}
