import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { api } from "../api/client";
import type { ResourceView } from "../api/types";

export type PublishedResourcePair = {
  paper: ResourceView;
  repository: ResourceView;
};

type ResourcePair = {
  paper: ResourceView | null;
  repository: ResourceView | null;
};

const TERMINAL_RESOURCE_FAILURES = new Set([
  "rejected",
  "cancelled",
  "failed_terminal",
  "reconciliation_required",
]);

// 轮询仅用于 Resource；Job 状态仍使用 SSE。导出该函数便于单测。
export async function waitUntilPublished(
  resourceId: string,
  signal: AbortSignal,
  onUpdate: (resource: ResourceView) => void,
): Promise<ResourceView> {
  while (!signal.aborted) {
    const current = await api.resource(resourceId);
    onUpdate(current);
    if (current.status === "published") return current;
    if (TERMINAL_RESOURCE_FAILURES.has(current.status)) {
      throw new Error(`Resource stopped in status: ${current.status}`);
    }
    await new Promise<void>((resolve, reject) => {
      const onAbort = () => {
        window.clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      };
      const timer = window.setTimeout(() => {
        signal.removeEventListener("abort", onAbort);
        resolve();
      }, 1000);
      signal.addEventListener("abort", onAbort, { once: true });
    });
  }
  throw new DOMException("Aborted", "AbortError");
}

type Props = {
  onReady: (resources: PublishedResourcePair) => void;
};

export function ResourceWizard({ onReady }: Props) {
  const [paperUrl, setPaperUrl] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [commitSha, setCommitSha] = useState("");
  const [resources, setResources] = useState<ResourcePair>({
    paper: null,
    repository: null,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef(new AbortController());

  useEffect(() => () => abortRef.current.abort(), []);

  function updateResource(resource: ResourceView) {
    setResources((current) => ({
      ...current,
      [resource.kind === "paper_pdf" ? "paper" : "repository"]: resource,
    }));
  }

  async function createResources(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      // 先显示规范化 URL 与 request hash，创建时绝不自动批准。
      // 第二个请求失败后重试时，复用已创建的 paper resource，
      // 不因部分失败重复生成资源请求。
      if (!resources.paper) {
        const paper = await api.createResource({
          kind: "paper_pdf",
          sourceUrl: paperUrl,
          purpose: "paper input for Web Console reproduction session",
        });
        updateResource(paper);
      }

      if (!resources.repository) {
        const repository = await api.createResource({
          kind: "git_repository",
          sourceUrl: repoUrl,
          expectedGitCommit: commitSha.trim().toLowerCase(),
          purpose: "repository input for Web Console reproduction session",
        });
        updateResource(repository);
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Resource 创建失败");
    } finally {
      setBusy(false);
    }
  }

  async function approveAndWait(resource: ResourceView) {
    setBusy(true);
    setError(null);
    try {
      const approved = await api.approveResource(resource);
      updateResource(approved);
      const published = await waitUntilPublished(
        approved.resource_id,
        abortRef.current.signal,
        updateResource,
      );
      updateResource(published);
    } catch (caught) {
      if (!(caught instanceof DOMException && caught.name === "AbortError")) {
        setError(caught instanceof Error ? caught.message : "Resource 获取失败");
      }
    } finally {
      setBusy(false);
    }
  }

  const published =
    resources.paper?.status === "published" &&
    resources.repository?.status === "published";

  return (
    <section className="resource-wizard">
      {!resources.paper || !resources.repository ? (
        <form onSubmit={createResources}>
          <label>
            Paper PDF HTTPS URL
            <input
              type="url"
              required
              value={paperUrl}
              onChange={(event) => setPaperUrl(event.currentTarget.value)}
            />
          </label>
          <label>
            Git repository HTTPS URL
            <input
              type="url"
              required
              value={repoUrl}
              onChange={(event) => setRepoUrl(event.currentTarget.value)}
            />
          </label>
          <label>
            Exact commit SHA
            <input
              required
              minLength={40}
              maxLength={64}
              pattern="[0-9a-fA-F]{40,64}"
              value={commitSha}
              onChange={(event) => setCommitSha(event.currentTarget.value)}
            />
          </label>
          <button className="primary-action" disabled={busy} type="submit">
            Create acquisition requests
          </button>
        </form>
      ) : null}

      {([resources.paper, resources.repository].filter(Boolean) as ResourceView[])
        .map((resource) => (
          <article className="resource-card" key={resource.resource_id}>
            <strong>{resource.kind}</strong>
            <p>{resource.source_url_sanitized}</p>
            {resource.expected_git_commit && <code>{resource.expected_git_commit}</code>}
            <small>Request SHA-256</small>
            <code>{resource.request_sha256}</code>
            <p>Status: {resource.status}</p>
            {resource.status === "awaiting_approval" && (
              <button disabled={busy} onClick={() => void approveAndWait(resource)}>
                Approve this exact request
              </button>
            )}
          </article>
        ))}

      {error && <p className="inline-error" role="alert">{error}</p>}
      {published && (
        <button
          className="primary-action"
          onClick={() => onReady({
            paper: resources.paper!,
            repository: resources.repository!,
          })}
        >
          Continue with published resources
        </button>
      )}
    </section>
  );
}
