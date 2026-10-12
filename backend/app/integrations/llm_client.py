import json
import re
from typing import Protocol

from openai import APIError, APITimeoutError, OpenAI

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.logging import event


class Provider(Protocol):
    def complete(self, history: list[dict], tools: list[dict], timeout: float) -> dict: ...


class MockProvider:
    def complete(self, history, tools, timeout):
        message = next(m["content"] for m in reversed(history) if m["role"] == "user")
        if history[-1]["role"] == "tool":
            return {"role": "assistant", "content": "Checked."}
        match = re.search(r"\bORD\d{1,16}\b", message.upper())
        if not match:
            return {"role": "assistant", "content": "Please provide your order ID."}
        name = "cancel_order" if "cancel" in message.lower() else "get_order_status"
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "mock-call",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps({"order_id": match.group()})},
                }
            ],
        }


class OpenAIProvider:
    def complete(self, history, tools, timeout):
        config = settings()
        try:
            with OpenAI(api_key=config.openai_api_key, timeout=timeout, max_retries=0) as client:
                result = client.chat.completions.create(
                    model=config.openai_model,
                    messages=history,
                    tools=tools,
                    parallel_tool_calls=False,
                    max_completion_tokens=500,
                )
            return result.choices[0].message.model_dump(exclude_none=True)
        except APITimeoutError:
            event("provider_failed", error_code="PROVIDER_TIMEOUT")
            raise DomainError("PROVIDER_TIMEOUT", "Support took too long. Please retry.", 504, True) from None
        except APIError:
            event("provider_failed", error_code="PROVIDER_UNAVAILABLE")
            raise DomainError(
                "PROVIDER_UNAVAILABLE", "Support is temporarily unavailable. Please retry.", 503, True
            ) from None


def provider():
    return MockProvider() if settings().provider_mode == "mock" else OpenAIProvider()
