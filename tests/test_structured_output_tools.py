from __future__ import annotations

from types import SimpleNamespace

from pydantic import BaseModel, ValidationError

from app.tools.error_tools import build_structured_stage_error
from app.tools.structured_output_tools import (
    StructuredInvocationResult,
    StructuredOutputAttempt,
    invoke_structured_with_retry,
)


class DemoOutput(BaseModel):
    answer: str
    count: int


class FakeStructuredRunnable:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def invoke(self, prompt, config=None):
        self.prompts.append(prompt)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeLLM:
    def __init__(self, runnable):
        self.runnable = runnable
        self.structured_kwargs = None

    def with_structured_output(self, schema, **kwargs):
        self.structured_kwargs = {
            "schema": schema,
            **kwargs,
        }
        return self.runnable


class FailingSetupLLM:
    def with_structured_output(self, schema, **kwargs):
        raise RuntimeError("structured output setup failed")


class LengthFinishReasonError(RuntimeError):
    pass


def test_structured_output_succeeds_on_first_attempt():
    runnable = FakeStructuredRunnable(
        [
            {
                "raw": SimpleNamespace(content='{"answer":"ok","count":1}'),
                "parsed": DemoOutput(answer="ok", count=1),
                "parsing_error": None,
            }
        ]
    )
    llm = FakeLLM(runnable)

    result = invoke_structured_with_retry(
        llm=llm,
        schema=DemoOutput,
        prompt="return demo output",
        method="json_schema",
        strict=True,
        max_retries=2,
    )

    assert result.succeeded is True
    assert result.value == DemoOutput(answer="ok", count=1)
    assert len(result.attempts) == 1
    assert result.attempts[0].status == "succeeded"
    assert llm.structured_kwargs["method"] == "json_schema"
    assert llm.structured_kwargs["strict"] is True
    assert llm.structured_kwargs["include_raw"] is True


def test_json_mode_embeds_schema_and_omits_provider_strict():
    runnable = FakeStructuredRunnable(
        [
            {
                "raw": SimpleNamespace(content='{"answer":"ok","count":1}'),
                "parsed": DemoOutput(answer="ok", count=1),
                "parsing_error": None,
            }
        ]
    )
    llm = FakeLLM(runnable)

    result = invoke_structured_with_retry(
        llm=llm,
        schema=DemoOutput,
        prompt="return demo output",
        method="json_mode",
        strict=True,
        max_retries=0,
    )

    assert result.succeeded is True
    assert result.strict is None
    assert llm.structured_kwargs["method"] == "json_mode"
    assert "strict" not in llm.structured_kwargs
    assert llm.structured_kwargs["include_raw"] is True
    assert "要求的 JSON Schema" in runnable.prompts[0]
    assert '"answer"' in runnable.prompts[0]


def test_structured_output_retries_with_validation_error():
    runnable = FakeStructuredRunnable(
        [
            {
                "raw": SimpleNamespace(content='{"answer":"missing count"}'),
                "parsed": None,
                "parsing_error": ValueError("count field required"),
            },
            {
                "raw": SimpleNamespace(content='{"answer":"fixed","count":2}'),
                "parsed": DemoOutput(answer="fixed", count=2),
                "parsing_error": None,
            },
        ]
    )
    llm = FakeLLM(runnable)

    result = invoke_structured_with_retry(
        llm=llm,
        schema=DemoOutput,
        prompt="return demo output",
        max_retries=2,
    )

    assert result.succeeded is True
    assert result.value == DemoOutput(answer="fixed", count=2)
    assert [item.status for item in result.attempts] == [
        "validation_error",
        "succeeded",
    ]
    assert "count field required" in runnable.prompts[1]
    assert "要求的 JSON Schema" in runnable.prompts[1]


def test_structured_output_retries_validation_error_raised_by_invoke():
    try:
        DemoOutput.model_validate({"answer": "missing count"})
    except ValidationError as exc:
        invoke_validation_error = exc
    else:
        raise AssertionError("expected DemoOutput validation to fail")

    runnable = FakeStructuredRunnable(
        [
            invoke_validation_error,
            {
                "raw": SimpleNamespace(content='{"answer":"fixed","count":2}'),
                "parsed": DemoOutput(answer="fixed", count=2),
                "parsing_error": None,
            },
        ]
    )
    llm = FakeLLM(runnable)

    result = invoke_structured_with_retry(
        llm=llm,
        schema=DemoOutput,
        prompt="return demo output",
        max_retries=2,
    )

    assert result.succeeded is True
    assert result.value == DemoOutput(answer="fixed", count=2)
    assert [item.status for item in result.attempts] == [
        "validation_error",
        "succeeded",
    ]
    assert result.attempts[0].error_type == "ValidationError"
    assert "count" in runnable.prompts[1]
    assert "要求的 JSON Schema" in runnable.prompts[1]


def test_structured_output_uses_compact_retry_for_truncated_json():
    try:
        DemoOutput.model_validate_json('{"answer":"unfinished')
    except ValidationError as exc:
        truncated_error = exc
    else:
        raise AssertionError("expected truncated JSON to fail")

    runnable = FakeStructuredRunnable(
        [
            truncated_error,
            {
                "raw": SimpleNamespace(
                    content='{"answer":"fixed","count":2}',
                    response_metadata={"finish_reason": "stop"},
                    usage_metadata={
                        "input_tokens": 10,
                        "output_tokens": 8,
                        "total_tokens": 18,
                    },
                ),
                "parsed": DemoOutput(answer="fixed", count=2),
                "parsing_error": None,
            },
        ]
    )

    result = invoke_structured_with_retry(
        llm=FakeLLM(runnable),
        schema=DemoOutput,
        prompt="return demo output",
        max_retries=1,
    )

    first_attempt = result.attempts[0]
    assert result.succeeded is True
    assert first_attempt.truncated is True
    assert first_attempt.raw_preview == '{"answer":"unfinished'
    assert first_attempt.output_chars == len('{"answer":"unfinished')
    assert "上一轮输出在 JSON 对象完成前被截断" in runnable.prompts[1]
    assert "要求的 JSON Schema" not in runnable.prompts[1]

    success_attempt = result.attempts[1]
    assert success_attempt.finish_reason == "stop"
    assert success_attempt.token_usage == {
        "input_tokens": 10,
        "output_tokens": 8,
        "total_tokens": 18,
    }
    assert success_attempt.output_chars == len('{"answer":"fixed","count":2}')


def test_structured_output_retries_length_finish_reason_as_truncation():
    runnable = FakeStructuredRunnable(
        [
            LengthFinishReasonError(
                "Could not parse response content as the length limit was reached"
            ),
            {
                "raw": SimpleNamespace(
                    content='{"answer":"fixed","count":2}'
                ),
                "parsed": DemoOutput(answer="fixed", count=2),
                "parsing_error": None,
            },
        ]
    )

    result = invoke_structured_with_retry(
        llm=FakeLLM(runnable),
        schema=DemoOutput,
        prompt="return demo output",
        max_retries=1,
    )

    assert result.succeeded is True
    assert [item.status for item in result.attempts] == [
        "validation_error",
        "succeeded",
    ]
    assert result.attempts[0].truncated is True
    assert "上一轮输出在 JSON 对象完成前被截断" in runnable.prompts[1]


def test_structured_output_records_callback_metadata_on_parser_error():
    try:
        DemoOutput.model_validate_json('{"answer":"unfinished')
    except ValidationError as exc:
        truncated_error = exc
    else:
        raise AssertionError("expected truncated JSON to fail")

    class CallbackFailingRunnable:
        def invoke(self, prompt, config=None):
            callback = config["callbacks"][0]
            callback.on_llm_end(
                SimpleNamespace(
                    llm_output={
                        "token_usage": {
                            "prompt_tokens": 20,
                            "completion_tokens": 32,
                            "total_tokens": 52,
                        }
                    },
                    generations=[
                        [
                            SimpleNamespace(
                                generation_info={"finish_reason": "length"},
                                message=SimpleNamespace(
                                    response_metadata={},
                                    usage_metadata=None,
                                ),
                            )
                        ]
                    ],
                )
            )
            raise truncated_error

    result = invoke_structured_with_retry(
        llm=FakeLLM(CallbackFailingRunnable()),
        schema=DemoOutput,
        prompt="return demo output",
        max_retries=0,
    )

    attempt = result.attempts[0]
    assert attempt.finish_reason == "length"
    assert attempt.truncated is True
    assert attempt.token_usage == {
        "prompt_tokens": 20,
        "completion_tokens": 32,
        "total_tokens": 52,
    }


def test_structured_stage_error_exposes_last_attempt_diagnostics():
    invocation = StructuredInvocationResult(
        value=None,
        attempts=[
            StructuredOutputAttempt(
                attempt_number=1,
                status="validation_error",
                prompt_kind="original",
                error_type="ValidationError",
                error_message="EOF while parsing",
                finish_reason="length",
                token_usage={
                    "completion_tokens": 4096,
                },
                output_chars=8192,
                truncated=True,
            )
        ],
        method="json_schema",
        strict=True,
        max_retries=0,
    )

    error = build_structured_stage_error(
        stage="experiment_plan",
        invocation=invocation,
        terminal=True,
    )

    assert error.context["finish_reason"] == "length"
    assert error.context["truncated"] is True
    assert error.context["output_chars"] == 8192
    assert error.context["token_usage"] == {
        "completion_tokens": 4096,
    }


def test_structured_output_exhausts_retries():
    invalid = {
        "raw": SimpleNamespace(content='{"wrong":true}'),
        "parsed": None,
        "parsing_error": ValueError("invalid schema"),
    }
    runnable = FakeStructuredRunnable([invalid, invalid, invalid])
    llm = FakeLLM(runnable)

    result = invoke_structured_with_retry(
        llm=llm,
        schema=DemoOutput,
        prompt="return demo output",
        max_retries=2,
    )

    assert result.succeeded is False
    assert result.value is None
    assert len(result.attempts) == 3
    assert all(item.status == "validation_error" for item in result.attempts)


def test_structured_output_does_not_format_retry_invoke_error():
    runnable = FakeStructuredRunnable([RuntimeError("provider does not support json_schema")])
    llm = FakeLLM(runnable)

    result = invoke_structured_with_retry(
        llm=llm,
        schema=DemoOutput,
        prompt="return demo output",
        max_retries=2,
    )

    assert result.succeeded is False
    assert len(result.attempts) == 1
    assert result.attempts[0].status == "invoke_error"


def test_structured_output_returns_configuration_error_when_setup_fails():
    result = invoke_structured_with_retry(
        llm=FailingSetupLLM(),
        schema=DemoOutput,
        prompt="return demo output",
        max_retries=2,
    )

    assert result.succeeded is False
    assert result.value is None
    assert len(result.attempts) == 1
    assert result.attempts[0].attempt_number == 0
    assert result.attempts[0].status == "configuration_error"
    assert result.attempts[0].prompt_kind == "configuration"
