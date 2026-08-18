import { useState } from "react";
import type { FormEvent } from "react";

import { api } from "../api/client";
import type {
  CommandEditPayload,
  CommandSelectionPreview,
  DecisionPayload,
  JobView,
  RunCommandPreview,
  TimelineItem,
} from "../api/types";

type Props = {
  job: JobView;
  item: TimelineItem;
  onMutation: (
    action: () => Promise<unknown>
  ) => Promise<void>;
};

const MAX_COMMAND_CHARS = 8192;
const HASH_PATTERN = /^[0-9a-f]{64}$/;

function isRecord(
  value: unknown,
): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

export function parseCommandSelectionPreview(
  value: unknown,
): CommandSelectionPreview | null {
  if (!isRecord(value)) return null;
  if (
    !Array.isArray(value.run_commands)
    || typeof value.run_commands_hash !== "string"
    || !HASH_PATTERN.test(value.run_commands_hash)
  ) {
    return null;
  }

  const commands: RunCommandPreview[] = [];
  for (const raw of value.run_commands) {
    if (!isRecord(raw) || typeof raw.command !== "string") {
      return null;
    }
    commands.push({
      command: raw.command,
      cwd: optionalString(raw.cwd),
      source: optionalString(raw.source),
      risk_level: optionalString(raw.risk_level),
      reason: optionalString(raw.reason),
    });
  }
  if (commands.length === 0) return null;

  return {
    run_commands: commands,
    run_commands_hash: value.run_commands_hash,
  };
}

function changedEdits(
  preview: CommandSelectionPreview,
  drafts: string[],
): CommandEditPayload[] {
  return drafts.flatMap((draft, index) => {
    const normalized = draft.trim();
    return normalized === preview.run_commands[index].command
      ? []
      : [{ index, command: normalized }];
  });
}

export function DecisionCard({
  job,
  item,
  onMutation,
}: Props) {
  const operation = item.operation!;
  const commandPreview = (
    operation.decision_kind === "command_selection"
      ? parseCommandSelectionPreview(
          item.interrupt?.value_preview,
        )
      : null
  );

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [draftCommands, setDraftCommands] = useState<string[]>(
    () => (
      commandPreview?.run_commands.map(
        (item) => item.command,
      ) ?? []
    ),
  );
  const [feedback, setFeedback] = useState("");
  const [localError, setLocalError] = useState<string | null>(
    null,
  );
  const [busy, setBusy] = useState(false);

  async function submit(decision: DecisionPayload) {
    setBusy(true);
    setLocalError(null);
    try {
      await onMutation(
        () => api.submitDecision(
          job,
          operation,
          decision,
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  function updateCommand(index: number, command: string) {
    setDraftCommands((current) => current.map(
      (item, itemIndex) => (
        itemIndex === index ? command : item
      ),
    ));
  }

  async function submitCommandSelection(
    event: FormEvent,
  ) {
    event.preventDefault();
    if (!commandPreview) return;

    const invalidIndex = draftCommands.findIndex(
      (command) => (
        !command.trim()
        || command.trim().length > MAX_COMMAND_CHARS
        || /[\u0000-\u001f\u007f]/.test(command.trim())
      ),
    );
    if (invalidIndex >= 0) {
      setLocalError(
        `Command ${invalidIndex + 1} is empty, too long, or contains control characters.`,
      );
      return;
    }

    await submit({
      kind: "command_selection",
      selected_index: selectedIndex,
      edits: changedEdits(
        commandPreview,
        draftCommands,
      ),
      run_commands_hash: (
        commandPreview.run_commands_hash
      ),
    });
  }

  if (operation.decision_kind === "command_selection") {
    if (!commandPreview) {
      return (
        <div className="decision-card inline-error">
          Command preview is incomplete. Refresh the session before deciding.
        </div>
      );
    }

    return (
      <form
        className="decision-card command-editor"
        onSubmit={submitCommandSelection}
      >
        <p>
          Edit only what this machine requires, then choose the
          command to execute first.
        </p>

        {commandPreview.run_commands.map((command, index) => (
          <fieldset
            className="command-edit-row"
            key={`${index}:${command.command}`}
          >
            <label className="command-choice">
              <input
                type="radio"
                name="selected-command"
                aria-label={`Select command ${index + 1}`}
                checked={selectedIndex === index}
                onChange={() => setSelectedIndex(index)}
              />
              Run command {index + 1} first
            </label>

            <label htmlFor={`command-edit-${index}`}>
              Command {index + 1}
            </label>
            <textarea
              id={`command-edit-${index}`}
              rows={3}
              maxLength={MAX_COMMAND_CHARS}
              value={draftCommands[index]}
              onChange={(event) => updateCommand(
                index,
                event.currentTarget.value,
              )}
            />
            <small>
              cwd: {command.cwd ?? "not provided"}
              {command.risk_level
                ? ` / risk: ${command.risk_level}`
                : ""}
            </small>
            {command.reason && <p>{command.reason}</p>}
          </fieldset>
        ))}

        {localError && (
          <p className="inline-error" role="alert">
            {localError}
          </p>
        )}
        <div className="decision-actions">
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              setDraftCommands(
                commandPreview.run_commands.map(
                  (item) => item.command,
                ),
              );
              setLocalError(null);
            }}
          >
            Restore generated commands
          </button>
          <button type="submit" disabled={busy}>
            Continue with selected command
          </button>
        </div>
      </form>
    );
  }

  const kind = operation.decision_kind;
  if (!kind) {
    return (
      <div className="decision-card inline-error">
        Unsupported decision.
      </div>
    );
  }

  const canRevise = operation.allowed_decisions.includes(
    "revise",
  );
  const canApprove = operation.allowed_decisions.includes(
    "approved",
  );
  const canReject = operation.allowed_decisions.includes(
    "rejected",
  );

  return (
    <div className="decision-card">
      <pre>
        {JSON.stringify(
          item.interrupt?.value_preview,
          null,
          2,
        )}
      </pre>
      <label>
        Feedback
        <textarea
          value={feedback}
          onChange={(event) => setFeedback(
            event.currentTarget.value,
          )}
          maxLength={4000}
        />
      </label>
      <div className="decision-actions">
        {canApprove && (
          <button
            disabled={busy}
            onClick={() => void submit({
              kind,
              decision: "approved",
              feedback: feedback || null,
            })}
          >
            Approve
          </button>
        )}
        {canReject && (
          <button
            disabled={busy}
            onClick={() => void submit({
              kind,
              decision: "rejected",
              feedback: feedback || null,
            })}
          >
            Reject
          </button>
        )}
        {canRevise && (
          <button
            disabled={busy}
            onClick={() => void submit({
              kind,
              decision: "revise",
              feedback: feedback || null,
            })}
          >
            Request revision
          </button>
        )}
      </div>
    </div>
  );
}
