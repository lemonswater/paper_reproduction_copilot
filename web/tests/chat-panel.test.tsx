import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../src/api/client";
import { JobChatPanel } from "../src/components/JobChatPanel";
import type { ChatMessage, ConversationMemory } from "../src/api/types";

const userMessage: ChatMessage = {
  message_id: "user-1",
  job_id: "job-1",
  sequence: 1,
  role: "user",
  content: "Why did it fail?",
  citations: [],
  reply_to: null,
  created_at: "2026-08-01T00:00:00Z",
};

const assistantMessage: ChatMessage = {
  message_id: "assistant-1",
  job_id: "job-1",
  sequence: 2,
  role: "assistant",
  content: "Dependency import failed.",
  citations: [{
    citation_id: "artifact:report:1",
    source_type: "artifact",
    label: "reports/final_report.md",
    artifact_id: "report",
    relative_path: "reports/final_report.md",
    artifact_sha256: "a".repeat(64),
    event_id: null,
    locator: "chunk 1",
    comparison_id: null,
    comparison_hash: null,
    base_job_id: null,
    target_job_id: null,
  }],
  reply_to: "user-1",
  created_at: "2026-08-01T00:00:01Z",
};

const memory: ConversationMemory = {
  job_id: "job-1",
  version: 2,
  covered_through_sequence: 200,
  summary: "Use CPU and validate with a small run first.",
  user_constraints: [{
    text: "Use CPU only.",
    source_sequences: [1],
  }],
  decisions: [],
  open_questions: [],
  citation_anchors: [],
  memory_sha256: "a".repeat(64),
  created_at: "2026-08-08T00:00:00+00:00",
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("JobChatPanel", () => {
  it("restores history and renders citation links", async () => {
    vi.spyOn(api, "chatMessages").mockResolvedValue([
      userMessage,
      assistantMessage,
    ]);
    vi.spyOn(api, "chatMemory").mockResolvedValue(null);

    render(<JobChatPanel jobId="job-1" />);

    expect(await screen.findByText("Dependency import failed.")).toBeTruthy();
    const link = screen.getByRole("link", {
      name: "reports/final_report.md",
    });
    expect(link.getAttribute("href")).toContain(
      "/v1/jobs/job-1/artifacts/report/content",
    );
  });

  it("submits one bounded question and appends the exchange", async () => {
    vi.spyOn(api, "chatMessages").mockResolvedValue([]);
    vi.spyOn(api, "chatMemory").mockResolvedValue(null);
    const ask = vi.spyOn(api, "askChat").mockResolvedValue({
      user_message: userMessage,
      assistant_message: assistantMessage,
      replayed: false,
      allowed_operations: [],
      memory: {
        enabled: true,
        available: false,
        version: null,
        covered_through_sequence: 0,
        degraded: false,
      },
    });

    render(<JobChatPanel jobId="job-1" />);
    fireEvent.change(
      screen.getByLabelText("Question about this job"),
      { target: { value: "Why did it fail?" } },
    );
    fireEvent.click(screen.getByRole("button", {
      name: "Ask Chat Agent",
    }));

    await waitFor(() => {
      expect(ask).toHaveBeenCalledWith(
        "job-1",
        "Why did it fail?",
      );
    });
    expect(await screen.findByText("Dependency import failed.")).toBeTruthy();
  });

  it("renders the durable memory summary without treating it as a citation", async () => {
    vi.spyOn(api, "chatMessages").mockResolvedValue([
      userMessage,
      assistantMessage,
    ]);
    vi.spyOn(api, "chatMemory").mockResolvedValue(memory);

    render(<JobChatPanel jobId="job-1" />);

    expect(await screen.findByText(/Memory v2/)).toBeTruthy();
    expect(screen.getByText(memory.summary)).toBeTruthy();
    expect(screen.getAllByRole("link", {
      name: "reports/final_report.md",
    })).toHaveLength(1);
  });

  it("keeps raw history visible when memory is unavailable", async () => {
    vi.spyOn(api, "chatMessages").mockResolvedValue([
      userMessage,
      assistantMessage,
    ]);
    vi.spyOn(api, "chatMemory").mockRejectedValue(
      new Error("memory unavailable"),
    );

    render(<JobChatPanel jobId="job-1" />);

    expect(await screen.findByText("Dependency import failed.")).toBeTruthy();
    expect(await screen.findByText(/Memory 暂时不可用/)).toBeTruthy();
  });
});
