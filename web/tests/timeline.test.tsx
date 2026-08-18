import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConversationTimeline } from "../src/components/ConversationTimeline";
import { SessionSidebar } from "../src/components/SessionSidebar";
import type { JobView, TimelineResponse } from "../src/api/types";

const job: JobView = {
  job_id: "job-1",
  thread_id: "thread-1",
  run_id: "run-1",
  status: "running",
  version: 1,
  attempt_count: 1,
  max_attempts: 3,
  wait_generation: 0,
  interrupts: [],
  cancel_requested: false,
  cancellation_reason: null,
  result: null,
  error: null,
  reconciliation: null,
  input: {
    paper_name: "PSTNet.pdf",
    repo_name: "PST-Convolution",
    experiment_goal: "reproduce main result",
    execution_profile_id: "local",
  },
  allowed_operations: [],
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:01:00Z",
};

describe("conversation projection", () => {
  it("renders timeline content as text", () => {
    const timeline: TimelineResponse = {
      job,
      last_event_id: 1,
      items: [{
        item_id: "event:1",
        role: "assistant",
        kind: "progress",
        title: "Workspace ready",
        content: "Agent started analysis.",
        created_at: "2026-08-01T00:00:10Z",
        event_id: 1,
        operation: null,
        interrupt: null,
      }],
    };

    render(
      <ConversationTimeline
        timeline={timeline}
        error={null}
        onMutation={async () => undefined}
      />,
    );

    expect(screen.getByText("Workspace ready")).toBeTruthy();
    expect(screen.getByText("Agent started analysis.")).toBeTruthy();
  });

  it("filters session history without changing server state", () => {
    const second = {
      ...job,
      job_id: "job-2",
      input: {
        ...job.input,
        paper_name: "Other.pdf",
        experiment_goal: "different target",
      },
    };
    const { container } = render(
      <SessionSidebar
        jobs={[job, second]}
        selectedId="job-1"
        onSelect={() => undefined}
        onNew={() => undefined}
      />,
    );

    fireEvent.change(screen.getByLabelText("Search sessions"), {
      target: { value: "PSTNet" },
    });

    const sidebar = container.querySelector(".session-sidebar")!;
    expect(sidebar.textContent).includes("PSTNet.pdf");
    expect(sidebar.textContent).not.includes("Other.pdf");
  });
});
