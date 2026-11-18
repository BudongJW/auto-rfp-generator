"""체험용 가상 제안요청서(rfpgen sample): 실제 RFP 없이 전체 흐름을 해 볼 수 있게 한다.

공개 RFP 형식(요구사항 총괄표·상세 정의서, 정량·정성 평가표, 작성지침, 별지 서식)을 흉내 낸 가상 문서다.
테스트도 같은 데이터를 쓴다(tests/conftest.py). 실제 기관·회사와 관계없다.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

OVERVIEW_LINES = [
    "Ⅰ. 사업 개요",
    "1. 추진 배경",
    "○ 현행 통합민원시스템은 2019년 구축 이후 7년간 운영되어 화면 구조가 노후화되고, 첨부파일 용량 제한(10MB)으로 "
    "민원인이 서류를 나누어 내는 불편이 지속됨",
    "○ 민원 신청의 모바일 비중이 늘었으나 모바일 화면이 최적화되어 있지 않아 신청 중도 포기가 발생함",
    "2. 사업 목적",
    "○ 민원 신청·조회 서비스를 개선하여 대국민 민원서비스 편의성 향상",
    "○ 처리 단계 공개와 알림으로 민원 처리 업무 효율화",
    "○ 개인정보 암호화와 응답 시간 개선으로 안전하고 안정적인 서비스 제공",
    "3. 현황",
    "○ 발주기관: 가상시 민원봉사과",
    "○ 운영 환경: WEB/WAS 이중화, DBMS 1식, 민원 담당 공무원 약 120명 사용",
    "○ 연계: 행정정보 공동이용 시스템, 문자·이메일 발송 서비스",
]

GUIDE_LINES = [
    "Ⅴ. 제안서 작성 안내",
    "1. 제안서 작성 지침",
    "○ 사업명: 2026년 통합민원시스템 고도화 사업",
    "○ 사업예산: 금 1,250,000,000원(부가가치세 포함)",
    "○ 사업기간: 계약일로부터 8개월",
    "○ 본 사업은 「국가를 당사자로 하는 계약에 관한 법률 시행령」 제43조에 따른 협상에 의한 계약으로 진행",
    "○ 기술능력평가(90%)와 입찰가격평가(10%)를 합산하여 종합평가점수를 산정",
    "○ 제안서는 A4 용지 세로 방향으로 작성하며, 제안서 본문은 100쪽 이내로 작성(표지, 목차, 간지 제외)",
    "○ 요약 제안서는 30페이지 이내로 작성",
    "○ 제안서 본문 글자 크기는 13pt 이상, 표 안의 글자는 12pt 이상으로 작성",
    "○ 제안서류 일체는 PDF 파일 형식으로 제출하여야 하며, 총 용량은 300MB를 초과할 수 없음",
    "○ 제안서에는 업체명, 로고 등 제안사를 식별할 수 있는 표시를 하여서는 안 됨(블라인드 평가)",
    "○ 제안 발표 시간은 20분, 질의응답 10분으로 하며 사업수행책임자(PM)가 직접 발표",
]

SUMMARY_TABLE = [
    ["구분", "요구사항 고유번호", "요구사항 명칭"],
    ["기능", "SFR-001", "민원 신청 관리"],
    [None, "SFR-002", "민원 처리 현황 조회"],
    ["보안", "SER-001", "개인정보 암호화"],
    ["성능", "PER-001", "응답 시간"],
    ["관리", "PMR-001", "사업 관리"],
]
SUMMARY_SPANS = {(1, 0): (2, 1)}

DECLARED_TABLE = [
    ["분류", "ID 부여규칙", "요구사항수"],
    ["기능 요구사항", "SFR-요구사항ID", "2개"],
    ["보안 요구사항", "SER-요구사항ID", "1개"],
    ["성능 요구사항", "PER-요구사항ID", "1개"],
    ["프로젝트 관리 요구사항", "PMR-요구사항ID", "1개"],
]


def detail_table(cat: str, rid: str, name: str, definition: str, details: str) -> tuple[list, dict]:
    rows = [
        ["요구사항 분류", None, cat],
        ["요구사항 고유번호", None, rid],
        ["요구사항 명칭", None, name],
        ["요구사항 상세설명", "정의", definition],
        [None, "세부내용", details],
        ["산출정보", None, "요구사항 정의서, 화면 설계서"],
    ]
    spans = {(0, 0): (1, 2), (1, 0): (1, 2), (2, 0): (1, 2), (3, 0): (2, 1), (5, 0): (1, 2)}
    return rows, spans


DETAILS = [
    ("기능 요구사항", "SFR-001", "민원 신청 관리", "온라인 민원 신청 기능을 구축한다",
     "□ 민원 신청\n- 민원 유형별 신청서 작성 기능\n- 첨부파일 업로드(최대 100MB)\n- 신청 결과 알림(문자, 이메일)\n- 임시저장 기능"),
    ("기능 요구사항", "SFR-002", "민원 처리 현황 조회", "민원 처리 현황을 조회한다", "- 처리 단계 조회 등"),
    ("보안 요구사항", "SER-001", "개인정보 암호화", "개인정보를 암호화한다",
     "- 주민등록번호 등 고유식별정보 암호화\n- 전송 구간 암호화(TLS 1.2 이상)"),
    ("성능 요구사항", "PER-001", "응답 시간", "주요 화면 응답 시간 기준",
     "- 주요 화면 3초 이내 응답\n- 동시 사용자 500명 이상 처리"),
    ("프로젝트 관리 요구사항", "PMR-001", "사업 관리", "사업 관리 방안을 제시한다",
     "- 원활한 사업 관리 방안 제시\n- 필요시 주간 보고"),
]

EVAL_QUANT = [
    ["평가부문", "평가항목", "평가요소", "배점한도"],
    ["수행능력", "유사사업 수행실적", "- 최근 3년 유사사업 실적", "10"],
    [None, "참여인력", "- 투입인력 등급과 경력", "10"],
    ["소계", None, None, "20"],
]
EVAL_QUANT_SPANS = {(1, 0): (2, 1), (3, 0): (1, 3)}

EVAL_QUAL = [
    ["평가부문", "평가항목", "평가요소", "배점한도"],
    ["전략 및 방법론", "", "", "20"],
    [None, "사업 이해도", "- 사업의 목표와 범위를 정확히 이해하고 있는가", "10"],
    [None, "추진 전략", "- 사업 특성을 고려한 추진 전략을 제시하였는가", "10"],
    ["기술 및 기능", "", "", "25"],
    [None, "기능 요구사항", "- 기능 요구사항 구현 방안이 구체적인가", "15"],
    [None, "보안 요구사항", "- 보안 요구사항 이행 방안이 적절한가", "10"],
    ["성능 및 품질", "성능 요구사항", "- 성능 목표 달성 방안", "10"],
    ["프로젝트 관리", "사업 관리", "- 일정·위험 관리 방안", "10"],
    ["상생협력", "상생협력 및 하도급", "- 중소기업 참여 및 하도급 계획", "5"],
    ["소계", None, None, "70"],
]
EVAL_QUAL_SPANS = {(1, 0): (3, 1), (4, 0): (3, 1), (10, 0): (1, 3)}


def add_table(doc, rows: list[list[str | None]], spans: dict[tuple[int, int], tuple[int, int]]) -> None:
    n_rows, n_cols = len(rows), max(len(r) for r in rows)
    t = doc.add_table(n_rows, n_cols)
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            if text:
                t.cell(r, c).text = text
    # 병합은 오른쪽·아래쪽부터 해야 앞쪽 셀 좌표가 흔들리지 않는다
    for (r, c), (rs, cs) in sorted(spans.items(), reverse=True):
        if rs > 1 or cs > 1:
            t.merge_cells(r, c, r + rs - 1, c + cs - 1)



_hwpx_table = add_table      # 테스트 호환 이름


def _add_forms(doc) -> None:
    """별지 서식 예시: 입찰참가신청서(이름표 칸), 청렴서약서(쪽 테두리 표), 유사사업 실적·참여인력(목록 표), 하도급 계획서."""
    doc.add_paragraph("Ⅵ. 제출 서식")
    doc.add_paragraph("[별지 제1호서식]")
    doc.add_paragraph("입 찰 참 가 신 청 서")
    add_table(doc, [["상호", "", "대표자", "      (인)"], ["사업자등록번호", "", "법인등록번호", ""],
                    ["주소", "", None, None], ["전화번호", "", "팩스번호", ""], ["입찰건명", "", None, None]],
              {(2, 1): (1, 3), (4, 1): (1, 3)})
    doc.add_paragraph("위와 같이 입찰에 참가하고자 신청합니다.")
    doc.add_paragraph("2026.     .     .")
    doc.add_paragraph("신청인  상    호 :")
    doc.add_paragraph("대 표 자 :              (인)")
    frame = doc.add_table(1, 1)
    cell = frame.cell(0, 0)
    cell.text = "[별지 제2호서식]"
    for line in ("청 렴 서 약 서", "당사는 이 입찰에 참가하면서 다음 사항을 지킬 것을 서약합니다.",
                 "     년     월     일", "서약자  업 체 명 :", "대 표 자 :            (인)"):
        cell.add_paragraph(line)
    doc.add_paragraph("[별지 제4호서식] 유사사업 수행실적")
    add_table(doc, [["순번", "사업명", "발주기관", "사업기간", "계약금액(백만원)", "참여형태"],
                    ["1", "", "", "", "", ""], ["합계", "", "", "", "", ""]], {})
    doc.add_paragraph("[별지 제7호서식]")
    doc.add_paragraph("참여인력 현황")
    add_table(doc, [["성명", "역할", "등급", "경력(년)", "보유자격"], ["", "", "", "", ""], ["", "", "", "", ""]], {})
    doc.add_paragraph("[별지 제9호서식] 하도급 계획서")
    add_table(doc, [["사업명", ""], ["하도급 부분", ""], ["하도급 업체", ""]], {})


def schedule_table(today: dt.date) -> list[list[str]]:
    """체험용 일정표: 만든 날을 기준으로 질의·설명회·제출 마감·평가 날짜를 잡는다(남은 날 안내를 해 볼 수 있게)."""

    def d(days: int) -> str:
        x = today + dt.timedelta(days=days)
        while x.weekday() >= 5:                        # 주말이면 다음 월요일
            x += dt.timedelta(days=1)
        return f"{x.year}. {x.month}. {x.day}.({'월화수목금토일'[x.weekday()]})"

    return [["구분", "일시", "장소·방법"],
            ["질의 기간", f"{d(1)} 09:00 ~ {d(6)} 18:00", "나라장터 공고 질의"],
            ["제안요청 설명회", f"{d(3)} 14:00", "가상시청 별관 2층 회의실"],
            ["제안서 제출 마감", f"{d(12)} 10:00", "국가종합전자조달시스템(나라장터)"],
            ["제안서 평가(발표)", f"{d(15)} 예정", "일시·장소는 개별 통보"]]


def build_sample_rfp(path: Path, *, with_forms: bool = True, today: dt.date | None = None) -> Path:
    """가상 제안요청서 HWPX를 만든다."""
    from hwpx import HwpxDocument

    doc = HwpxDocument.new()
    doc.add_paragraph("※ 이 문서는 rfpgen 체험용으로 만든 가상 제안요청서입니다(실제 기관·사업과 관계없음).")
    for line in OVERVIEW_LINES:
        doc.add_paragraph(line)
    doc.add_paragraph("Ⅳ. 제안 요청 내용")
    doc.add_paragraph("1. 요구사항 총괄표")
    add_table(doc, DECLARED_TABLE, {})
    add_table(doc, SUMMARY_TABLE, SUMMARY_SPANS)
    doc.add_paragraph("2. 요구사항 상세")
    for d in DETAILS:
        rows, spans = detail_table(*d)
        add_table(doc, rows, spans)
    for line in GUIDE_LINES:
        doc.add_paragraph(line)
    doc.add_paragraph("2. 제안서 평가")
    doc.add_paragraph("가. 정량적 평가(20점)")
    add_table(doc, EVAL_QUANT, EVAL_QUANT_SPANS)
    doc.add_paragraph("나. 정성적 평가(70점)")
    add_table(doc, EVAL_QUAL, EVAL_QUAL_SPANS)
    doc.add_paragraph("3. 제안서 제출 일정")
    add_table(doc, schedule_table(today or dt.date.today()), {})
    if with_forms:
        _add_forms(doc)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save_to_path(str(path))
    return path


__all__ = ["DECLARED_TABLE", "DETAILS", "EVAL_QUAL", "EVAL_QUAL_SPANS", "EVAL_QUANT", "EVAL_QUANT_SPANS", "GUIDE_LINES",
           "OVERVIEW_LINES", "SUMMARY_SPANS", "SUMMARY_TABLE", "add_table", "build_sample_rfp", "detail_table",
           "schedule_table"]
