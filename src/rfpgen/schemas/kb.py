"""회사 지식베이스(KB) 스키마(설계서 6.5절).

원칙
- 본문에 들어가는 모든 수치(실적 금액, 인원, 연수 등)의 유일한 출처는 KB다(원칙 P2).
- LLM에는 값을 보내지 않는다. LLM은 '{{fact:F-001}}', '{{kb:P-001.amount}}' 같은 토큰만 쓰고 코드가 값을 넣는다.
- 인력 실명·연락처는 KB 형식에 두지 않는다(역할·등급·경력만). 블라인드 점검용 회사 식별어는 Identity에 둔다.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class Identity(BaseModel):
    """블라인드 점검 사전: 이 문자열이 제안서·메타데이터에 나오면 안 된다(블라인드 평가 시)."""

    name: str = ""
    name_en: str = ""
    aliases: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    ceo: str = ""
    products: list[str] = Field(default_factory=list)

    def terms(self) -> list[str]:
        out = [self.name, self.name_en, *self.aliases, *self.domains, self.ceo, *self.products]
        return sorted({t.strip() for t in out if t and len(t.strip()) >= 2}, key=len, reverse=True)


class CompanyInfo(BaseModel):
    """별지 서식(입찰참가신청서·일반현황 등)에 들어가는 회사 기본정보. LLM에는 보내지 않는다."""

    biz_no: str = ""             # 사업자등록번호
    corp_no: str = ""            # 법인등록번호
    address: str = ""
    phone: str = ""
    fax: str = ""
    email: str = ""
    homepage: str = ""
    established: str = ""        # 설립일
    capital: str = ""            # 자본금(표기 그대로)
    employees: str = ""          # 종업원 수(표기 그대로)


class Fact(BaseModel):
    id: str
    label: str                       # LLM에 보이는 설명(값은 보내지 않는다)
    value: str                       # 본문에 들어갈 값(예: "12건", "45억 원")
    kind: str = "수치"
    evidence: str = ""
    valid_until: dt.date | None = None


class ReferenceProject(BaseModel):
    id: str
    name: str
    client: str = ""
    start: str = ""
    end: str = ""
    amount_krw: int | None = None
    role: str = ""                   # 주관/참여
    tech: list[str] = Field(default_factory=list)
    evidence: str = ""


class Person(BaseModel):
    id: str
    role: str                        # PM, 아키텍트, 개발자 …
    grade: str = ""                  # 특급·고급·중급·초급
    years: float | None = None
    skills: list[str] = Field(default_factory=list)
    certs: list[str] = Field(default_factory=list)


class Certification(BaseModel):
    id: str
    name: str
    number: str = ""
    valid_until: dt.date | None = None


class ContentBlock(BaseModel):
    """과거 제안서 절 등 재사용 후보 텍스트(content/*.md)."""

    id: str
    title: str
    tags: list[str] = Field(default_factory=list)
    source: str = ""
    won: bool | None = None
    text: str = ""


class CompanyKB(BaseModel):
    schema_version: str = "1"
    identity: Identity = Field(default_factory=Identity)
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    facts: list[Fact] = Field(default_factory=list)
    projects: list[ReferenceProject] = Field(default_factory=list)
    people: list[Person] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    content: list[ContentBlock] = Field(default_factory=list)

    def resolve(self, token: str) -> str | None:
        """'F-001' 또는 'P-001.amount' 형식의 토큰 값을 돌려준다. 없으면 None."""
        if "." not in token:
            for f in self.facts:
                if f.id == token:
                    return f.value
            return None
        entity, field = token.split(".", 1)
        for coll in (self.projects, self.people, self.certifications):
            for e in coll:
                if e.id == entity:
                    v = getattr(e, field, None)
                    if v is None or v == "" or v == []:
                        return None
                    if field == "amount_krw" and isinstance(v, int):
                        return _krw(v)
                    if isinstance(v, list):
                        return ", ".join(str(x) for x in v)
                    if isinstance(v, float):
                        return f"{v:g}"
                    return str(v)
        return None

    def expired(self, today: dt.date | None = None) -> list[str]:
        today = today or dt.date.today()
        out = [f.id for f in self.facts if f.valid_until and f.valid_until < today]
        out += [c.id for c in self.certifications if c.valid_until and c.valid_until < today]
        return out


def _krw(v: int) -> str:
    if v >= 10**8:
        eok = v / 10**8
        return f"{eok:,.1f}억 원".replace(".0억", "억")
    if v >= 10**4:
        return f"{v // 10**4:,}만 원"
    return f"{v:,}원"
