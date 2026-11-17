"""사람 승인 게이트 G1~G5 기록(설계서 3장 '게이트', 원칙 P5).

게이트마다 승인자·시각·메모와 함께 '무엇을 승인했는지'(근거 산출물의 지문)를 project.yaml에 남긴다.
근거가 바뀌면(정정공고로 RFP 새 판, 목차·매핑 수정, 스토리보드 수정, 절 새 판, 새 패키지) 승인은 자동으로
'재확인 필요(stale)'가 되고, 앞 게이트가 무효면 뒤 게이트도 무효로 본다.

| 게이트 | 근거 | 승인 조건(hard) |
|---|---|---|
| G1 추출 확정 | 최신 rfp.vN.json | RFP 분석 결과가 있다 |
| G2 설계 확정 | outline·budget·요구사항→절 매핑 | G1, 연결되지 않은 요구사항 0건 |
| G3 전략 확정 | storyboard.json | G2, 스토리보드가 있다 |
| G4 절 승인 | 절별 최신 판 | G3, 승인할 절 초안이 있다(절별 또는 전체) |
| G5 제출 승인 | 최신 패키지 점검 | G1~G4 모두 승인, 패키지 점검 blocker 0건 |

--force는 hard 조건을 건너뛰지만 기록에 forced=true를 남긴다. 승인자 이름은 이 파일에만 남고 밖으로 보내지 않는다.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

GATES: dict[str, tuple[str, str]] = {
    "G1": ("추출 확정", "평가표·요구사항·작성지침·계약방법"),
    "G2": ("설계 확정", "목차·쪽수 예산·요구사항→절 매핑"),
    "G3": ("전략 확정", "win theme·스토리보드·자료 요청"),
    "G4": ("절 승인", "절 초안(절별)"),
    "G5": ("제출 승인", "점검 blocker 0건·제출 전 점검표"),
}
ORDER = list(GATES)


class GateError(RuntimeError):
    pass


@dataclass
class GateState:
    gate: str
    name: str
    status: str                    # approved | stale | partial | pending
    record: dict[str, Any] | None
    fingerprint: dict[str, Any]
    problems: list[str] = field(default_factory=list)    # 승인을 막는 것
    notes: list[str] = field(default_factory=list)       # 알려 줄 것


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.exists() else ""


def _sha_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _latest(paths: list[Path]) -> Path | None:
    def num(p: Path) -> int:
        m = re.search(r"v(\d+)", p.name)
        return int(m.group(1)) if m else 0
    return max(paths, key=num) if paths else None


def _meta(project: Path) -> dict[str, Any]:
    path = project / "project.yaml"
    meta = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None
    if not meta:
        raise GateError(f"{project}: project.yaml이 없습니다 — 먼저 `rfpgen analyze`를 실행하세요")
    return meta


def _save(project: Path, meta: dict[str, Any]) -> None:
    (project / "project.yaml").write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _section_versions(project: Path) -> dict[str, int]:
    latest: dict[str, int] = {}
    for p in (project / "sections").glob("*.v*.json"):
        m = re.match(r"(.+)\.v(\d+)\.json$", p.name)
        if m:
            latest[m.group(1)] = max(latest.get(m.group(1), 0), int(m.group(2)))
    return dict(sorted(latest.items()))


def _fingerprints(project: Path) -> dict[str, dict[str, Any]]:
    rfp = _latest(list(project.glob("rfp/rfp.v*.json")))
    trace_path = project / "plan" / "trace.json"
    mapping: Any = None
    unmapped: list[str] = []
    if trace_path.exists():
        rows = json.loads(trace_path.read_text(encoding="utf-8")).get("rows", [])
        mapping = sorted((r["req_id"], sorted(r.get("sections") or [])) for r in rows)
        unmapped = [r["req_id"] for r in rows if not r.get("sections")]
    packages = sorted((project / "checks").glob("package-*.json"))       # 실행 ID가 UTC 시각이라 이름순 = 시간순
    package = packages[-1] if packages else None
    pkg_info: dict[str, Any] = {}
    if package is not None:
        rep = json.loads(package.read_text(encoding="utf-8"))
        pkg_info = {"run": rep.get("run_id"), "blocker": sum(1 for f in rep.get("findings", []) if f["severity"] == "blocker")}
    return {
        "G1": {"rfp": rfp.name if rfp else "", "sha": _sha(rfp) if rfp else ""},
        "G2": {"outline": _sha(project / "plan" / "outline.json"), "budget": _sha(project / "plan" / "budget.json"),
               "mapping": _sha_obj(mapping) if mapping is not None else "", "_unmapped": unmapped},
        "G3": {"storyboard": _sha(project / "strategy" / "storyboard.json")},
        "G4": {"sections": _section_versions(project)},
        "G5": pkg_info,
    }


def _public(fp: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in fp.items() if not k.startswith("_")}


def gate_status(project: Path) -> list[GateState]:
    project = Path(project)
    meta = _meta(project)
    records = meta.get("gates") or {}
    fps = _fingerprints(project)
    out: list[GateState] = []
    upstream_ok = True
    for g in ORDER:
        rec = records.get(g)
        fp = fps[g]
        st = GateState(g, GATES[g][0], "pending", rec, _public(fp))
        # 승인 조건
        if g == "G1" and not fp["rfp"]:
            st.problems.append("RFP 분석 결과가 없습니다")
        if g == "G2":
            if not fp["outline"]:
                st.problems.append("목차(plan/outline.json)가 없습니다")
            if fp["_unmapped"]:
                st.problems.append(f"목차에 연결되지 않은 요구사항 {len(fp['_unmapped'])}건: {', '.join(fp['_unmapped'][:8])}")
        if g == "G3" and not fp["storyboard"]:
            st.problems.append("스토리보드가 없습니다 — `rfpgen draft`를 먼저 실행하세요")
        if g == "G4" and not fp["sections"]:
            st.problems.append("절 초안이 없습니다")
        if g == "G5":
            if not fp:
                st.problems.append("패키지 점검 결과가 없습니다 — `rfpgen package`를 먼저 실행하세요")
            elif fp["blocker"]:
                st.problems.append(f"패키지 점검 blocker {fp['blocker']}건")
        if not upstream_ok:
            st.problems.append("앞 게이트가 승인되지 않았거나 재확인이 필요합니다")
        # 상태
        if rec:
            if g == "G4":
                approved = rec.get("sections") or {}
                cur = fp["sections"]
                stale = [s for s, v in approved.items() if s in cur and v < cur[s]]
                missing = [s for s in cur if s not in approved]
                if stale:
                    st.status = "stale"
                    st.notes.append(f"승인 뒤 새 판이 나온 절: {', '.join(stale[:8])}")
                elif missing:
                    st.status = "partial"
                    st.notes.append(f"승인 {len(cur) - len(missing)}/{len(cur)}절 — 남은 절: {', '.join(missing[:8])}")
                else:
                    st.status = "approved"
            else:
                st.status = "approved" if rec.get("basis") == _public(fp) else "stale"
                if st.status == "stale":
                    st.notes.append("승인한 뒤 근거 산출물이 바뀌었습니다")
            if st.status == "approved" and not upstream_ok:
                st.status = "stale"
        upstream_ok = upstream_ok and st.status == "approved"
        out.append(st)
    return out


def approve(project: Path, gate: str, *, by: str, note: str = "", sections: list[str] | None = None,
            force: bool = False, now: dt.datetime | None = None) -> GateState:
    project = Path(project)
    gate = gate.upper()
    if gate not in GATES:
        raise GateError(f"모르는 게이트: {gate} (G1~G5)")
    if not by.strip():
        raise GateError("승인자(--by)를 적어 주세요")
    states = {s.gate: s for s in gate_status(project)}
    st = states[gate]
    if st.problems and not force:
        raise GateError(f"{gate} {st.name}을 승인할 수 없습니다: " + "; ".join(st.problems) + " (꼭 필요하면 --force)")
    meta = _meta(project)
    records = meta.get("gates") or {}
    rec: dict[str, Any] = {"by": by.strip(), "at": (now or dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds"),
                           "note": note, "forced": bool(force and st.problems)}
    if rec["forced"]:
        rec["forced_over"] = list(st.problems)
    if gate == "G4":
        cur = st.fingerprint["sections"]
        chosen = sections or list(cur)
        unknown = [s for s in chosen if s not in cur]
        if unknown:
            raise GateError(f"없는 절: {', '.join(unknown)}")
        prev = (records.get("G4") or {}).get("sections") or {}
        rec["sections"] = {**prev, **{s: cur[s] for s in chosen}}
    else:
        rec["basis"] = st.fingerprint
    records[gate] = rec
    meta["gates"] = records
    _save(project, meta)
    return {s.gate: s for s in gate_status(project)}[gate]


def revoke(project: Path, gate: str) -> None:
    project = Path(project)
    meta = _meta(project)
    records = meta.get("gates") or {}
    gate = gate.upper()
    if gate not in GATES:
        raise GateError(f"모르는 게이트: {gate} (G1~G5)")
    records[gate] = None
    meta["gates"] = records
    _save(project, meta)


STATUS_KO = {"approved": "승인", "stale": "재확인 필요", "partial": "일부 승인", "pending": "미승인"}


def gates_markdown(states: list[GateState]) -> str:
    lines = ["| 게이트 | 상태 | 승인 | 확인할 것 |", "|---|---|---|---|"]
    for s in states:
        who = f"{s.record.get('by')} {s.record.get('at', '')[:10]}" if s.record else "-"
        todo = "; ".join(s.problems + s.notes) or "-"
        lines.append(f"| {s.gate} {s.name} | {STATUS_KO[s.status]} | {who} | {todo} |")
    return "\n".join(lines)


__all__ = ["GATES", "GateError", "GateState", "approve", "gate_status", "gates_markdown", "revoke"]
