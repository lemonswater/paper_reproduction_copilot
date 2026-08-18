import { startTransition, useEffect, useState } from "react";

import { api, ApiClientError } from "./api/client";
import { ConversationTimeline } from "./components/ConversationTimeline";
import { NewSessionPanel } from "./components/NewSessionPanel";
import { RunContextPanel } from "./components/RunContextPanel";
import { SessionSidebar } from "./components/SessionSidebar";
import type { JobView, TimelineResponse, UiConfig } from "./api/types";
import { useJobStream } from "./hooks/useJobStream";

export default function App() {
  const [jobs, setJobs] = useState<JobView[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(
    window.location.hash.slice(1) || null,
  );
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newSessionOpen, setNewSessionOpen] = useState(false);
  const [uiConfig, setUiConfig] = useState<UiConfig | null>(null);

  async function refreshJobs() {
    try {
      const next = await api.listJobs();
      startTransition(() => {
        setJobs(next);
        setSelectedId((current) => current ?? next[0]?.job_id ?? null);
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "任务列表加载失败");
    }
  }

  async function refreshTimeline() {
    if (!selectedId) return;
    try {
      const next = await api.timeline(selectedId);
      startTransition(() => setTimeline(next));
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "加载任务失败");
    }
  }

  useEffect(() => {
    void refreshJobs();

    void api.config()
      .then(setUiConfig)
      .catch((caught) => {
        setError(
          caught instanceof Error
            ? caught.message
            : "UI 配置加载失败",
        );
      });

    const restoreFromHash = () => {
      setSelectedId(window.location.hash.slice(1) || null);
    };
    window.addEventListener("hashchange", restoreFromHash);
    return () => window.removeEventListener("hashchange", restoreFromHash);
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setTimeline(null);
      return;
    }
    window.history.replaceState(null, "", `#${selectedId}`);
    setTimeline(null);
    void refreshTimeline();
  }, [selectedId]);

  useJobStream(
    selectedId,
    timeline?.job.job_id === selectedId ? timeline.last_event_id : 0,
    () => {
      void Promise.all([refreshTimeline(), refreshJobs()]);
    },
  );

  async function runMutation(action: () => Promise<unknown>) {
    try {
      await action();
      await Promise.all([refreshTimeline(), refreshJobs()]);
    } catch (caught) {
      if (caught instanceof ApiClientError && caught.status === 409) {
        await refreshTimeline();
        setError("状态已经变化，页面已刷新，请重新确认当前操作。");
        return;
      }
      setError(caught instanceof Error ? caught.message : "操作失败");
    }
  }

  return (
    <main className="workspace-shell">
      <SessionSidebar
        jobs={jobs}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onNew={() => setNewSessionOpen(true)}
      />
      <ConversationTimeline
        timeline={timeline}
        error={error}
        onMutation={runMutation}
        chatEnabled={uiConfig?.chat_enabled ?? false}
      />
      <RunContextPanel
        job={timeline?.job ?? null}
        onMutation={runMutation}
      />
      {newSessionOpen && (
        <NewSessionPanel
          onClose={() => setNewSessionOpen(false)}
          onCreated={(job) => {
            setSelectedId(job.job_id);
            setNewSessionOpen(false);
            void refreshJobs();
          }}
        />
      )}
    </main>
  );
}
