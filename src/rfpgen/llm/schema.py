"""Pydantic 모델 → 구조화 출력(output_config.format)에 맞는 엄격 JSON Schema.

구조화 출력은 모든 object에 additionalProperties: false를 요구하고, 수치·문자열 길이 제약 등은
지원하지 않는다. 응답은 받은 뒤 Pydantic으로 다시 검증하므로, 여기서는 그런 제약을 지운다.
"""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel

_UNSUPPORTED = {
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "minLength", "maxLength", "pattern", "minItems", "maxItems", "uniqueItems",
    "default", "examples", "title",
}


def _strict(node: Any) -> Any:
    if isinstance(node, dict):
        out = {k: _strict(v) for k, v in node.items() if k not in _UNSUPPORTED}
        if out.get("type") == "object" or "properties" in out:
            props = out.get("properties", {})
            out["type"] = "object"
            out["properties"] = props
            out["required"] = list(props.keys())  # 선택 필드도 null을 허용하는 필수 필드로 받는다
            out["additionalProperties"] = False
        return out
    if isinstance(node, list):
        return [_strict(x) for x in node]
    return node


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = copy.deepcopy(model.model_json_schema())
    return _strict(schema)
