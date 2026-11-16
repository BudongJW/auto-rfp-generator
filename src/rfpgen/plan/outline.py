"""목차 생성(설계서 7.4절).

우선순위: ① RFP 지정 목차(그대로, 바꾸지 않음) ② 평가표 부문·항목 순서 ③ 기본 템플릿(별지 제5호).
SW사업이면 상생협력·하도급 장이 없을 때 자동으로 넣는다. 평가항목은 이름 유사도로 절에 연결한다.
"""

from __future__ import annotations

import re

from ..profile import Profile
from ..schemas.plan import Outline, OutlineNode
from ..schemas.rfp import ExtractionReport, Rfp, TocNode

_ROMAN = ["Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ", "Ⅵ", "Ⅶ", "Ⅷ", "Ⅸ", "Ⅹ", "Ⅺ", "Ⅻ"]

# 장 제목 → 표준 장 키(기본 매핑과 쪽수 배분에 쓰인다). 위에서부터 먼저 맞는 규칙을 쓴다.
_CANONICAL_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("제안개요", re.compile(r"제안\s*개요|사업\s*개요|^개요")),
    ("제안업체일반", re.compile(r"업체\s*일반|일반\s*현황|제안사\s*일반|회사\s*개요|제안사\s*현황")),
    ("상생협력하도급", re.compile(r"상생|하도급")),
    ("증빙자료", re.compile(r"증빙|첨부|부록")),
    ("그밖의사항", re.compile(r"그\s*밖|기타|추가\s*제안")),
    ("성능및품질", re.compile(r"성능|품질")),
    ("프로젝트관리", re.compile(r"관리")),
    ("프로젝트지원", re.compile(r"지원")),
    ("전략및방법론", re.compile(r"전략|방법론|사업\s*이해")),
    ("기술및기능", re.compile(r"기술|기능|수행\s*계획|수행\s*기반|구축|시스템")),
]


def canonical(title: str) -> str | None:
    for key, pat in _CANONICAL_RULES:
        if pat.search(title):
            return key
    return None


def _norm(text: str) -> str:
    return re.sub(r"[\s·ㆍ/()\[\]（）,]+", "", text or "")


def _bigrams(text: str) -> set[str]:
    t = _norm(text)
    return {t[i:i + 2] for i in range(len(t) - 1)} or ({t} if t else set())


def similarity(a: str, b: str) -> float:
    """문자 2-gram 자카드 유사도. 한쪽이 다른 쪽을 포함하면 0.9 이상."""
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.9
    ba, bb = _bigrams(a), _bigrams(b)
    return len(ba & bb) / len(ba | bb)


class _Numberer:
    def __init__(self) -> None:
        self.n = 0

    def chapter(self) -> str:
        self.n += 1
        return _ROMAN[self.n - 1] if self.n <= len(_ROMAN) else str(self.n)


def _node(node_id: str, number: str, title: str, level: int, origin: str) -> OutlineNode:
    return OutlineNode(id=node_id, number=number, title=title, level=level,
                       canonical=canonical(title) if level == 1 else None, origin=origin)  # type: ignore[arg-type]


def _from_toc(toc: list[TocNode]) -> list[OutlineNode]:
    chapters: list[OutlineNode] = []
    for ci, ch in enumerate(toc, start=1):
        node = _node(f"S-{ci}", f"{ch.number}.", ch.title, 1, "prescribed")
        for si, sub in enumerate(ch.children, start=1):
            node.children.append(_node(f"S-{ci}-{si}", f"{ch.number}.{sub.number}", sub.title, 2, "prescribed"))
        chapters.append(node)
    return chapters


def _fixed_chapters(profile: Profile, start: _Numberer) -> list[OutlineNode]:
    out: list[OutlineNode] = []
    for spec in profile.value("outline.fixed_chapters"):
        num = start.chapter()
        ci = len(out) + 1
        node = _node(f"S-{ci}", f"{num}.", spec["title"], 1, "fixed")
        node.canonical = spec["key"]
        for si, title in enumerate(spec.get("sections", []), start=1):
            node.children.append(_node(f"S-{ci}-{si}", f"{num}.{si}", title, 2, "fixed"))
        out.append(node)
    return out


def _from_eval(rfp: Rfp, profile: Profile, report: ExtractionReport) -> list[OutlineNode]:
    numberer = _Numberer()
    chapters = _fixed_chapters(profile, numberer)
    for area in rfp.evaluation.areas:
        if area.kind == "정량":
            continue
        ci = len(chapters) + 1
        num = numberer.chapter()
        node = _node(f"S-{ci}", f"{num}.", area.name, 1, "eval_table")
        for si, item in enumerate(area.items, start=1):
            sec = _node(f"S-{ci}-{si}", f"{num}.{si}", item.name, 2, "eval_table")
            sec.eval_items.append(item.id)
            node.children.append(sec)
        chapters.append(node)
    _ensure_mandatory(chapters, profile, numberer, "eval_table")
    return chapters


def _from_template(profile: Profile) -> list[OutlineNode]:
    numberer = _Numberer()
    chapters = _fixed_chapters(profile, numberer)
    for spec in profile.value("outline.default_template"):
        ci = len(chapters) + 1
        num = numberer.chapter()
        node = _node(f"S-{ci}", f"{num}.", spec["title"], 1, "default_template")
        node.canonical = spec["key"]
        for si, title in enumerate(spec.get("sections", []), start=1):
            node.children.append(_node(f"S-{ci}-{si}", f"{num}.{si}", title, 2, "default_template"))
        chapters.append(node)
    return chapters


def _ensure_mandatory(chapters: list[OutlineNode], profile: Profile, numberer: _Numberer, origin: str) -> None:
    if not profile.value("outline.is_sw_project"):
        return
    present = {c.canonical for c in chapters}
    templates = {spec["key"]: spec for spec in profile.value("outline.default_template")}
    for key in profile.value("outline.mandatory_chapters"):
        if key in present or key not in templates:
            continue
        spec = templates[key]
        ci = len(chapters) + 1
        num = numberer.chapter()
        node = _node(f"S-{ci}", f"{num}.", spec["title"], 1, origin)
        node.canonical = key
        for si, title in enumerate(spec.get("sections", []), start=1):
            node.children.append(_node(f"S-{ci}-{si}", f"{num}.{si}", title, 2, origin))
        chapters.append(node)


def _attach_eval_items(chapters: list[OutlineNode], rfp: Rfp, report: ExtractionReport,
                       threshold: float = 0.5) -> None:
    """정성 평가항목을 이름이 가장 비슷한 절(들)에 연결한다(지정 목차·기본 템플릿용).

    '기능/컨설팅 요구사항'처럼 여러 절을 묶은 항목은 조각별로도 찾고, 끝내 못 찾으면
    부문 이름이나 표준 장 키가 같은 장에 붙인다.
    """
    pairs = [(c, s) for c in chapters for s in (c.children or [c])]
    sections = [s for _, s in pairs]
    for area in rfp.evaluation.areas:
        if area.kind == "정량":
            continue
        for item in area.items:
            scored = sorted(((similarity(item.name, s.title), s) for s in sections), key=lambda t: -t[0])
            best = [s for score, s in scored if score >= threshold and score >= scored[0][0] - 0.05] if scored else []
            parts = [p.strip() for p in re.split(r"[/,·ㆍ]", item.name) if len(_norm(p)) >= 2]
            if len(parts) > 1:
                suffix = "요구사항" if "요구사항" in item.name else ""
                for p in parts:
                    cand = p if p.endswith(suffix) else p + suffix
                    top = max(((similarity(cand, s.title), s) for s in sections), key=lambda t: t[0], default=None)
                    if top and top[0] >= 0.8 and top[1] not in best:
                        best.append(top[1])
            if not best:
                key = canonical(area.name)
                chapter = next((c for c in chapters if similarity(area.name, c.title) >= 0.6), None) or next(
                    (c for c in chapters if key and c.canonical == key), None)
                if chapter is not None:
                    best = chapter.children[:1] if len(chapter.children) == 1 else [chapter]
            if not best:
                report.add("PLAN-EVAL-UNMAPPED", "warning",
                           f"평가항목 '{item.name}'에 맞는 목차 절을 찾지 못했습니다 — 수동 연결 필요")
                continue
            for s in best:
                if item.id not in s.eval_items:
                    s.eval_items.append(item.id)


def build_outline(rfp: Rfp, profile: Profile, report: ExtractionReport) -> Outline:
    toc = rfp.guideline.prescribed_toc
    if toc is not None and toc.value:
        outline = Outline(origin="prescribed", chapters=_from_toc(toc.value))
        _attach_eval_items(outline.chapters, rfp, report)
        if profile.value("outline.is_sw_project") and not any(
            c.canonical == "상생협력하도급" for c in outline.chapters
        ):
            report.add("PLAN-MANDATORY-MISSING", "warning",
                       "지정 목차에 상생협력·하도급 장이 없습니다 — 지정 목차를 바꾸지 않고 해당 내용을 넣을 위치를 확인하세요")
    elif rfp.evaluation.qualitative_items():
        outline = Outline(origin="eval_table", chapters=_from_eval(rfp, profile, report))
    else:
        outline = Outline(origin="default_template", chapters=_from_template(profile))
        _attach_eval_items(outline.chapters, rfp, report)

    # 평가 질문을 절 체크리스트로
    items = {it.id: it for it in rfp.evaluation.items()}
    for node in outline.walk():
        for iid in node.eval_items:
            for crit in items[iid].criteria:
                if crit not in node.checklist:
                    node.checklist.append(crit)
    return outline
