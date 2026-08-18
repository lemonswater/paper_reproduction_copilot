# Error Report

## 1. PAPER_SECTION_EVIDENCE_INVALID

- Error ID：`error_6a177658a7a0476b`
- Stage：`method_extractor`
- Category：`agent`
- Terminal：`False`
- Retryable：`False`
- Exception：`not_recorded`
- Time：`2026-08-18T07:59:42.845428+00:00`
- Message：Unknown evidence block_ids: ['p016-b0086-6bd8ca2f050']

## 2. PROVIDER_INVOKE_FAILED

- Error ID：`error_382c8470149643fd`
- Stage：`method_extractor`
- Category：`provider`
- Terminal：`False`
- Retryable：`False`
- Exception：`LengthFinishReasonError`
- Time：`2026-08-18T08:01:00.277180+00:00`
- Message：Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=<redacted>, prompt_tokens=<redacted>, total_tokens=<redacted>, completion_tokens_details=<redacted>, prompt_tokens_details=<redacted>

## 3. PAPER_SECTION_EVIDENCE_INVALID

- Error ID：`error_1b96e0db73864103`
- Stage：`method_extractor`
- Category：`agent`
- Terminal：`False`
- Retryable：`False`
- Exception：`not_recorded`
- Time：`2026-08-18T08:01:16.380562+00:00`
- Message：Unknown evidence block_ids: ['p005-b0079-2bc54e2f46']

## 4. PROVIDER_ERROR

- Error ID：`error_561e812dff4d4711`
- Stage：`mapping`
- Category：`provider`
- Terminal：`True`
- Retryable：`False`
- Exception：`ModelRouteUnavailable`
- Time：`2026-08-18T08:01:22.451278+00:00`
- Message：MODEL_ROUTE_INPUT_LIMIT_EXCEEDED
- Traceback Artifact：`/data/tianshaoqi24/agent/paper_reproduction_copilot/runs/eval-provider-pstnet-section-understanding-b02b391d3d-20260818-075800-78251d4b/traces/errors/error_561e812dff4d4711.traceback.txt`
