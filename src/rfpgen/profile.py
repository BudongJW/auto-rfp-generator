"""계층형 설정 프로필(설계서 9장).

내장 기본값 < 조직 설정 < 프로젝트 오버라이드 순으로 덮어쓴다.
RFP 파싱값은 프로필 밖(Rfp 객체)에 있고, 사용하는 쪽에서 항상 우선한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

BUILTIN_PROFILES = "national_negotiation_sw"


@dataclass(frozen=True)
class ProfileValue:
    value: Any
    status: str
    ref: str
    layer: str


class Profile:
    def __init__(self, name: str, values: dict[str, ProfileValue], description: str = "") -> None:
        self.name = name
        self.description = description
        self._values = values

    def get(self, key: str) -> ProfileValue:
        try:
            return self._values[key]
        except KeyError as exc:
            raise KeyError(f"프로필 '{self.name}'에 '{key}' 값이 없습니다") from exc

    def value(self, key: str) -> Any:
        return self.get(key).value

    def items(self) -> list[tuple[str, ProfileValue]]:
        return sorted(self._values.items())

    def merged(self, layer_data: dict[str, Any], layer: str) -> Profile:
        values = dict(self._values)
        values.update(_flatten(layer_data, layer))
        return Profile(self.name, values, self.description)


def _is_leaf(node: Any) -> bool:
    return isinstance(node, dict) and "value" in node and set(node) <= {"value", "status", "ref"}


def _flatten(data: dict[str, Any], layer: str, prefix: str = "") -> dict[str, ProfileValue]:
    out: dict[str, ProfileValue] = {}
    for key, node in data.items():
        if key in ("profile", "description") and not prefix:
            continue
        dotted = f"{prefix}{key}"
        if _is_leaf(node):
            out[dotted] = ProfileValue(
                value=node["value"],
                status=str(node.get("status", "user")),
                ref=str(node.get("ref", "")),
                layer=layer,
            )
        elif isinstance(node, dict):
            out.update(_flatten(node, layer, f"{dotted}."))
        else:
            # 단축 표기(key: value)는 사람이 정한 값으로 본다.
            out[dotted] = ProfileValue(value=node, status="user", ref="", layer=layer)
    return out


def _read_yaml(text: str) -> dict[str, Any]:
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("프로필 YAML의 최상위는 매핑이어야 합니다")
    return data


def load_profile(name: str = BUILTIN_PROFILES, overrides: list[Path] | None = None) -> Profile:
    """내장 프로필을 읽고, 주어진 오버라이드 파일을 순서대로 덮어쓴다."""
    builtin = resources.files("rfpgen.config.profiles").joinpath(f"{name}.yaml")
    data = _read_yaml(builtin.read_text(encoding="utf-8"))
    profile = Profile(data.get("profile", name), _flatten(data, "builtin"), data.get("description", ""))
    for path in overrides or []:
        profile = profile.merged(_read_yaml(Path(path).read_text(encoding="utf-8")), f"override:{path}")
    return profile
