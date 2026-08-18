# Error Report

## 1. PROVIDER_INVOKE_FAILED

- Error ID：`error_ddaec43d2ac04632`
- Stage：`method_extractor`
- Category：`provider`
- Terminal：`False`
- Retryable：`False`
- Exception：`LengthFinishReasonError`
- Time：`2026-08-18T08:02:46.095438+00:00`
- Message：Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=<redacted>, prompt_tokens=<redacted>, total_tokens=<redacted>, completion_tokens_details=<redacted>, prompt_tokens_details=<redacted>

## 2. PAPER_SECTION_EVIDENCE_INVALID

- Error ID：`error_1c84e214ce2c48ee`
- Stage：`method_extractor`
- Category：`agent`
- Terminal：`False`
- Retryable：`False`
- Exception：`not_recorded`
- Time：`2026-08-18T08:03:08.002610+00:00`
- Message：Unknown evidence block_ids: ['p004-b0122-f4f88ee96']

## 3. PAPER_SECTION_EVIDENCE_INVALID

- Error ID：`error_7a7b3163326248ee`
- Stage：`method_extractor`
- Category：`agent`
- Terminal：`False`
- Retryable：`False`
- Exception：`not_recorded`
- Time：`2026-08-18T08:03:49.215583+00:00`
- Message：Unknown evidence block_ids: ['p001-b0088-9e62ee82e3', 'p001-b0090-00155af0f58', 'p001-b0092-380b4f266d8', 'p001-b0094-94fcbc369dc4', 'p001-b0095-816747b9']

## 4. PAPER_SECTION_EVIDENCE_INVALID

- Error ID：`error_907f31e9819b4c40`
- Stage：`method_extractor`
- Category：`agent`
- Terminal：`False`
- Retryable：`False`
- Exception：`not_recorded`
- Time：`2026-08-18T08:04:11.882149+00:00`
- Message：Unknown evidence block_ids: ['p008-b0120-121e189471ab', 'p008-b0123-5d7b70f1']

## 5. PROVIDER_ERROR

- Error ID：`error_8ba49fa918e843de`
- Stage：`mapping`
- Category：`provider`
- Terminal：`True`
- Retryable：`False`
- Exception：`ModelRouteUnavailable`
- Time：`2026-08-18T08:05:34.754652+00:00`
- Message：MODEL_ROUTE_INPUT_LIMIT_EXCEEDED
- Traceback Artifact：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-p4transformer-mapping-959727b037-20260818-080123-076fe9c6/traces/errors/error_8ba49fa918e843de.traceback.txt`
