import { useDeferredValue, useState } from "react";

import type { JobView } from "../api/types";
import { StatusBadge } from "./StatusBadge";

type Props = {
  jobs: JobView[];
  selectedId: string | null;
  onSelect: (jobId: string) => void;
  onNew: () => void;
};

export function SessionSidebar({ jobs, selectedId, onSelect, onNew }: Props) {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());
  const visible = jobs.filter((job) =>
    [job.input.experiment_goal, job.input.paper_name, job.input.repo_name]
      .join(" ")
      .toLowerCase()
      .includes(deferredQuery),
  );

  return (
    <aside className="session-sidebar">
      <header>
        <p className="eyebrow">Research workspace</p>
        <h1>Reproduction sessions</h1>
        <button className="primary-action" onClick={onNew}>
          New session
        </button>
      </header>
      <input
        aria-label="Search sessions"
        placeholder="Search paper or goal"
        value={query}
        onChange={(event) => setQuery(event.currentTarget.value)}
      />
      <nav aria-label="Reproduction sessions">
        {visible.map((job) => (
          <button
            key={job.job_id}
            className={job.job_id === selectedId ? "session active" : "session"}
            onClick={() => onSelect(job.job_id)}
          >
            <span>{job.input.paper_name}</span>
            <small>{job.input.experiment_goal}</small>
            <StatusBadge status={job.status} />
          </button>
        ))}
      </nav>
    </aside>
  );
}
