"""별지 서식 채우기 결과 스키마(설계서 7.9절 '별지 채우기', 7.10절 문서구분).

원칙
- 원본 양식의 레이아웃은 바꾸지 않고 빈칸에 값만 넣는다. 표가 모자랄 때만 같은 서식의 행을 복제해 늘린다.
- 값의 출처는 KB(회사 기본정보·실적·인력·인증), RFP(사업명·공고번호), 사람이 준 값(private/forms.yaml)뿐이다.
- 개인 실명(private/people.csv)은 서식 파일에만 들어가고 보고서·로그에는 가린 값으로 남는다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .draft import CheckFinding

FormDocType = Literal["정성제안서", "정량제안서", "하도급계획서", "기타문서"]
FillSource = Literal["kb", "rfp", "private", "user", "date"]


class FormFill(BaseModel):
    """채운 칸 하나."""

    where: str                      # "표1 r2c1", "문단 12", "표2 행 3"
    label: str                      # 서식의 이름표(열 머리글)
    field: str                      # identity.name, company.biz_no, projects[P-001].name, date …
    source: FillSource
    value: str                      # 보고서용 값(실명은 가린다)


class FormResult(BaseModel):
    key: str                        # "1", "4-2"
    form_no: str                    # "별지 제1호"
    title: str
    source_file: str
    doc_type: FormDocType = "기타문서"
    blind: bool = False             # 블라인드 평가 문서(지정 목차가 이 서식을 가리킴) — 회사 식별 정보를 넣지 않는다
    output: str = ""                # 프로젝트 기준 상대 경로
    fills: list[FormFill] = Field(default_factory=list)
    added_rows: int = 0
    findings: list[CheckFinding] = Field(default_factory=list)
    external: bool = False          # 발급기관이 확인·발급하는 서식(실적증명서 등) — 제출 묶음에 넣지 않는다
    requests: list[str] = Field(default_factory=list)   # 발급 요청용 초안(실적마다 한 장, 프로젝트 기준 상대 경로)


class FormsReport(BaseModel):
    schema_version: str = "1"
    run_id: str
    date: str                       # 서식에 넣은 날짜(YYYY-MM-DD)
    forms: list[FormResult] = Field(default_factory=list)
    findings: list[CheckFinding] = Field(default_factory=list)   # 서식 밖(누락 서식·PDF 서식 등)
