import type { TimelineResponse } from "../api/types";
import { DecisionCard } from "./DecisionCard";
import { JobChatPanel } from "./JobChatPanel";

type Props = {
  timeline: TimelineResponse | null;
  error: string | null;
  onMutation: (
    action: () => Promise<unknown>
  ) => Promise<void>;
  chatEnabled?: boolean;
};

export function ConversationTimeline({
  timeline,
  error,
  onMutation,
  chatEnabled = false,
}: Props) {
  if (!timeline) {
    return (
      <section className="conversation empty-state">
        <p className="eyebrow">No session selected</p>
        <h2>Start with a paper and its repository.</h2>
      </section>
    );
  }

  return (
    <section className="conversation" aria-live="polite">
      <header className="conversation-header">
        <p className="eyebrow">{timeline.job.input.paper_name}</p>
        <h2>{timeline.job.input.experiment_goal}</h2>
      </header>
      {error && <div className="inline-error" role="alert">{error}</div>}
      <ol className="timeline-list">
        {timeline.items.map((item) => (
          <li
            key={item.item_id}
            className={`timeline-item ${item.role} ${item.kind}`}
          >
            <div className="message-meta">
              <span>{item.role === "user" ? "You" : "Agent"}</span>
              <time dateTime={item.created_at}>
                {new Date(item.created_at).toLocaleString()}
              </time>
            </div>
            <article>
              <h3>{item.title}</h3>
              <p>{item.content}</p>
              {item.kind === "decision" && item.operation && (
                <DecisionCard
                  job={timeline.job}
                  item={item}
                  onMutation={onMutation}
                />
              )}
            </article>
          </li>
        ))}
      </ol>
      {chatEnabled && (
        <JobChatPanel jobId={timeline.job.job_id} />
      )}
    </section>
  );
}
