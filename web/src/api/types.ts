export type JobStatus =
  | "queued"
  | "running"
  | "waiting_for_input"
  | "cancelling"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "reconciliation_required";

export type PublicInterrupt = {
  node: string;
  interrupt_id: string | null;
  value_preview: unknown;
};

export type AllowedOperation = {
  operation_id: string;
  kind: "submit_decision" | "cancel" | "operator_reconciliation_required";
  endpoint: string | null;
  decision_kind:
    | "command_selection"
    | "action_approval"
    | "patch_review"
    | "patch_promotion"
    | null;
  expected_node: string | null;
  expected_job_version: number;
  expected_wait_generation: number | null;
  allowed_decisions: string[];
  requires_idempotency_key: boolean;
  detail: string | null;
};

export type RunCommandPreview = {
  command: string;
  cwd?: string;
  source?: string;
  risk_level?: string;
  reason?: string;
};

export type CommandSelectionPreview = {
  run_commands: RunCommandPreview[];
  run_commands_hash: string;
};

export type CommandEditPayload = {
  index: number;
  command: string;
};

export type CommandSelectionDecision = {
  kind: "command_selection";
  selected_index: number;
  edits: CommandEditPayload[];
  run_commands_hash: string;
};

export type ReviewDecision = {
  kind:
    | "action_approval"
    | "patch_review"
    | "patch_promotion";
  decision: "approved" | "rejected" | "revise";
  feedback: string | null;
};

export type DecisionPayload =
  | CommandSelectionDecision
  | ReviewDecision;

export type JobView = {
  job_id: string;
  thread_id: string;
  run_id: string;
  status: JobStatus;
  version: number;
  attempt_count: number;
  max_attempts: number;
  wait_generation: number;
  interrupts: PublicInterrupt[];
  cancel_requested: boolean;
  cancellation_reason: string | null;
  result: {
    final_status: string | null;
    stage_error_count: number | null;
    output_file_count: number | null;
  } | null;
  error: unknown;
  reconciliation: unknown;
  input: {
    paper_name: string;
    repo_name: string;
    experiment_goal: string;
    execution_profile_id: string;
  };
  allowed_operations: AllowedOperation[];
  created_at: string;
  updated_at: string;
};

export type TimelineItem = {
  item_id: string;
  role: "user" | "assistant" | "system";
  kind: "request" | "progress" | "decision" | "result" | "error";
  title: string;
  content: string;
  created_at: string;
  event_id: number | null;
  operation: AllowedOperation | null;
  interrupt: PublicInterrupt | null;
};

export type TimelineResponse = {
  job: JobView;
  items: TimelineItem[];
  last_event_id: number;
};

export type ArtifactView = {
  artifact_id: string;
  run_id: string;
  layer: string;
  relative_path: string;
  media_type: string;
  sha256: string;
  size_bytes: number;
  producer_node: string;
  created_at: string;
  preview_supported: boolean;
  integrity_status: "unchecked" | "current";
};

export type ArtifactPreview = {
  artifact_id: string;
  relative_path: string;
  media_type: string;
  sha256: string;
  total_size_bytes: number;
  returned_bytes: number;
  truncated: boolean;
  encoding: "utf-8";
  content: string;
};

export type ResourceView = {
  resource_id: string;
  kind: "paper_pdf" | "git_repository" | "checkpoint";
  source_url_sanitized: string;
  purpose: string;
  expected_git_commit: string | null;
  request_sha256: string;
  status: string;
  version: number;
  manifest: Record<string, unknown> | null;
  error: unknown;
};

export type UiConfig = {
  product_name: string;
  default_execution_profile: string;
  execution_profiles: Array<{
    profile_id: string;
    backend: string;
    enforcement_mode: string;
    network_policy: string;
  }>;
  chat_enabled: boolean;
};

export type ComparisonCategory =
  | "input"
  | "repository"
  | "environment"
  | "command"
  | "execution"
  | "error"
  | "repair"
  | "artifact";

export interface ComparisonListItem {
  comparison_id: string;
  comparison_hash: string;
  base_job_id: string;
  base_run_id: string;
  target_job_id: string;
  target_run_id: string;
  change_count: number;
  high_count: number;
  changed_categories: ComparisonCategory[];
  created_at: string;
}

export interface ComparisonListResponse {
  items: ComparisonListItem[];
  count: number;
}

export type ChatCitation = {
  citation_id: string;
  source_type: "job" | "event" | "artifact" | "log" | "comparison";
  label: string;
  artifact_id: string | null;
  relative_path: string | null;
  artifact_sha256: string | null;
  event_id: number | null;
  locator: string | null;
  comparison_id: string | null;
  comparison_hash: string | null;
  base_job_id: string | null;
  target_job_id: string | null;
};

export type ChatMessage = {
  message_id: string;
  job_id: string;
  sequence: number;
  role: "user" | "assistant";
  content: string;
  citations: ChatCitation[];
  reply_to: string | null;
  created_at: string;
};

export type ChatAskResponse = {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  replayed: boolean;
  allowed_operations: AllowedOperation[];
  memory: ChatMemoryStatus;
};

export type MemoryStatement = {
  text: string;
  source_sequences: number[];
};

export type ConversationMemory = {
  job_id: string;
  version: number;
  covered_through_sequence: number;
  summary: string;
  user_constraints: MemoryStatement[];
  decisions: MemoryStatement[];
  open_questions: MemoryStatement[];
  citation_anchors: ChatCitation[];
  memory_sha256: string;
  created_at: string;
};

export type ChatMemoryStatus = {
  enabled: boolean;
  available: boolean;
  version: number | null;
  covered_through_sequence: number;
  degraded: boolean;
};
