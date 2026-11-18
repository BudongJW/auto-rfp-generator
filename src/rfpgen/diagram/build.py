"""도식 스펙 만들기(결정적) — RFP·KB·템플릿에서 조직도·추진체계·일정·WBS·절차·시스템 구성도 스펙을 만든다.

원칙
- 그림에 들어가는 사실은 RFP(사업기간·요구사항 이름·발주기관)와 KB(인력 역할·등급·경력)에서만 가져온다.
- 근거가 없으면 지어내지 않고 [확인 필요] 자리표시자를 넣거나, 일반 템플릿을 쓰고 그 사실을 assumptions에 남긴다.
- 회사명·실명은 넣지 않는다(블라인드 여부와 무관). 사람은 strategy/figures/<id>.json으로 스펙을 고친다.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from ..schemas.diagram import DiagramEdge, DiagramLayer, DiagramNode, DiagramSpec, GanttTask
from ..schemas.kb import CompanyKB
from ..schemas.plan import Outline, OutlineNode
from ..schemas.rfp import Rfp


def load_templates(override: Path | None = None) -> dict[str, Any]:
    base = yaml.safe_load(resources.files("rfpgen.config.diagrams").joinpath("default.yaml").read_text(encoding="utf-8"))
    if override is not None:
        base.update(yaml.safe_load(Path(override).read_text(encoding="utf-8")) or {})
    return base


@dataclass
class BuildContext:
    rfp: Rfp
    kb: CompanyKB
    title: str
    templates: dict[str, Any] = field(default_factory=load_templates)

    @property
    def project_type(self) -> dict[str, Any]:
        for t in self.templates["project_types"]:
            if t.get("match") and re.search(t["match"], self.title):
                return t
        return next(t for t in self.templates["project_types"] if not t.get("match"))

    def rfp_text(self) -> str:
        r = self.rfp
        return " ".join([r.notice.title.value if r.notice.title else ""]
                        + [f"{q.name} {q.definition} {' '.join(q.details)}" for q in r.requirements]
                        + [c for it in r.evaluation.items() for c in it.criteria])


# ---------------------------------------------------------------- 어느 절에 넣을지

def _leaves(outline: Outline) -> list[tuple[OutlineNode, OutlineNode]]:
    """(장, 잎 절) 목록."""
    out = []
    for ch in outline.chapters:
        for n in (ch.children or [ch]):
            out.append((ch, n))
    return out


def plan_figures(outline: Outline, rfp: Rfp, templates: dict[str, Any] | None = None) -> dict[str, list[str]]:
    """절 ID → 넣을 도식 종류. 절 제목(없으면 평가항목 이름)으로 고르고, 종류마다 상한까지만 넣는다."""
    templates = templates or load_templates()
    names = {it.id: it.name for it in rfp.evaluation.items()}
    leaves = _leaves(outline)
    out: dict[str, list[str]] = {}
    used: dict[str, int] = {}
    variants: set[tuple[str, str]] = set()      # 조직도는 추진체계도·수행조직도를 하나씩만(같은 모양이 겹치지 않게)
    for rule in templates["assign"]:
        pat = re.compile(rule["match"])
        for by_eval in (False, True):
            for _, node in leaves:
                if used.get(rule["kind"], 0) >= rule["max"]:
                    break
                text = " ".join(names.get(e, "") for e in node.eval_items) if by_eval else node.title
                if text and pat.search(text) and rule["kind"] not in out.get(node.id, []):
                    if by_eval and any(rule["kind"] in v for v in out.values()):
                        continue
                    variant = (rule["kind"], "체계" if rule["kind"] == "org" and "체계" in node.title else "")
                    if variant in variants:
                        continue
                    variants.add(variant)
                    out.setdefault(node.id, []).append(rule["kind"])
                    used[rule["kind"]] = used.get(rule["kind"], 0) + 1
    for kind, canon in (templates.get("fallback") or {}).items():
        if used.get(kind):
            continue
        target = next((n for ch, n in leaves if ch.canonical == canon), None)
        if target is not None:
            out.setdefault(target.id, []).append(kind)
    return out


# ---------------------------------------------------------------- 사업기간

_MONTHS = re.compile(r"(\d{1,2})\s*개월")
_DAYS = re.compile(r"(\d{2,4})\s*일(?!\s*이내\s*착수)")
_RANGE = re.compile(r"(20\d{2})\s*[.\-년/]\s*(\d{1,2})\D{0,8}?[~∼\-–]\s*(?:(20\d{2})\s*[.\-년/]\s*)?(\d{1,2})")


def project_months(rfp: Rfp) -> tuple[int, str | None]:
    """(개월 수, 가정). RFP 사업기간을 못 읽으면 6개월로 두고 가정을 돌려준다."""
    text = rfp.notice.period.value if rfp.notice.period else ""
    if text:
        if m := _MONTHS.search(text):
            return max(1, int(m.group(1))), None
        if m := _RANGE.search(text):
            y1, m1, y2, m2 = int(m.group(1)), int(m.group(2)), int(m.group(3) or m.group(1)), int(m.group(4))
            months = (y2 - y1) * 12 + (m2 - m1) + 1
            if 1 <= months <= 60:
                return months, None
        if m := _DAYS.search(text):
            return max(1, round(int(m.group(1)) / 30)), None
    return 6, "RFP에서 사업기간을 읽지 못해 6개월로 가정했습니다 — 일정 도식의 기간을 고치세요"


def _half(x: float) -> float:
    return round(x * 2) / 2


# ---------------------------------------------------------------- 종류별 스펙

def build_gantt(ctx: BuildContext, fig_id: str) -> DiagramSpec:
    months, assumption = project_months(ctx.rfp)
    pt = ctx.project_type
    spec = DiagramSpec(id=fig_id, kind="gantt", title="사업 추진 일정(안)", months=months)
    for ph in pt["phases"]:
        s, e = _half(ph["start"] * months), _half(ph["end"] * months)
        spec.tasks.append(GanttTask(label=ph["label"], start=s, end=max(e, s + 0.5), group="단계"))
    sup = pt.get("support")
    if sup:
        spec.tasks.append(GanttTask(label=sup["label"], start=_half(sup["start"] * months), end=_half(sup["end"] * months),
                                    group="관리"))
    for ms in pt.get("milestones") or []:
        at = _half(ms["at"] * months)
        spec.tasks.append(GanttTask(label=ms["label"], start=at, end=at, group="보고", milestone=True))
    if assumption:
        spec.assumptions.append(assumption)
    spec.assumptions.append(f"단계 구간은 '{pt['key']}' 유형 템플릿의 비율로 만든 초안입니다 — 수행계획에 맞춰 고치세요")
    return spec


def build_wbs(ctx: BuildContext, fig_id: str) -> DiagramSpec:
    pt = ctx.project_type
    spec = DiagramSpec(id=fig_id, kind="wbs", title="작업 분할 구조(WBS)")
    spec.nodes.append(DiagramNode(id="root", label="본 사업"))
    for i, ph in enumerate(pt["phases"], start=1):
        pid = f"p{i}"
        spec.nodes.append(DiagramNode(id=pid, label=f"{i}. {ph['label']}", parent="root"))
        for j, act in enumerate((pt.get("activities") or {}).get(ph["label"], []), start=1):
            spec.nodes.append(DiagramNode(id=f"{pid}-{j}", label=f"{i}.{j} {act}", parent=pid))
    spec.assumptions.append(f"WBS는 '{pt['key']}' 유형 템플릿으로 만든 초안입니다 — 과업 범위에 맞춰 고치세요")
    return spec


def build_flow(ctx: BuildContext, fig_id: str) -> DiagramSpec:
    pt = ctx.project_type
    spec = DiagramSpec(id=fig_id, kind="flow", title="단계별 추진 절차와 주요 산출물")
    for i, ph in enumerate(pt["phases"], start=1):
        spec.nodes.append(DiagramNode(id=f"p{i}", label=ph["label"], note="\n".join(ph.get("outputs") or [])))
    spec.assumptions.append(f"추진 절차·산출물은 '{pt['key']}' 유형 템플릿입니다 — RFP 산출물 목록과 맞추세요")
    return spec


_HEADER_WORDS = {"비고", "구분", "내용", "항목", "기타"}
_PM = re.compile(r"\bPM\b|사업\s*관리|총괄|사업\s*책임", re.I)
_QA = re.compile(r"\bQA\b|품질", re.I)


def _person_note(people: list) -> str:
    if len(people) == 1:
        p = people[0]
        parts = [p.grade] + ([f"{p.years:g}년"] if p.years is not None else [])
        return " · ".join(x for x in parts if x)
    grades: OrderedDict[str, int] = OrderedDict()
    for p in people:
        grades[p.grade or "등급 미정"] = grades.get(p.grade or "등급 미정", 0) + 1
    return f"{len(people)}명 (" + ", ".join(f"{g} {n}" for g, n in grades.items()) + ")"


def build_org(ctx: BuildContext, fig_id: str, section_title: str) -> DiagramSpec:
    governance = bool(re.search(r"체계", section_title))
    spec = DiagramSpec(id=fig_id, kind="org", title="사업 추진 체계" if governance else "사업 수행 조직")
    people = list(ctx.kb.people)
    pm = [p for p in people if _PM.search(p.role)]
    qa = [p for p in people if _QA.search(p.role) and p not in pm]
    rest = [p for p in people if p not in pm and p not in qa]
    spec.nodes.append(DiagramNode(id="pm", label="사업관리(PM)", note=_person_note(pm) if pm else ""))
    if governance:
        agency = ctx.rfp.notice.agency.value if ctx.rfp.notice.agency else ""
        if len(re.sub(r"\s+", "", agency)) < 2 or re.sub(r"\s+", "", agency) in _HEADER_WORDS or len(agency) > 30:
            agency = "발주기관"
        spec.nodes.append(DiagramNode(id="client", label=agency, group="external", note="사업 총괄·검수"))
        spec.edges.append(DiagramEdge(src="client", dst="pm", label="보고·협의", style="dashed"))
        if "감리" in ctx.rfp_text():
            spec.nodes.append(DiagramNode(id="audit", label="감리", group="external", note="단계별 감리"))
            spec.edges.append(DiagramEdge(src="audit", dst="pm", label="감리 대응", style="dashed"))
    for i, label in enumerate(ctx.templates.get("support_nodes") or [], start=1):
        spec.nodes.append(DiagramNode(id=f"sup{i}", label=label, parent="pm", group="support",
                                      note=_person_note(qa) if qa and i == 1 else ""))
    teams: OrderedDict[str, list] = OrderedDict()
    for p in rest:
        teams.setdefault(p.role.strip() or "기타", []).append(p)
    if teams:
        for i, (role, members) in enumerate(teams.items(), start=1):
            spec.nodes.append(DiagramNode(id=f"t{i}", label=role, parent="pm", note=_person_note(members)))
    else:
        for i, label in enumerate(ctx.templates.get("default_teams") or [], start=1):
            spec.nodes.append(DiagramNode(id=f"t{i}", label=label, parent="pm", note="[확인 필요: 투입 인력]"))
        spec.assumptions.append("KB에 투입 인력이 없어 일반 팀 구성으로 넣었습니다 — people.csv를 채우세요")
    return spec


def _short(name: str, limit: int = 20) -> str:
    s = re.sub(r"\s*(?:기능|구현|구축|개발|개선|고도화)\s*$", "", name.strip()) or name.strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _names(rfp: Rfp, prefixes: tuple[str, ...], limit: int) -> list[str]:
    seen: list[str] = []
    for r in rfp.requirements:
        if (r.prefix or r.id[:3]) in prefixes and r.name:
            s = _short(r.name)
            if s not in seen:
                seen.append(s)
    if len(seen) > limit:
        return seen[: limit - 1] + [f"외 {len(seen) - limit + 1}개"]
    return seen


def build_layers(ctx: BuildContext, fig_id: str) -> DiagramSpec:
    rfp = ctx.rfp
    text = ctx.rfp_text()
    spec = DiagramSpec(id=fig_id, kind="layers", title="목표 시스템 구성도(안)")
    users = [label for pat, label in ((r"모바일|앱", "모바일"), (r"포털|홈페이지|대국민|민원인", "사용자 웹"),
                                      (r"관리자", "관리자"), (r"외부\s*기관|유관\s*기관", "외부 기관"))
             if re.search(pat, text)] or ["내부 사용자", "관리자"]
    spec.layers.append(DiagramLayer(name="사용자", items=users))
    func = _names(rfp, ("SFR",), 8)
    spec.layers.append(DiagramLayer(name="업무 서비스", items=func or ["[확인 필요: 업무 기능]"]))
    if sir := _names(rfp, ("SIR",), 4):
        spec.layers.append(DiagramLayer(name="연계", items=sir))
    spec.layers.append(DiagramLayer(name="데이터", items=_names(rfp, ("DAR",), 4) or ["업무 DB"]))
    infra = _names(rfp, ("ECR", "HWR", "SWR"), 4)
    spec.layers.append(DiagramLayer(name="인프라", items=infra or ["WEB/WAS", "DBMS"]))
    if not infra:
        spec.assumptions.append("RFP에서 장비·SW 구성 요구사항을 찾지 못해 인프라 층을 일반 구성으로 넣었습니다")
    if ser := _names(rfp, ("SER",), 4):
        spec.layers.append(DiagramLayer(name="보안", items=ser, side=True))
    if not func:
        spec.assumptions.append("기능 요구사항(SFR)이 없어 업무 서비스 층을 비워 두었습니다")
    return spec


def build_figure(kind: str, ctx: BuildContext, section_id: str, section_title: str) -> DiagramSpec:
    fig_id = f"{section_id}-{kind}"
    if kind == "gantt":
        return build_gantt(ctx, fig_id)
    if kind == "wbs":
        return build_wbs(ctx, fig_id)
    if kind == "flow":
        return build_flow(ctx, fig_id)
    if kind == "org":
        return build_org(ctx, fig_id, section_title)
    if kind == "layers":
        return build_layers(ctx, fig_id)
    raise ValueError(f"모르는 도식 종류: {kind}")


__all__ = ["BuildContext", "build_figure", "load_templates", "plan_figures", "project_months"]
