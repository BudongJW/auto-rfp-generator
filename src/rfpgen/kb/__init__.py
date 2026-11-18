"""회사 지식베이스(KB) 읽기·쓰기(설계서 6.5절, 16장 Q6: YAML/CSV 입력).

폴더 구조
  company.yaml       identity(블라인드 사전), company(별지 서식용 기본정보), facts(수치 근거)
  projects.csv       유사사업 실적
  people.csv         투입 인력(역할·등급·경력 — 실명·연락처는 넣지 않는다)
  certifications.csv 인증
  content/*.md       재사용 후보 문단(앞머리 YAML: title, tags, source, won)
  private/           (선택) people.csv(id,name) 실명, forms.yaml(values: 이름표→값) — 별지 서식에만 쓰고
                     LLM·보고서·로그로 보내지 않는다. 저장소에 올리지 않는다(.gitignore)
"""

from __future__ import annotations

import csv
import datetime as dt
import re
from pathlib import Path

import yaml

from ..schemas.kb import Certification, CompanyInfo, CompanyKB, ContentBlock, Fact, Identity, Person, ReferenceProject

_LIST_SEP = re.compile(r"\s*[;|]\s*")


def _list(v: str | None) -> list[str]:
    return [x for x in _LIST_SEP.split(v or "") if x]


def _date(v) -> dt.date | None:
    if not v:
        return None
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v).strip())


def _rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(f)]


def _front_matter(text: str) -> tuple[dict, str]:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            meta = yaml.safe_load(text[3:end]) or {}
            return (meta if isinstance(meta, dict) else {}), text[end + 4:].lstrip("\n")
    return {}, text


def load_kb(folder: Path) -> CompanyKB:
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"KB 폴더가 없습니다: {folder}")
    company = yaml.safe_load((folder / "company.yaml").read_text(encoding="utf-8")) if (folder / "company.yaml").exists() else {}
    company = company or {}
    kb = CompanyKB(
        identity=Identity(**(company.get("identity") or {})),
        company=CompanyInfo(**{k: str(v) for k, v in (company.get("company") or {}).items()}),
        facts=[Fact(**{**f, "id": str(f["id"]), "value": str(f["value"]),
                       "valid_until": _date(f.get("valid_until"))}) for f in company.get("facts") or []],
    )
    for r in _rows(folder / "projects.csv"):
        kb.projects.append(ReferenceProject(
            id=r["id"], name=r.get("name", ""), client=r.get("client", ""), start=r.get("start", ""), end=r.get("end", ""),
            amount_krw=int(r["amount_krw"].replace(",", "")) if r.get("amount_krw") else None,
            role=r.get("role", ""), tech=_list(r.get("tech")), evidence=r.get("evidence", "")))
    for r in _rows(folder / "people.csv"):
        kb.people.append(Person(
            id=r["id"], role=r.get("role", ""), grade=r.get("grade", ""),
            years=float(r["years"]) if r.get("years") else None, skills=_list(r.get("skills")), certs=_list(r.get("certs"))))
    for r in _rows(folder / "certifications.csv"):
        kb.certifications.append(Certification(id=r["id"], name=r.get("name", ""), number=r.get("number", ""),
                                               valid_until=_date(r.get("valid_until"))))
    for i, path in enumerate(sorted((folder / "content").glob("*.md")) if (folder / "content").is_dir() else [], start=1):
        meta, body = _front_matter(path.read_text(encoding="utf-8"))
        kb.content.append(ContentBlock(id=str(meta.get("id") or f"K-{i:03d}"), title=str(meta.get("title") or path.stem),
                                       tags=[str(t) for t in meta.get("tags") or []], source=str(meta.get("source") or ""),
                                       won=meta.get("won"), text=body.strip()))
    return kb


def load_private_names(folder: Path) -> dict[str, str]:
    """private/people.csv(id,name): 별지 서식의 '성명' 칸에만 쓴다. LLM·보고서·로그로 보내지 않는다."""
    return {r["id"]: r.get("name", "") for r in _rows(Path(folder) / "private" / "people.csv") if r.get("id")}


def check_kb(kb: CompanyKB, today: dt.date | None = None) -> list[str]:
    """KB 품질 경고 목록."""
    warnings: list[str] = []
    ids: dict[str, int] = {}
    for coll in (kb.facts, kb.projects, kb.people, kb.certifications, kb.content):
        for e in coll:
            ids[e.id] = ids.get(e.id, 0) + 1
    dup = [k for k, n in ids.items() if n > 1]
    if dup:
        warnings.append(f"ID가 겹칩니다: {', '.join(dup)}")
    for f in kb.facts:
        if re.search(r"\d", f.label):
            warnings.append(f"{f.id}: 설명(label)에 숫자가 있습니다 — 수치는 value에만 두세요(설명은 LLM에 보일 수 있음)")
    for eid in kb.expired(today):
        warnings.append(f"{eid}: 유효기간이 지났습니다")
    if not kb.identity.name:
        warnings.append("identity.name(회사명)이 비어 있습니다 — 블라인드 점검을 할 수 없습니다")
    return warnings


_TEMPLATE_COMPANY = """\
# 회사 지식베이스 — 제안서 본문에 들어가는 수치·사실의 유일한 출처입니다.
# LLM에는 id와 label만 보일 수 있고(--llm-share-kb), value는 절대 보내지 않습니다.
identity:                 # 블라인드 점검 사전: 블라인드 평가에서 제안서·파일 정보에 나오면 안 되는 표기
  name: (주)예시정보
  name_en: Yesi Info
  aliases: [예시정보, YESI]
  domains: [yesi.co.kr]
  ceo: 홍길동
  products: [YesiFlow]
company:                  # 별지 서식(입찰참가신청서·일반현황 등)에 들어가는 기본정보 — LLM에 보내지 않음
  biz_no: 123-45-67890
  corp_no: 110111-1234567
  address: 서울특별시 ○○구 ○○로 1
  phone: 02-123-4567
  fax: 02-123-4568
  email: bid@yesi.co.kr
  established: 2010-03-02
  capital: 10억 원
  employees: 120명
facts:
  - id: F-001
    label: 최근 공공 SW 유사사업 수행 건수(기간은 증빙 기준)
    value: 12건
    evidence: 실적증명서 묶음.pdf
  - id: F-002
    label: 정규직 개발 인력 수
    value: 85명
    evidence: 4대보험 가입자 명부
    valid_until: 2027-06-30
"""

_TEMPLATE_FILES = {
    "projects.csv": "id,name,client,start,end,amount_krw,role,tech,evidence\n"
                    "P-001,통합민원시스템 구축,○○시청,2024-03,2024-12,1250000000,주관,Java;eGovFrame;PostgreSQL,실적증명서_P-001.pdf\n",
    "people.csv": "id,role,grade,years,skills,certs\n"
                  "H-001,PM,특급,18,사업관리;공공SI,정보관리기술사;PMP\n"
                  "H-002,아키텍트,고급,12,MSA;클라우드,정보처리기사\n",
    "certifications.csv": "id,name,number,valid_until\nC-001,GS인증 1등급(YesiFlow),GS-24-0001,2027-03-31\n",
    "private/people.csv": "id,name\nH-001,홍○○\nH-002,김○○\n",
    "private/README.md": "# 개인정보(실명)\n\n이 폴더의 파일은 별지 서식의 '성명' 칸을 채울 때만 씁니다.\n"
                         "LLM·보고서·로그로 보내지 않습니다. 저장소에 올리지 마세요.\n",
    "content/사업이해도_예시.md": "---\ntitle: 사업 이해도 — 민원 시스템 고도화\ntags: [사업이해도, 전략및방법론]\n"
                               "source: 2025 ○○시 민원 고도화 제안서\nwon: true\n---\n"
                               "□ 사업 환경\n○ 민원 처리 전 과정을 온라인으로 전환하려는 정책 방향에 맞춰 …\n",
}


def init_kb(folder: Path) -> list[Path]:
    """예시 KB 폴더를 만든다(이미 있는 파일은 건드리지 않는다)."""
    folder = Path(folder)
    (folder / "content").mkdir(parents=True, exist_ok=True)
    (folder / "private").mkdir(parents=True, exist_ok=True)
    made: list[Path] = []
    targets = {"company.yaml": _TEMPLATE_COMPANY, **_TEMPLATE_FILES}
    for name, text in targets.items():
        p = folder / name
        if not p.exists():
            p.write_text(text, encoding="utf-8")
            made.append(p)
    return made


__all__ = ["check_kb", "init_kb", "load_kb", "load_private_names"]
