"""LLM 게이트웨이(설계서 8장): 공급자 추상화, 데이터 분류 정책, 구조화 출력 검증, 감사 로그."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from .schema import strict_schema

T = TypeVar("T", bound=BaseModel)
# public: 공개 RFP / internal: KB 설명·ID·과거 제안서 문단(값 제외, --llm-share-kb로 허용)
# confidential: KB 값·단가·미공개 전략(현재 어떤 공급자에도 보내지 않음) / personal: 개인정보(보내지 않음)
DataClass = Literal["public", "internal", "confidential", "personal"]


@dataclass
class LLMCall:
    """한 번의 구조화 출력 호출.

    system은 모든 과제가 공유하는 고정 지침(캐시 접두부), context는 RFP 발췌(캐시 지점),
    instruction은 과제 지시(가변)다. 지시는 산문으로 쓰고 태그는 데이터 구분에만 쓴다(설계서 8.4절).
    """

    task: str
    system: str
    context: str
    instruction: str
    schema: type[BaseModel]
    effort: str = "high"
    max_tokens: int = 32000
    data_class: DataClass = "public"


@dataclass
class ProviderReply:
    text: str
    model: str
    stop_reason: str | None
    usage: dict[str, int] = field(default_factory=dict)
    request_id: str | None = None
    refusal_category: str | None = None
    fallback_used: bool = False


class Provider(Protocol):
    name: str
    allowed_data_classes: set[str]

    def complete(self, call: LLMCall, json_schema: dict[str, Any]) -> ProviderReply: ...


class LLMError(RuntimeError):
    """LLM 호출 실패(인증·네트워크·잘못된 요청 등). 결정적 결과는 그대로 쓰고 과제만 건너뛴다."""


class LLMRefusal(LLMError):
    pass


class LLMInvalidOutput(LLMError):
    pass


class LLMPolicyError(LLMError):
    pass


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    def add(self, u: dict[str, int]) -> None:
        self.calls += 1
        for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            setattr(self, k, getattr(self, k) + int(u.get(k) or 0))


class LLMGateway:
    def __init__(self, provider: Provider, audit_path: Path | None = None) -> None:
        self.provider = provider
        self.audit_path = audit_path
        self.usage = Usage()

    def _audit(self, record: dict[str, Any]) -> None:
        if self.audit_path is None:
            return
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def run(self, call: LLMCall, schema: type[T]) -> tuple[T, ProviderReply]:
        if call.data_class not in self.provider.allowed_data_classes:
            raise LLMPolicyError(
                f"{call.task}: '{call.data_class}' 데이터는 공급자 '{self.provider.name}'로 보낼 수 없습니다(설계서 8.3절)")
        json_schema = strict_schema(schema)
        digest = hashlib.sha256((call.system + call.context + call.instruction).encode("utf-8")).hexdigest()[:16]
        record: dict[str, Any] = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "task": call.task, "provider": self.provider.name,
            "effort": call.effort, "data_class": call.data_class, "input_sha256_16": digest,
            "context_chars": len(call.context),
        }
        started = time.monotonic()
        try:
            reply = self.provider.complete(call, json_schema)
        except LLMError as exc:
            record.update(status="error", error=str(exc)[:500], seconds=round(time.monotonic() - started, 2))
            self._audit(record)
            raise
        self.usage.add(reply.usage)
        record.update(model=reply.model, stop_reason=reply.stop_reason, usage=reply.usage, request_id=reply.request_id,
                      fallback_used=reply.fallback_used, seconds=round(time.monotonic() - started, 2))
        if reply.stop_reason == "refusal":
            record.update(status="refusal", refusal_category=reply.refusal_category)
            self._audit(record)
            raise LLMRefusal(f"{call.task}: 모델이 응답을 거부했습니다(category={reply.refusal_category})")
        if reply.stop_reason == "max_tokens":
            record.update(status="truncated")
            self._audit(record)
            raise LLMInvalidOutput(f"{call.task}: 출력이 max_tokens에서 잘렸습니다")
        try:
            data = schema.model_validate(json.loads(reply.text))
        except (json.JSONDecodeError, ValidationError) as exc:
            record.update(status="invalid", error=str(exc)[:500], output=reply.text[:2000])
            self._audit(record)
            raise LLMInvalidOutput(f"{call.task}: 응답이 스키마에 맞지 않습니다 — {exc}") from exc
        record.update(status="ok", output=json.loads(reply.text))
        self._audit(record)
        return data, reply
