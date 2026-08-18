import type {
  AllowedOperation,
  ArtifactPreview,
  ArtifactView,
  ChatAskResponse,
  ChatMessage,
  ConversationMemory,
  DecisionPayload,
  JobView,
  ResourceView,
  TimelineResponse,
  UiConfig,
} from "./types";

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail ?? payload;
    throw new ApiClientError(
      detail?.message ?? `Request failed: ${response.status}`,
      response.status,
      detail?.code ?? "HTTP_ERROR",
    );
  }
  return response.json() as Promise<T>;
}

function mutationHeaders(): HeadersInit {
  return { "Idempotency-Key": crypto.randomUUID() };
}

export const api = {
  async config() {
    return request<UiConfig>("/v1/ui/config");
  },

  async listJobs(): Promise<JobView[]> {
    const result = await request<{ items: JobView[] }>("/v1/jobs?limit=100");
    return result.items;
  },

  timeline(jobId: string) {
    return request<TimelineResponse>(
      `/v1/ui/jobs/${encodeURIComponent(jobId)}/timeline`,
    );
  },

  async createJob(input: {
    paperResourceId: string;
    repoResourceId: string;
    experimentGoal: string;
    executionProfileId: string;
  }): Promise<JobView> {
    const result = await request<{ job: JobView }>("/v1/jobs", {
      method: "POST",
      headers: mutationHeaders(),
      body: JSON.stringify({
        paper_resource_id: input.paperResourceId,
        repo_resource_id: input.repoResourceId,
        experiment_goal: input.experimentGoal,
        execution_profile_id: input.executionProfileId,
      }),
    });
    return result.job;
  },

  createResource(input: {
    kind: "paper_pdf" | "git_repository";
    sourceUrl: string;
    expectedGitCommit?: string;
    purpose: string;
  }) {
    return request<{ resource: ResourceView }>("/v1/resources", {
      method: "POST",
      headers: mutationHeaders(),
      body: JSON.stringify({
        kind: input.kind,
        source_url: input.sourceUrl,
        expected_git_commit: input.expectedGitCommit ?? null,
        expected_sha256: null,
        purpose: input.purpose,
      }),
    }).then((value) => value.resource);
  },

  resource(resourceId: string) {
    return request<ResourceView>(
      `/v1/resources/${encodeURIComponent(resourceId)}`,
    );
  },

  approveResource(resource: ResourceView) {
    return request<{ resource: ResourceView }>(
      `/v1/resources/${encodeURIComponent(resource.resource_id)}/decision`,
      {
        method: "POST",
        body: JSON.stringify({
          decision: "approved",
          request_sha256: resource.request_sha256,
          expected_version: resource.version,
          reason: "approved in local Web Console",
        }),
      },
    ).then((value) => value.resource);
  },

  submitDecision(
    _job: JobView,
    operation: AllowedOperation,
    decision: DecisionPayload,
  ) {
    return request<{ job: JobView }>(operation.endpoint!, {
      method: "POST",
      headers: mutationHeaders(),
      body: JSON.stringify({
        expected_job_version: operation.expected_job_version,
        expected_wait_generation: operation.expected_wait_generation,
        decision,
      }),
    }).then((value) => value.job);
  },

  cancel(job: JobView) {
    const operation = job.allowed_operations.find((item) => item.kind === "cancel");
    if (!operation?.endpoint) {
      throw new Error("Current job cannot be cancelled");
    }
    return request<{ job: JobView }>(operation.endpoint, {
      method: "POST",
      headers: mutationHeaders(),
      body: JSON.stringify({
        expected_job_version: operation.expected_job_version,
        reason: "cancelled from Web Console",
      }),
    }).then((value) => value.job);
  },

  async artifacts(jobId: string): Promise<ArtifactView[]> {
    const result = await request<{ items: ArtifactView[] }>(
      `/v1/jobs/${encodeURIComponent(jobId)}/artifacts`,
    );
    return result.items;
  },

  artifactPreview(jobId: string, artifactId: string) {
    return request<ArtifactPreview>(
      `/v1/jobs/${encodeURIComponent(jobId)}`
      + `/artifacts/${encodeURIComponent(artifactId)}/preview`,
    );
  },

  artifactDownloadUrl(jobId: string, artifactId: string) {
    return (
      `/v1/jobs/${encodeURIComponent(jobId)}`
      + `/artifacts/${encodeURIComponent(artifactId)}/download`
    );
  },

  jobExportUrl(jobId: string) {
    return `/v1/jobs/${encodeURIComponent(jobId)}/export`;
  },

  log(jobId: string) {
    return request<{ content: string; relative_path: string | null }>(
      `/v1/jobs/${encodeURIComponent(jobId)}/logs?lines=200`,
    );
  },

  async chatMessages(jobId: string): Promise<ChatMessage[]> {
    const result = await request<{
      items: ChatMessage[];
      next_after: number;
    }>(`/v1/jobs/${encodeURIComponent(jobId)}/chat/recent?limit=100`);
    return result.items;
  },

  chatMemory(jobId: string) {
    return request<ConversationMemory | null>(
      `/v1/jobs/${encodeURIComponent(jobId)}/chat/memory`,
    );
  },

  askChat(jobId: string, question: string) {
    return request<ChatAskResponse>(
      `/v1/jobs/${encodeURIComponent(jobId)}/chat`,
      {
        method: "POST",
        headers: mutationHeaders(),
        body: JSON.stringify({ question }),
      },
    );
  },
};
