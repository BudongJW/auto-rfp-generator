"""Claude API 공급자(공식 Python SDK `anthropic`).

- 구조화 출력: output_config.format(JSON Schema)로 응답 형식을 강제하고, 게이트웨이가 Pydantic으로 재검증한다.
- 프롬프트 캐싱: 고정 지침(system)과 RFP 발췌 블록에 cache_control을 둔다. 같은 발췌로 2회 실행하면 두 번째는 캐시를 읽는다.
- 사고와 effort: thinking은 생략해 모델 기본(adaptive)에 맡기고, effort를 과제별로 명시한다.
- 거부: stop_reason == "refusal"을 먼저 확인한다. 서버 측 fallback("default")을 기본으로 켜고,
  모델이 그 옵션을 받지 않으면 한 번만 끄고 다시 보낸다.
- 긴 출력이 끊기지 않도록 스트리밍으로 받고 get_final_message()로 완성본을 얻는다.

모델 ID는 저장소에 고정하지 않는다: --llm-model 또는 환경변수 RFPGEN_LLM_MODEL, 없으면 Models API에서
가장 최근 Opus 계열을 고른다.

인증: rfpgen 전용 키 RFP_ANTHROPIC_API_KEY가 있으면 그 키로 공식 API 주소(또는 RFPGEN_ANTHROPIC_BASE_URL)에
보낸다. Claude Code 같은 도구가 자기 용도로 둔 ANTHROPIC_BASE_URL을 물려받지 않기 위해서다. 없으면 SDK 기본
(ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, ant 로그인 프로필 순)을 따른다.
"""

from __future__ import annotations

import os
from typing import Any

from .gateway import LLMCall, LLMError, ProviderReply

FALLBACK_BETA = "server-side-fallback-2026-07-01"
DEFAULT_FAMILY = "claude-opus"
KEY_ENV = "RFP_ANTHROPIC_API_KEY"
BASE_URL_ENV = "RFPGEN_ANTHROPIC_BASE_URL"
OFFICIAL_BASE_URL = "https://api.anthropic.com"


def client_options() -> dict[str, str]:
    """rfpgen 전용 키가 있으면 {api_key, base_url}, 없으면 빈 dict(SDK 기본 인증)."""
    key = os.environ.get(KEY_ENV)
    if not key:
        return {}
    return {"api_key": key, "base_url": os.environ.get(BASE_URL_ENV) or OFFICIAL_BASE_URL}


def credential_source() -> str:
    """인증 정보가 어디서 오는지(값은 돌려주지 않는다)."""
    if os.environ.get(KEY_ENV):
        return KEY_ENV
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        if os.environ.get(name):
            return name
    return ""


class AnthropicProvider:
    name = "anthropic"
    def __init__(self, model: str | None = None, client: Any = None, use_fallbacks: bool = True,
                 timeout: float = 600.0, share_internal: bool = False) -> None:
        # 기본은 공개 RFP만 보낸다. KB 설명·과거 제안서 문단(internal)은 사용자가 --llm-share-kb로 허용할 때만.
        self.allowed_data_classes = {"public", "internal"} if share_internal else {"public"}
        self._client = client
        self._model = model or os.environ.get("RFPGEN_LLM_MODEL") or None
        self.use_fallbacks = use_fallbacks
        self.timeout = timeout

    @property
    def client(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(timeout=self.timeout, **client_options())
        return self._client

    def resolve_model(self) -> str:
        if self._model:
            return self._model
        try:
            models = list(self.client.models.list())
        except Exception as exc:  # 인증 정보 없음(TypeError), API 오류 등
            raise LLMError(f"사용할 모델을 정하지 못했습니다(Models API 조회 실패): {exc}. "
                           "--llm-model 또는 RFPGEN_LLM_MODEL로 모델 ID를 지정하세요") from exc
        family = [m for m in models if str(getattr(m, "id", "")).startswith(DEFAULT_FAMILY)]
        if not family:
            raise LLMError("Opus 계열 모델을 찾지 못했습니다 — --llm-model로 모델 ID를 지정하세요")
        family.sort(key=lambda m: str(getattr(m, "created_at", "")), reverse=True)
        self._model = str(family[0].id)
        return self._model

    def _request(self, call: LLMCall, json_schema: dict[str, Any], model: str, fallbacks: bool) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": call.max_tokens,
            "system": [{"type": "text", "text": call.system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": call.context, "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": call.instruction},
                ],
            }],
            "output_config": {"effort": call.effort, "format": {"type": "json_schema", "schema": json_schema}},
        }
        if fallbacks:
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        return kwargs

    def complete(self, call: LLMCall, json_schema: dict[str, Any]) -> ProviderReply:
        import anthropic

        model = self.resolve_model()
        fallbacks = self.use_fallbacks
        for attempt in range(2):
            try:
                with self.client.beta.messages.stream(**self._request(call, json_schema, model, fallbacks)) as stream:
                    message = stream.get_final_message()
                break
            except anthropic.BadRequestError as exc:
                if fallbacks and attempt == 0 and "fallback" in str(exc).lower():
                    fallbacks = False  # 이 모델이 서버 측 fallback을 받지 않으면 끄고 다시 보낸다
                    continue
                raise LLMError(f"{call.task}: 잘못된 요청 — {exc}") from exc
            except anthropic.AuthenticationError as exc:
                raise LLMError(f"{call.task}: 인증 실패 — API 키를 확인하세요") from exc
            except anthropic.RateLimitError as exc:
                raise LLMError(f"{call.task}: 사용량 한도 초과 — 잠시 뒤 다시 실행하세요") from exc
            except anthropic.APIStatusError as exc:
                raise LLMError(f"{call.task}: API 오류 {exc.status_code} — {exc}") from exc
            except anthropic.APIConnectionError as exc:
                raise LLMError(f"{call.task}: 네트워크 오류 — {exc}") from exc
            except TypeError as exc:  # 인증 정보가 전혀 없을 때 SDK가 요청 전에 던진다
                raise LLMError(f"{call.task}: 인증 정보가 없습니다 — ANTHROPIC_API_KEY를 설정하거나 `ant auth login`을 하세요") from exc

        text = next((b.text for b in message.content if getattr(b, "type", None) == "text"), "")
        usage = message.usage
        usage_dict = {
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            "cache_read_input_tokens": int(getattr(usage, "cache_read_input_tokens", 0) or 0),
            "cache_creation_input_tokens": int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
        }
        details = getattr(message, "stop_details", None)
        iterations = getattr(usage, "iterations", None) or []
        return ProviderReply(
            text=text,
            model=str(getattr(message, "model", model)),
            stop_reason=getattr(message, "stop_reason", None),
            usage=usage_dict,
            request_id=getattr(message, "_request_id", None),
            refusal_category=getattr(details, "category", None) if details is not None else None,
            fallback_used=any(getattr(it, "type", "") == "fallback_message" for it in iterations),
        )
