import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { api } from "../api/client";
import type {
  AllowedOperation,
  ChatMessage,
  ConversationMemory,
} from "../api/types";

type Props = {
  jobId: string;
};

function mergeMessages(
  current: ChatMessage[],
  incoming: ChatMessage[],
): ChatMessage[] {
  const byId = new Map(
    current.map((item) => [item.message_id, item]),
  );
  for (const item of incoming) byId.set(item.message_id, item);
  return [...byId.values()].sort(
    (left, right) => left.sequence - right.sequence,
  );
}

export function JobChatPanel({ jobId }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [operations, setOperations] = useState<AllowedOperation[]>([]);
  const [memory, setMemory] = useState<ConversationMemory | null>(null);
  const [memoryWarning, setMemoryWarning] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    setMessages([]);
    setError(null);
    setOperations([]);
    setMemory(null);
    setMemoryWarning(null);

    void api.chatMessages(jobId).then((items) => {
      if (!disposed) setMessages(items);
    }).catch((caught) => {
      if (!disposed) {
        setError(
          caught instanceof Error
            ? caught.message
            : "聊天记录加载失败",
        );
      }
    });

    void api.chatMemory(jobId).then((currentMemory) => {
      if (!disposed) setMemory(currentMemory);
    }).catch(() => {
      if (!disposed) {
        setMemory(null);
        setMemoryWarning("Conversation Memory 暂时不可用，仍显示原始消息。");
      }
    });

    return () => {
      disposed = true;
    };
  }, [jobId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const normalized = question.trim();
    if (!normalized || busy) return;

    setBusy(true);
    setError(null);
    try {
      const response = await api.askChat(jobId, normalized);
      setMessages((current) => mergeMessages(
        current,
        [response.user_message, response.assistant_message],
      ));
      setOperations(response.allowed_operations);
      setQuestion("");

      if (response.memory.available) {
        void api.chatMemory(jobId)
          .then((currentMemory) => {
            setMemory(currentMemory);
            setMemoryWarning(null);
          })
          .catch(() => {
            setMemoryWarning("Conversation Memory 暂时不可用。");
          });
      }
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Chat Agent 暂时不可用",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="job-chat" aria-label="Ask about this run">
      <header>
        <p className="eyebrow">Grounded follow-up</p>
        <h3>Ask about this reproduction run</h3>
        <p>
          Answers are limited to the current job's published evidence.
        </p>
      </header>

      {memory && (
        <details className="chat-memory-status">
          <summary>
            Memory v{memory.version} · summarized through message {memory.covered_through_sequence}
          </summary>
          <p>{memory.summary}</p>
          {memory.user_constraints.length > 0 && (
            <ul>
              {memory.user_constraints.map((item) => (
                <li key={`${item.text}:${item.source_sequences.join("-")}`}>
                  {item.text}
                </li>
              ))}
            </ul>
          )}
        </details>
      )}
      {memoryWarning && (
        <p className="memory-warning" role="status">{memoryWarning}</p>
      )}

      <ol className="chat-message-list" aria-live="polite">
        {messages.map((message) => (
          <li
            key={message.message_id}
            className={`chat-message ${message.role}`}
          >
            <span>{message.role === "user" ? "You" : "Chat Agent"}</span>
            <p>{message.content}</p>
            {message.citations.length > 0 && (
              <ul className="citation-list" aria-label="Sources">
                {message.citations.map((citation) => (
                  <li key={citation.citation_id}>
                    {citation.artifact_id ? (
                      <a
                        href={`/v1/jobs/${encodeURIComponent(jobId)}/artifacts/${encodeURIComponent(
                          citation.artifact_id,
                        )}/content`}
                      >
                        {citation.label}
                      </a>
                    ) : (
                      <span>{citation.label}</span>
                    )}
                    {citation.locator && <small>{citation.locator}</small>}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>

      {operations.length > 0 && (
        <p className="operation-notice">
          This job currently has an allowed operation. Review the existing
          decision card above; Chat Agent cannot submit it for you.
        </p>
      )}
      {error && <p className="inline-error" role="alert">{error}</p>}

      <form className="chat-composer" onSubmit={submit}>
        <label>
          Question about this job
          <textarea
            required
            maxLength={4000}
            rows={3}
            value={question}
            disabled={busy}
            onChange={(event) => setQuestion(event.currentTarget.value)}
          />
        </label>
        <button
          className="primary-action"
          type="submit"
          disabled={busy || !question.trim()}
        >
          {busy ? "Checking evidence..." : "Ask Chat Agent"}
        </button>
      </form>
    </section>
  );
}
