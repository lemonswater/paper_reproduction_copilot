import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { api } from "../src/api/client";
import { DecisionCard } from "../src/components/DecisionCard";
import type {
  AllowedOperation,
  JobView,
  TimelineItem,
} from "../src/api/types";

const commandHash = "a".repeat(64);

const operation: AllowedOperation = {
  operation_id: "wait:2:command_selection",
  kind: "submit_decision",
  endpoint: "/v1/jobs/job-1/decisions",
  decision_kind: "command_selection",
  expected_node: "command_selection",
  expected_job_version: 4,
  expected_wait_generation: 2,
  allowed_decisions: [],
  requires_idempotency_key: true,
  detail: null,
};

const job: JobView = {
  job_id: "job-1",
  thread_id: "thread-1",
  run_id: "run-1",
  status: "waiting_for_input",
  version: 4,
  attempt_count: 1,
  max_attempts: 3,
  wait_generation: 2,
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
  allowed_operations: [operation],
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:01:00Z",
};

const item: TimelineItem = {
  item_id: "decision:wait:2:command_selection",
  role: "assistant",
  kind: "decision",
  title: "Select command",
  content: "Choose and edit a command.",
  created_at: "2026-08-01T00:01:00Z",
  event_id: null,
  operation,
  interrupt: {
    node: "command_selection",
    interrupt_id: "interrupt-1",
    value_preview: {
      run_commands: [
        {
          command: "python train.py --dataset_path <path>",
          cwd: "/data/repo",
          risk_level: "high",
          reason: "train",
        },
        {
          command: "python test.py --checkpoint <path>",
          cwd: "/data/repo",
          risk_level: "medium",
          reason: "test",
        },
      ],
      run_commands_hash: commandHash,
    },
  },
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderCard() {
  const onMutation = vi.fn(
    async (action: () => Promise<unknown>) => {
      await action();
    },
  );
  render(
    <DecisionCard
      job={job}
      item={item}
      onMutation={onMutation}
    />,
  );
  return onMutation;
}

describe("command selection editor", () => {
  it("submits selection without redundant edits", async () => {
    const submit = vi.spyOn(
      api,
      "submitDecision",
    ).mockResolvedValue(job);
    renderCard();

    fireEvent.click(
      screen.getByLabelText("Select command 2"),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue with selected command",
      }),
    );

    await waitFor(() => {
      expect(submit).toHaveBeenCalled();
    });
    expect(submit.mock.calls[0][2]).toEqual({
      kind: "command_selection",
      selected_index: 1,
      edits: [],
      run_commands_hash: commandHash,
    });
  });

  it("submits only changed commands with original indexes", async () => {
    const submit = vi.spyOn(
      api,
      "submitDecision",
    ).mockResolvedValue(job);
    renderCard();

    fireEvent.change(
      screen.getByLabelText("Command 1"),
      {
        target: {
          value: (
            "python train.py "
            + "--dataset_path /data/ntu60"
          ),
        },
      },
    );
    fireEvent.change(
      screen.getByLabelText("Command 2"),
      {
        target: {
          value: (
            "python test.py "
            + "--checkpoint /data/best.pth"
          ),
        },
      },
    );
    fireEvent.click(
      screen.getByLabelText("Select command 2"),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Continue with selected command",
      }),
    );

    await waitFor(() => {
      expect(submit).toHaveBeenCalled();
    });
    expect(submit.mock.calls[0][2]).toMatchObject({
      selected_index: 1,
      run_commands_hash: commandHash,
      edits: [
        {
          index: 0,
          command: (
            "python train.py "
            + "--dataset_path /data/ntu60"
          ),
        },
        {
          index: 1,
          command: (
            "python test.py "
            + "--checkpoint /data/best.pth"
          ),
        },
      ],
    });
  });

  it("restores generated commands without submitting", () => {
    const submit = vi.spyOn(api, "submitDecision");
    renderCard();
    const first = screen.getByLabelText(
      "Command 1",
    ) as HTMLTextAreaElement;

    fireEvent.change(first, {
      target: { value: "python changed.py" },
    });
    fireEvent.click(
      screen.getByRole("button", {
        name: "Restore generated commands",
      }),
    );

    expect(first.value).toContain("train.py");
    expect(submit).not.toHaveBeenCalled();
  });
});
