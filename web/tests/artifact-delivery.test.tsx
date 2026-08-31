import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../src/api/client";
import { RunContextPanel } from "../src/components/RunContextPanel";
import type { ArtifactPreview, ArtifactView, JobView } from "../src/api/types";

const job: JobView = {
  job_id: "job-1",
  thread_id: "thread-1",
  run_id: "run-1",
  status: "succeeded",
  version: 4,
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
    paper_name: "paper.pdf",
    repo_name: "repo",
    experiment_goal: "reproduce main result",
    execution_profile_id: "local",
  },
  allowed_operations: [],
  created_at: "2026-08-06T00:00:00Z",
  updated_at: "2026-08-06T00:01:00Z",
};

const artifact: ArtifactView = {
  artifact_id: "artifact-1",
  run_id: "run-1",
  layer: "reports",
  relative_path: "reports/final.md",
  media_type: "text/markdown",
  sha256: "a".repeat(64),
  size_bytes: 42,
  producer_node: "final_report_node",
  created_at: "2026-08-06T00:01:00Z",
  preview_supported: true,
  integrity_status: "unchecked",
};

const preview: ArtifactPreview = {
  artifact_id: artifact.artifact_id,
  relative_path: artifact.relative_path,
  media_type: artifact.media_type,
  sha256: artifact.sha256,
  total_size_bytes: 42,
  returned_bytes: 42,
  truncated: false,
  encoding: "utf-8",
  content: '<script data-test="unsafe">window.pwned = true</script>',
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("artifact delivery", () => {
  it("shows all run identities and copies the Job ID", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(
      <RunContextPanel
        job={job}
        onMutation={async () => undefined}
      />,
    );

    expect(screen.getByText("job-1")).toBeTruthy();
    expect(screen.getByText("thread-1")).toBeTruthy();
    expect(screen.getByText("run-1")).toBeTruthy();

    fireEvent.click(
      screen.getByRole("button", { name: "Copy Job ID" }),
    );

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith("job-1");
    });
    expect(
      screen.getByRole("button", { name: "Job ID copied" }),
    ).toBeTruthy();
  });

  it("previews as text and exposes download/export links", async () => {
    vi.spyOn(api, "artifacts").mockResolvedValue([artifact]);
    vi.spyOn(api, "artifactPreview").mockResolvedValue(preview);

    const { container } = render(
      <RunContextPanel
        job={job}
        onMutation={async (action) => {
          await action();
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "artifacts" }));
    fireEvent.click(await screen.findByRole("button", { name: "Preview" }));

    await waitFor(() => {
      expect(api.artifactPreview).toHaveBeenCalledWith(
        "job-1",
        "artifact-1",
      );
    });

    // 字符串可见，但 DOM 中没有 script 元素。
    expect(await screen.findByText(preview.content)).toBeTruthy();
    expect(container.querySelector(".artifact-preview script")).toBeNull();

    expect(
      screen.getByRole("link", { name: "Download" }).getAttribute("href"),
    ).toBe(
      "/v1/jobs/job-1/artifacts/artifact-1/download",
    );
    expect(
      screen.getByRole("link", { name: "Export job (.zip)" })
        .getAttribute("href"),
    ).toBe("/v1/jobs/job-1/export");
  });

  it("does not offer preview when the server disables it", async () => {
    vi.spyOn(api, "artifacts").mockResolvedValue([
      {
        ...artifact,
        artifact_id: "binary-1",
        relative_path: "reports/model.bin",
        media_type: "application/octet-stream",
        preview_supported: false,
      },
    ]);

    render(
      <RunContextPanel job={job} onMutation={async () => undefined} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "artifacts" }));
    await screen.findByText("reports/model.bin");

    expect(screen.queryByRole("button", { name: "Preview" })).toBeNull();
    expect(screen.getByRole("link", { name: "Download" })).toBeTruthy();
  });
});
