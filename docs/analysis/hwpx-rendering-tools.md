# HWPX·HWP 출력 도구 분석: hwpx-docs, H2Orestart

| 항목 | 내용 |
|---|---|
| 문서 상태 | 분석 v0.1 |
| 작성일 | 2026-11-16 |
| 목적 | 두 GPL 계열 도구의 소스를 읽고, 우리 render·parse 모듈에 가져올 부분과 그 라이선스 의무를 정한다 |
| 관련 설계 | [design.md](../design.md) 7.2 parse, 7.9 render, 10장 스타일, 11장 스택·라이선스 |
| 비교 기준 | python-hwpx 6.12.0(Apache-2.0) wheel 압축 해제본 |
| 분석 방법 | 소스 읽기만 했다. 내려받은 코드는 실행하지 않았고 의존성도 설치하지 않았다 |

---

## 0. 요약

**결론 한 줄:** hwpx-docs는 "코드보다 실측 지식"이 값지고, H2Orestart는 "외부 프로세스 + 배포용 문서 복호화 알고리즘"이 값지다. 둘 다 통째로 들여올 이유는 없다.

python-hwpx 6.12.0이 이미 누름틀, 변경 추적, 체크 상자, 머리말·꼬리말·쪽 번호, 스타일 중복 제거(`ensure_*`), 표 병합·셀 테두리, 한컴 고유 차례 필드, 검증기를 갖추고 있다. 그래서 hwpx-docs에서 코드째 가져올 후보는 좁다.

**M2 render 핵심 발견**

1. python-hwpx에 없는 기능 중 쓸 만한 것은 **데이터→한글 차트(chartML) 생성**(`chart/ooxml.py:111-208`)이다. python-hwpx `add_chart`는 완성된 `c:chartSpace` XML만 받는다(`_document/ns/shapes.py:363-386`).
2. **개조식 보고서 프리셋**(`presets/report-gongmun.json`, `text/markdown.py:65-189`)이 우리 보고서체와 거의 같은 구조다. 제목 상자, 장 막대, □ 항목, ○ - · 단계, ※ 주석, 격자 표로 되어 있다. 값은 우리 10.2절 기준으로 다시 정하고, 구조만 재구현한다.
3. `docs/rules.md`의 한글 2024 실측 규칙은 그대로 구현 규칙이 된다. 특히 다음 네 가지는 모르면 결과물이 조용히 틀어진다.
   - 내어쓰기 의미(H25)
   - `KEEP_WORD`/`BREAK_WORD` 이름이 실제 동작과 반대라는 점(H12)
   - □○※·가 SYMBOL 언어 글꼴을 쓴다는 점(H05)
   - 선 굵기 문자열에 공백이 필요하다는 점(H16)
4. 표는 "HTML식 셀 배치 + 격자선(H/V) 모델"(`table/table.py:19-78`)이 선언형 TableSpec을 python-hwpx 명령형 API로 옮기는 다리로 적합하다. 알고리즘이 짧아 재구현한다.

**M1 parse 핵심 발견**

1. python-hwpx 6.12.0은 **배포용 HWP와 암호화된 HWPX를 거부**한다.
   - HWP: `hwp5/reader.py:18-44, 72-82`
   - HWPX: `opc/package.py:712-731`
   - 우리 `src/rfpgen/parse/hwp5.py`도 이 경우 실패로 끝난다.

   H2Orestart는 두 경우를 모두 복호화한다.
   - HWP5 ViewText: `HwpFile.java:315-364, 396-409`
   - HWPX 배포용: `HwpxFile.java:254-308`

   공고 첨부가 배포용으로 올라오는 경우를 처리할 유일한 근거 코드다. 다만 법률 검토(저작권법 제104조의2)가 먼저다.
2. 표 정규화가 필요하다. HWP 표에는 앵커 셀이 하나도 없는 열이 생긴다. H2Orestart는 이 열을 지우고 colSpan을 줄인다(`ConvTable.java:117, 1275-1330`). python-hwpx의 `get_cell_map`은 이런 칸을 만나면 `IndexError`를 낸다(`oxml/table.py:1004-1046`). DocIR 빌더에 관대한 격자 정규화를 둔다.
3. 텍스트 추출과 CFB 견고성은 python-hwpx가 더 낫다. 루프 검출과 크기 제한이 있다(`hwp5/cfb.py:131-215`). H2Orestart 파서를 주 경로로 바꿀 이유는 없다.

**M3 PDF 핵심 발견**

H2Orestart+LibreOffice 경로는 **쪽수 판정에 쓰면 안 된다.** 쪽수가 달라지는 원인은 다음과 같다.

- 양쪽 정렬을 왼쪽 정렬로 바꾼다(`ConvPara.java:214-215, 445-446`).
- 글꼴이 없으면 장평을 100%로 고정한다(`ConvPara.java:627-632`).
- 줄간격을 경험값으로 보정한다(`ConvPara.java:286-304`).
- 표 행 높이를 최소 높이로 둔다(`ConvTable.java:244-253`).

일부 개체는 출력에서 빠진다.

- HWPX의 `hp:switch` 안에 있는 차트는 무시된다(`HwpParagraph.java:286-299`).
- OLE와 글맵시는 "Not Supported Object" 상자로 바뀐다(`ConvGraphics.java:165-168, 727-780`).
- 양식 개체, 덧말, 글자 겹침은 빠진다(`HwpParagraph.java:276-285`).

따라서 H2Orestart는 HWP 원본 열람용 PDF, 파싱 폴백, 교차 렌더 비교에만 쓴다.

**라이선스**

- hwpx-docs 코드를 수정해 넣으면 GPL-3.0 제13조에 따라 결합 자체는 허용된다. 다만 결합물 전체에 AGPL 제13조의 네트워크 소스 제공 의무가 붙는다. M4에서 Web UI와 REST API를 열면 실제 의무가 생긴다.
- H2Orestart는 GPL-3.0-or-later라 우리 GPL-3.0과 바로 호환된다.
- 권고: hwpx-docs는 **재구현과 아이디어 차용을 기본**으로 한다. 꼭 옮겨야 하는 코드는 차트 생성기 하나 정도로 한정하고, 별도 하위 패키지에 격리한다(5장).

---

## 1. 확보한 소스와 라이선스 확인

| 저장소 | 로컬 경로 | 커밋 | 커밋 시각 | 버전 | 라이선스 확인 |
|---|---|---|---|---|---|
| BlackBuddle/hwpx-docs | `/tmp/claude-0/-home-user-auto-rfp-generator/f3d3ff9a-3973-59c5-bd3d-f4f9b614b83d/scratchpad/ext/hwpx-docs/` | `ffe24ee213951d0b44529ff5eaff34bf7ba5c690` (main) | 2026-11-15 16:31:28 +0900 | 0.3.0 (`.claude-plugin/plugin.json`) | **AGPL-3.0-or-later** (아래 1) |
| ebandal/H2Orestart | `/tmp/claude-0/-home-user-auto-rfp-generator/f3d3ff9a-3973-59c5-bd3d-f4f9b614b83d/scratchpad/ext/H2Orestart/` | `8c1a37c31f1adca143a07b1f8454e74fd5690521` (main) | 2026-11-16 21:58:49 +0900 | 0.8.0 (`description.xml`) | **GPL-3.0-or-later** (아래 2) |

두 저장소 모두 2026-11-16에 `git clone --depth 1`로 받았다. H2Orestart는 변경 이력을 보려고 `git fetch --depth=400`으로 275개 커밋까지 늘렸다.

**1. hwpx-docs 라이선스 근거**

- `LICENSE`: AGPL v3 원문, 661줄, sha256 `0d96a4ff…abcb0`, 제13조가 540행에 있다.
- `README.md:273, 289`: "AGPL-3.0-or-later, Copyright (C) 2026 BlackBuddle"이라고 적혀 있다.
- `plugin.json`의 `"license"` 값도 `"AGPL-3.0-or-later"`다.
- 파일별 저작권 머리말과 SPDX 표기는 없다.

**2. H2Orestart 라이선스 근거**

- `COPYING`: GPL v3 원문이다. `/usr/share/common-licenses/GPL-3`와 비교하면 첫 줄 앞 공백과 마지막 줄바꿈만 다르다.
- Java 110개 파일 중 100개에 "Copyright (C) 2023 ebandal … either version 3 of the License, or (at your option) any later version" 머리말이 있다.
- 머리말이 없는 10개 파일은 `README.md`("소스코드는 GNU GPLv3")와 `COPYING`을 따른다. 여기에는 `ConvHypua2Unicode.java`, `compare/HwpComparer.java`, `HwpxManifest.java` 등이 포함된다.
- AUR 패키지 메타데이터는 라이선스를 "MIT"로 적었지만 잘못된 정보다. 기준은 저장소의 `COPYING`이다.

**규모**

- hwpx-docs: 파일 828개, Python 약 23,000줄. 표준 라이브러리만 쓰고, XML은 대부분 정규식과 문자열로 조립한다. `tests/fixtures/`에 한글 2024로 만든 HWPX 271개가 있다.
- H2Orestart: 파일 130개, Java 약 34,800줄이다.
  - 그중 `ConvHypua2Unicode.java`(옛한글 변환표)가 5,724줄이다.
  - 저장소의 `dist/H2Orestart.oxt`는 **v0.5.4(2023-05-29)로 낡았다**. 실제 배포본은 LibreOffice 확장 사이트(v0.8.0, 2026-10-18)나 Debian forky·sid의 `libreoffice-h2orestart 0.8.0-1`을 쓴다. Debian trixie에는 0.7.2-1이 있다.

**접근하지 못한 것**

- GitHub API와 웹의 이슈·릴리스 페이지는 이 세션에서 저장소별로 막혀 있었다(403). `add_repo`를 읽기 권한으로 요청해도 익명 git 읽기만 허용되고, 이슈 API는 붙지 않았다.
- 대신 다음 자료로 이슈 내용을 재구성했다.
  - LibreOffice 확장 사이트(extensions.libreoffice.org/…/27504)의 릴리스 노트(v0.5.4~v0.8.0, 이슈 번호 포함)
  - git log 275개 커밋 메시지
  - Debian·AUR 패키지 페이지

  이슈 본문과 댓글에만 있는 한계(재현 파일, 미해결 이슈 목록)는 확인하지 못했다.

---

## 2. hwpx-docs 분석

### 2.1 구조

| 계층 | 위치 | 역할 |
|---|---|---|
| CLI | `lib/hd.py` | `hd build/md/html/read/slots/edit/guard/text/pagefit/preview/render/convert/secure/selftest` |
| core | `lib/hwpx_docs/core/` | `build.py`(스펙→HWPX), `header.py`(header.xml 등록부), `read.py`(HWPX→스펙), `units.py`, `layout.py`·`textfit.py`(줄 계산), `registry.py`(기능 패키지 자동 등록), `template/`(한글 2024 빈 문서) |
| 기능 패키지 | `text/ table/ objects/ objects2/ page/ pagex/ chart/ fields/ textstyle/` | 블록·런 작성기. `BLOCKS`/`READS`/`DRAWS`를 `__init__.py`에 등록한다(`docs/interfaces.md:22-43`) |
| 편집 | `edit/edit.py`, `edit/guard.py` | 받은 양식에 글자만 채우고 검사 |
| 점검·맞춤 | `check/readability.py`, `check/check_xml.py`, `pagefit/` | 가독성 RD01~RD13, 체크리스트 질의, 쪽 맞춤 |
| 렌더 | `preview/`(약 5천 줄, SVG 자체 렌더러), `render/hwpcom.py`·`convert/`(Windows 한글 COM) | 쪽 그림, PDF 변환 |
| 지식 | `docs/rules.md`, 패키지별 `rules.md`, `docs/owpml-crosscheck.md`, `skills/gongmun-style/` | 한글 2024 실측 규칙, 공문 문장 규칙 |

### 2.2 입력 스펙(JSON) 형식

정식 JSON Schema 파일은 없다. `docs/spec.md`가 유일한 계약이다(`docs/interfaces.md:3`). 빌더는 모르는 블록, 런, class를 만나면 `ValueError`로 멈춘다(`core/build.py:54, 190`, `text/text.py:94`).

| 층 | 키 (출처) |
|---|---|
| 문서 | `title`, `defaults{font,size,align,line}`, `page{size,landscape,margin{left,right,top,bottom,header,footer,gutter}}`, `columns`, `page_border`, `header`/`footer`(블록 목록 또는 `{blocks,apply,style}`), `page_number{pos,format,side}`, `numberings[{levels:[{text:"^1.",format}]}]`, `styles`(CSS class처럼 쓰는 속성 묶음), `named_styles`(한글 스타일 목록 항목), `sections[]`, `body[]` (`docs/spec.md:10-34`, 173행) |
| 블록 | `"글"`, `{p: 글 또는 [런], …문단·글자 속성}`, `{table}`, `{pic}`, `{shapes}`, `{gap: pt}`, `{chart}`, `{page_break}`, `{toc}`, `{index}`, `{object}`, `{ole}`, `hide_page`, `columns_here` (`docs/spec.md:36-48, 195-250`) |
| 런 | `{t}`, `{link,t}`, `{footnote}`/`{endnote}`, `{page_num}`, `{new_page_num}`, `{field,t,memo}`(누름틀), `{bookmark}`, `{equation}`, `{tab}`, `{xml}`(원시 OWPML), `{form}`, `{xref}`, `{index_mark}`, `{change}`(변경 추적), `{dutmal}`, `{proof}` (`docs/spec.md:50-65`, 표 228-250) |
| 글자 속성 | `font`(7개 언어 모두), `font_latin`·`font_symbol` 등, `size`, `bold`, `italic`, `color`, `shade`, `spacing`(자간), `ratio`(장평), `underline`, `strike`, `shadow`, `sup`/`sub`, `char_border`/`char_fill` (`docs/spec.md:67-75`) |
| 문단 속성 | `align`, `left`·`right`·`indent`(pt, 음수는 내어쓰기), `before`·`after`, `line`(%, `{fixed}`, `{at_least}`, `{between}`), `keep_next`, `keep_lines`, `page_break_before`, `widow`, `word_break`(char/word), `condense`, `border`, `fill`, `bullet`, `number`, `outline_level`, `tabs` (`docs/spec.md:77-88`) |
| 표 | `cols`(mm, 바깥 크기), `heights`, `border`, `outline`, `hlines`/`vlines`, `cell`(셀 기본값), `pad`, `margin`, `inline`, `align`, `pos`, `page_break`, `repeat_header`, `header_rows`, `rows`(HTML처럼 `cs`·`rs`), `caption`, `formula`, `protect` (`docs/spec.md:90-132`) |
| 단위 | 쪽·표·도형은 mm, 글자 관련은 pt. `"12pt"`, `"3.5mm"`, `"500hu"` 같은 문자열도 받는다. 선은 `"0.4mm solid #000000"` 형식이다 (`docs/spec.md:3-8`) |

`hd read`는 거꾸로 HWPX를 같은 스펙으로 읽는다(`core/read.py:744-759`). 모르는 요소는 `{"xml": …}`로 보존한다.

### 2.3 header.xml 생성과 itemCnt·ID 일관성

| 항목 | 방식 | 근거 |
|---|---|---|
| 기본 틀 | 한글 2024가 저장한 빈 문서를 템플릿으로 쓴다. 템플릿 항목 뒤에 새 항목을 덧붙인다. 바탕글, 개요 1~10 같은 한글 기본 스타일이 그대로 남는다 | `core/build.py:34`, `docs/rules.md` K08 |
| ID 시작값 | 종류별로 템플릿 항목 수를 센다. 새 ID는 borderFill·bullet·numbering이 개수+1, charPr·paraPr·tabPr·style이 개수부터다 | `core/header.py:16-24`, rules H02 |
| 중복 제거 | `add(kind, key, make)`가 내용 키를 보고 같은 서식이면 같은 ID를 돌려준다. charPr 키는 (머리 속성, 본문 XML), paraPr 키는 본문 XML 전체다 | `core/header.py:36-41, 108-112, 158` |
| 글꼴 | 언어 7개마다 같은 글꼴 목록을 쓰고, 렌더 때 `fontCnt`를 고친다 | `core/header.py:66-68, 229-234` |
| itemCnt | 렌더 때 `itemCnt="(\d+)"` 값에 덧붙인 항목 수를 더한다. 템플릿에 `hh:bullets`가 없으면 `paraProperties` 앞에 새로 만든다 | `core/header.py:235-246`, rules H01·H03 |
| secCnt | 구역 수로 덮어쓴다 | `core/build.py:209` |
| 개체 ID | 종류별 기준값에 문서 내 순번을 더한다: 표 1000000000+n(`table/table.py:130`), 필드·하이퍼링크 1300000000+n(`text/text.py:19, 58`), 수식 1400000000+n(46행), 차트 1900000000+n(`chart/section.py:34`), 각주 instId 2000000000+n(`text/text.py:112`). zOrder는 같은 순번이다 | 왼쪽 |
| 문단 ID | **모든 문단을 `id="0"`으로 쓴다** | `core/build.py:110` |
| 메타데이터 | content.hpf의 `creator`와 `lastsaveby`를 `hwpx-docs`로 쓴다 | `core/build.py:225` |

시사점은 세 가지다.

- **중복 제거 등록부**는 python-hwpx의 `ensure_run`, `ensure_paragraph_format`, `ensure_border_fill`, `ensure_style`, `ensure_numbering`이 이미 같은 일을 한다(`_document/ns/styles.py:530-807`). itemCnt도 그쪽이 맞춰 준다. 이식할 필요가 없다.
- **문단 ID가 모두 0**이면 차례·상호 참조의 앵커로 쓸 수 없다. python-hwpx의 한컴 고유 차례는 문서 안에서 유일한 문단 ID를 요구한다(`tools/toc_author.py:115`). 우리 방식은 python-hwpx 쪽이 맞다.
- **creator 기록**은 블라인드 평가에서 문제가 된다. 생성 도구 이름이 남기 때문이다. package 단계에서 문서 속성을 비운다(5장, BLD 규칙).

### 2.4 문단·런

- `para_xml`(`core/build.py:87-111`): 블록 속성을 문단 속성과 합쳐 paraPr ID를 얻는다. `bullet`·`number`·`outline_level`은 `hh:heading`으로 연결한다. 구역 설정 런의 charPr은 첫 텍스트 런과 같게 맞춘다(rules S02). 첫 줄 높이가 달라지지 않게 하려는 처리다.
- `para_pr`(`core/header.py:114-158`): 여백 값은 `hp:switch` 안에 두 번 쓴다. `hp:case`에는 실제 HWPUNIT, `hp:default`에는 그 2배를 넣는다(rules H08). 줄 나눔 설정은 이름과 실제 동작이 반대다. **`KEEP_WORD`가 글자 단위, `BREAK_WORD`가 어절 단위**다(140-143행, rules H12).
- `char_pr`(`core/header.py:65-112`): 글꼴을 7개 언어에 모두 넣는다. ○ □ ☐ ※ ·는 SYMBOL 언어 글꼴을 쓰기 때문에 하나라도 빠지면 기호 모양이 바뀐다(rules H05).
- `run_xml`(`text/text.py:10-94`): 하이퍼링크(18-34행), 형광펜(38-39행), 수식(43-54행), 책갈피, 누름틀(57-71행), 각주·미주, 쪽 번호 자동 번호(81-84행), 원시 XML을 쓴다.

### 2.5 표 (병합, 테두리, 너비)

`TableMixin.table`(`table/table.py:10-136`)의 처리 순서는 다음과 같다.

1. **셀 배치**(19-46행): HTML처럼 각 셀이 다음 빈 격자 자리를 차지한다. `cs`·`rs`가 덮는 자리는 건너뛴다. 빈 자리에는 빈 셀을 채운다.
2. **격자선 모델**(53-78행): `H[(r,c)]`는 행 r 위의 선, `V[(r,c)]`는 열 c 왼쪽의 선이다. 바깥선(`outline`), 가로줄·세로줄 덮어쓰기(`hlines`/`vlines`), 셀별 `border`를 차례로 적용한다. 같은 선을 두 셀이 정하면 나중 셀이 이긴다. 각 셀의 borderFill은 자기 네 변의 격자선에서 나온다(101-104행).
3. **행 높이 추정**(79-90행): 줄 수 × 글자 크기 × 줄간격 + 위아래 여백. 한글은 글이 넘치면 행을 늘린다.
4. **XML 작성**(117-136행): `cellSz`는 바깥 크기(rules T02)다. 덮인 셀은 쓰지 않는다(T03). `rowCnt`는 실제 `hp:tr` 수와 같아야 한다(T04, 다르면 한글이 열지 못한다). 기본값은 셀 여백 510/141 hu, 바깥 여백 283 hu(T06·T07)이고, `page_break`와 `repeatHeader`를 쓴다.

같은 선 모델을 읽기에도 쓴다(`core/read.py:524-623`). 두 셀 중 더 강한 선을 고르고, 가장 흔한 선을 표 기본선으로 둔다. `solve()`(`core/read.py:730-741`)는 병합 셀 너비에서 열 너비를 역산한다.

**우리 쪽 판단:** python-hwpx는 `add_table(rows, cols)` 다음에 `merge_cells`, `set_cell_borders`, `set_cell_shading`, `set_column_widths`를 부르는 명령형 API다. 셀 배치와 격자선 모델(약 60줄)을 재구현해 "선언형 TableSpec → python-hwpx 호출" 변환기로 쓴다.

### 2.6 그림

- `ObjectsMixin.pic`(`objects/objects.py:86-123`): 그림을 `BinData/imageN.ext`로 넣고 manifest에 `isEmbeded="1"` 항목을 쓴다(rules K05).
- orgSz·curSz·sz를 모두 목표 크기로 쓴다(G02).
- python-hwpx `add_picture`와 `media.add_image`로 대체할 수 있다.

### 2.7 차트

두 가지 방식이 있다.

**① 한글 차트 개체** (`"native": true`, `chart/`)

- `ooxml.chart_xml(spec)`(`chart/ooxml.py:111-208`)은 범주·계열 데이터로 `Chart/chartN.xml`(`c:chartSpace`)을 만든다. 시리즈는 `_ser`(54-104행)가 만든다.
- 지원 종류: 세로 막대, 가로 막대, 꺾은선, 원, 혼합, 영역, 분산형, 보조 축.
- 제목, 축 제목, 범례, 값 표시, 최솟값·최댓값, 글꼴(`c:txPr`)도 쓴다.
- `section.element`(`chart/section.py:15-37`)는 본문에 `hp:switch/hp:case(ooxmlchart)/hp:chart`를 쓴다. OLE 대체본과 미리보기 그림은 생략한다. 한글 2024가 그것 없이도 그린다는 실측이 근거다(`chart/rules.md` CH04).
- 이 차트 파트는 content.hpf에 올리지 않는다(CH02). 한글도 같게 한다.
- 데이터가 잘못되면 `FALLBACK chart`를 출력하고 ②로 그린다(`chart/section.py:40-54`).

**② 그리기 개체로 그린 차트** (`objects.chart_shapes`, `objects/objects.py:134-204`)

- 격자, 축, 막대·선, 값 레이블, 범례를 사각형·선·글상자로 조립한다.
- 벡터라서 한글에서 편집할 수 있지만 "차트 데이터 편집"은 안 된다.

**python-hwpx와의 차이:** python-hwpx `shapes.add_chart(chart_xml)`은 완성된 chartML만 받는다(`_document/ns/shapes.py:363-386`). 데이터에서 chartML을 만드는 부분이 **python-hwpx 6.12.0에 없는 기능**이다.

**렌더 경로 주의:** H2Orestart는 `hp:switch`를 통째로 무시한다(`HwpParagraph.java:286-299`). server PDF 경로에서는 차트가 사라진다. rhwp의 차트 지원 여부는 확인하지 못했다. 그래서 차트는 "한글 차트 개체 + 서버 경로용 PNG"를 함께 두거나 ②처럼 도형으로 그려야 렌더러 사이 차이에 강하다.

### 2.8 누름틀·양식 개체·변경 추적

- **누름틀**(`text/text.py:57-71`, rules S23): `fieldBegin type="CLICK_HERE" fieldid="627272811"`를 쓴다. Command 문자열은 `Clickhere:set:<본문 길이>:Direction:wstring:<n>:<안내문> HelpState:wstring:<n>:<메모> ` 형식이다. 안내문은 필드 안의 텍스트 런으로 쓴다.
- **양식 개체**(`fields/forms.py`): checkBtn, radioBtn, comboBox, edit 등을 쓰고, `hd form fill`로 값을 채운다. 한글은 콤보와 목록 항목 중 첫 항목만 남기는 제약이 있다(`fields/rules.md` F08).
- **변경 추적**(`fields/track.py`): header.xml에 `hh:trackChanges`·`trackChangeAuthors`를 넣고, 본문에 삽입·삭제 표지를 넣는다.
- **python-hwpx 6.12.0에 이미 있다:**
  - `doc.fields.add(name, prompt=, memo=)`(`_document/ns/fields.py:45-71`)
  - `add_check_box`/`set_check_box`
  - `doc.tracking.insert/delete/replace`(`_document/ns/tracking.py:34-115`)

  이식이 필요 없다.

### 2.9 머리말·꼬리말·쪽 설정·쪽 번호

- `PageMixin.section_xml`(`page/page.py:13-79`)은 템플릿 `secPr`에서 용지, 방향, 여백, 단, 쪽 테두리를 바꾼다.
  - 가로는 너비와 높이를 바꾸지 않고 `landscape="NARROWLY"`로 표시한다(rules S03).
  - A4는 한글 값 그대로 59528×84186 hu다(S04).
- 머리말·꼬리말은 첫 문단의 `hp:ctrl/hp:header|footer`에 subList로 넣는다. `textWidth`는 본문 너비, `textHeight`는 머리말 길이다(58-67행, S07).
- 쪽 번호는 `hp:pageNum pos formatType sideChar`를 쓴다. `sideChar="-"`이면 **`- 1 -`** 꼴이 된다(68-72행, S08).
- python-hwpx는 `page.set_header/set_footer/set_page_number(prefix, suffix)`, `restart_page_number`, `set_visibility`로 대체한다(`_document/ns/page.py:200-360`).
  - 주의: python-hwpx의 쪽 번호는 한컴 쪽 번호 컨트롤이 아니라 꼬리말 안의 자동 번호다.
  - 그래서 표지에서 숨기려면 `hide_first_footer`를 써야 한다(같은 파일 docstring).

### 2.10 번호·글머리표·개요

- `Header.numbering(levels)`(`core/header.py:195-210`)는 `hh:paraHead` 10단계를 만든다. 텍스트는 `^1.` 꼴이고 `numFormat`을 지정한다.
- 기본값은 공문 체계다: 1. → 가. → 1) → 가) → (1) → (가) → ① → ㉮ (`core/units.py:159-163`).
- `bullet(char)`(220-225행)는 글자 글머리표를 만든다.
- 우리 체계 Ⅰ. → 1. → 가. → 1) → 가)에는 `ROMAN_CAPITAL, DIGIT, HANGUL_SYLLABLE, DIGIT, HANGUL_SYLLABLE` 순서가 필요하다. python-hwpx `ensure_numbering(kind="number"|"outline", levels=)`가 형식 목록을 지원한다(`oxml/numbering_kinds.py:45-60`).
- 단, 개요 번호의 사용자 정의 idRef는 python-hwpx 자신도 "미실측(experimental)"이라고 적었다(같은 파일 1-25행).

**권고:** 제목 번호는 plan 단계 outline에 이미 있다. 렌더에서는 **번호를 글자로 박아 넣고** 자동 번호에 기대지 않는다. 이유는 세 가지다.

- 렌더러마다 자동 번호 지원이 다르다. H2Orestart에도 "번호 없는 개요에 번호가 보이는 오류"를 고친 이력이 있다.
- 추적표의 절 번호와 출력물 번호가 항상 같아야 한다.
- 개조식 기호(□○-·※)도 hwpx-docs처럼 글자로 쓰고 내어쓰기로 정렬한다.

### 2.11 차례

- hwpx-docs의 `{"toc"}`(`fields/refs.py:144-166`)는 정적 차례다. 제목 문단, 오른쪽 점선 탭, 쪽 번호로 이루어진다.
- `pages:"auto"`이면 2단계로 만든다(`fields/rules.md` X05). 먼저 같은 길이의 가짜 항목으로 빌드한다. 자체 미리보기 렌더러로 제목 쪽을 잰 다음 다시 빌드한다.
- 한글 COM의 `MakeContents`는 실패했다고 기록돼 있다(X04).
- python-hwpx는 한글 고유 `TABLEOFCONTENTS` 필드를 만든다(`tools/toc_author.py:1-21, 338`). 그 쪽 번호도 추정값이고, 한글에서 "차례 새로 고침"을 해야 확정된다.

**우리 쪽 판단:** hancom 경로에서는 python-hwpx 고유 차례를 쓰고 한글에서 새로 고친다. server 경로(rhwp)에서는 hwpx-docs처럼 **렌더 쪽 지도를 이용한 2단계 빌드**로 정적 쪽 번호를 확정한다. 이 2단계 결과는 PDF 북마크 생성과 추적표의 "쪽"에도 같이 쓴다.

### 2.12 개조식 보고서 프리셋 (Markdown → 보고서체)

| Markdown | 역할 | 프리셋 값 (`presets/report-gongmun.json`) | 구현 |
|---|---|---|---|
| `# 제목`, `> 부제` | title, subtitle | 돋움 22pt 굵게 가운데. 위아래 3pt 남색(#1F3864) 테두리 상자 | `markdown.py:122`, `box()` 89-100행 |
| `작성일:` | date | 바탕 11.5pt 오른쪽 | `mdparse.py:144-147` |
| `◇ …` | summary | 바탕 12pt, left 15 / indent -15. 회색 배경 상자 | `mdparse.py:152-154`, `markdown.py:124-125` |
| `## Ⅰ. 장` | chapter | 6pt 남색 막대 셀 + 연회색 배경 셀(아래 1pt 선)로 된 2열 표 | `markdown.py:129-140` |
| `### 항목` | item | 앞에 "□ " 자동 추가. 돋움 12.5pt 굵게, left 16 / indent -16, before 9 | `mdparse.py:135-136` |
| `- ` (들여쓰기 0/2/4칸) | l0/l1/l2 | "○ ", "- ", "· " 바탕 12/11.5/11pt, left 31/43/55 · indent -15/-11/-11 | `mdparse.py:60, 161-169`, `markdown.py:148-152` |
| `※ …` | note | 바탕 10.5pt, left 31 / indent -15 | `mdparse.py:158-160` |
| 표 | th/td | 머리 행 #D9D9D9·굵게, 위 굵은 선, 마지막 행 아래 굵은 선, 셀 여백 3.5/5pt, 줄간격 145% | `markdown.py:157-181` |
| `끝.` | end | 오른쪽 정렬 | `mdparse.py:155-157` |

- `para()`(`markdown.py:65-82`)는 CSS 방식 내어쓰기를 한글 방식으로 바꾼다. 한글에서는 첫 줄이 `left`, 둘째 줄부터가 `left+|indent|`에서 시작한다(rules H25).
- 프리셋에 없는 Markdown 요소를 만나면 `UNMAPPED`로 멈춘다. `--fallback`을 주면 가까운 스타일로 대신 쓰고 기록을 남긴다(`markdown.py:198-262`).
- python-hwpx의 Markdown 가져오기는 중립 스타일뿐이다. 제목 16/12/11/10pt에 표 머리 음영 정도만 있다(`tools/markdown_import.py:44-61`). 개조식 구조는 없다. **이 부분이 python-hwpx에 없는 두 번째 실질 기능**이다.

### 2.13 별지 채우기와 사후 검사

- `edit.Doc`(`edit/edit.py:162-329`)
  - 칸 키는 `t<T>.r<R>c<C>`, `p<N>` 형식이다.
  - **라벨 자동 대응**(188-209행): 15자 이하의 짧은 셀을 라벨로 본다. 오른쪽 셀이 비었으면 오른쪽을, 아니면 아래 셀을 값 칸으로 고른다. 빈칸 판정 정규식은 `[\s○◯_·.\-:]*`이다(31행).
  - **글자만 교체**(218-239행): 가장 긴 런의 서식을 살리고 나머지 런은 비운다. 바뀐 문단의 `linesegarray`는 지워서 한글이 다시 계산하게 한다.
  - **체크 상자**(296-314행): 라벨 바로 앞의 ☐/□를 ☑로 바꾼다.
  - **저장**(316-329행): 바뀐 구역 파일만 다시 쓴다. `Preview/PrvText.txt`를 새로 만들고 `PrvImage.png`는 흰 그림으로 바꾼다. 옛 내용이 미리보기에 남는 것을 막기 위해서다.
- `guard.report`(`edit/guard.py:49-107`)는 세 가지를 검사한다.
  - **구조 지문**: 문단 수, 표 rowCnt·colCnt, 셀 주소·병합·크기, 개체 수, header.xml이 같은지 본다.
  - **분량**: 바뀐 문단의 줄 수 증가와 그만큼 행이나 본문이 늘어난 mm를 계산한다.
  - **잔여물**: `○○`, `{{…}}`, `XXX`, `___`(24행)과 금지어·필수어를 찾는다.
- python-hwpx에는 더 강한 도구가 있다. `tables.find_cell_by_label`, `fill_by_path`(`_document/ns/tables.py:78-92`), 한컴 렌더로 보정한 `form_fit`(값 맞춤 keep→wrap→shrink), `tools/page_guard.py`(구조·텍스트 지표 비교)다.
- **판단:** python-hwpx를 주로 쓰고, hwpx-docs에서는 세 가지를 아이디어로만 가져온다.
  - 잔여 자리표시자 패턴
  - Preview 파트 처리
  - "라벨 앞 ☐ → ☑" 규칙

### 2.14 검증

- **JSON Schema 검증은 없다.** 모르는 키는 빌더 예외로 잡는다.
- `hd selftest`: 패키지별 자체 시험을 돌린다. 이어서 한글 2024가 만든 픽스처 271개를 읽기→빌드→읽기 해서 스펙이 같은지 비교한다(`README.md:241-243`). 한글은 필요 없다.
- 빌드할 때마다 가독성 보고를 출력한다(`core/build.py:278-280`, `check/readability.py` RD01~RD13).
- `check_xml`(`check/check_xml.py:1-18`): `text("회의명").size`처럼 유효 서식을 질의하고 체크리스트와 비교한다.
- `hd roundtrip`(Windows+한글): HWPX → 스펙 → HWPX → 한글 렌더 순으로 돌려 잉크 차이를 측정한다.
- **결함 실험 기록**(`docs/rules.md` 6장 124-126행)이 우리 HWPX 린트에 그대로 쓸 만하다. 한글이 어떤 결함에 어떻게 반응하는지 정리돼 있다.
  - **열지 못함**: manifest에 구역 누락, XML 비정형(예: 날 `&`), rowCnt 불일치, 빈 `hp:tr`
  - **열지만 바뀜**: 없는 ID 참조, 굵기 문자열 공백 누락, 모르는 선 종류, colSpan 범위 초과, secPr 없음, 속성 중복
  - **무해**: itemCnt 1 차이, `hp:default` 없음, mimetype 순서·압축, cellSz 없음, linesegarray 없음

### 2.15 한글 COM 경로

`render/hwpcom.py`, `convert/convert.py`의 방식은 다음과 같다.

- `DispatchEx`로 숨긴 **새** 한글 인스턴스를 만든다(149-152행).
- 공식 보안 승인 모듈 `RegisterModule("FilePathCheckDLL", 이름)`은 사용자가 직접 등록하고 환경변수로 켤 때만 쓴다(38-52행).
- 파일 접근 허용 창에 대신 답하지 않는다.
- 저장은 매번 새 임시 경로에 `SaveAs`한 뒤 옮긴다(306-323행).
- 한 묶음에 한글 하나만 쓴다(`run_jobs`, 362행).
- `CreatePageImage`는 bmp로만 성공한다(rules C04).

hancom 경로의 Windows 에이전트(pyhwpx) 설계에 그대로 참고할 운영 지식이다. 코드는 쓰지 않는다.

### 2.16 python-hwpx 6.12.0과 비교

| 기능 | hwpx-docs | python-hwpx 6.12.0 (근거) | 판단 |
|---|---|---|---|
| 서식 중복 제거·itemCnt | `Header.add` | `ensure_run/paragraph_format/border_fill/style/numbering` (`_document/ns/styles.py:530-807`) | python-hwpx 사용 |
| 이름으로 스타일 조회 (StyleMapper) | `style_ids` 이름·영문명 사전 (`core/header.py:25-28`) | `styles.resolve(name)`, `style_name_aliases` (`oxml/document_parts.py:1006`) | python-hwpx 사용 |
| 문서 전체 선언형 생성 | spec → HWPX 한 번에 | 없음. `hwpx.plan`은 **기존 문서 편집 계획**용이다 (`plan/__init__.py:1-14`) | 우리 RenderSpec을 직접 만든다 |
| 개조식 보고서 프리셋 | 있음 (2.12) | 중립 Markdown 스타일만 (`tools/markdown_import.py:44-61`) | **재구현** |
| 표 선언형 배치·격자선 | 있음 (2.5) | 명령형 생성 후 병합·테두리 | **재구현** |
| 데이터→한글 차트 | 있음 (2.7 ①) | 완성된 chartML만 받음 | **이식 또는 재구현** |
| 차트를 도형으로 | 있음 (2.7 ②) | 없음 | 아이디어 |
| 누름틀, 체크 상자, 변경 추적 | 있음 | 있음 (2.8) | python-hwpx |
| 머리말·꼬리말·쪽 번호 | 있음 | 있음 (2.9) | python-hwpx |
| 차례 | 정적 + 2단계 쪽 번호 | 한컴 고유 필드, 쪽 번호는 추정 | 경로별로 나눠 씀 (2.11) |
| 쪽 수 추정 | 자체 미리보기 + pagefit | `layout.estimate_pages` (`layout/pages.py:284`) | rhwp를 기준으로, 아이디어만 |
| 쪽 맞춤 자동 수정 | `pagefit fix` (keep·widow·쪽 나눔·간격 조정) | 없음. 린트·경고뿐 (`layout/lint.py`) | 아이디어 (M3) |
| 가독성 점검 | RD01~RD13 | 넘침·표 구조·오래된 줄 배치 캐시 린트 | check 규칙으로 재구현 |
| 서식 규칙 검사 | `check_xml` 질의 | `tools/format_rules.py`(hancom-io/dvc 키 호환) | python-hwpx 우선, 질의 DSL은 아이디어 |
| 양식 채우기 맞춤 | 줄 수 증가 경고 | `form_fit` (측정, 줄바꿈, 축소) | python-hwpx |
| 패키지 검증 | 자체 시험, minidom | `tools/package_validator.py`, `id_integrity.py`, `validator.py` | python-hwpx + polaris_dvc |
| 보안 파싱 | 표준 `xml.etree`(defusedxml 아님), 색 속성만 정화 (`core/read.py:82-94`) | lxml 기반 `parse_xml` | python-hwpx (우리 7.2 정책 유지) |
| 한글 실측 규칙 문서·픽스처 | rules.md, 픽스처 271개 | 저장소에 코퍼스가 있다고 언급하지만 wheel에는 없음 | **지식·데이터로 활용** |

### 2.17 render 모듈에 가져올 함수

| 대상 | hwpx-docs 위치 | 가져오는 방식 | 우리 쪽 형태 |
|---|---|---|---|
| 보고서체 문단 | `text/markdown.py:65-82` `para()` (내어쓰기 변환), `presets/report-gongmun.json:24-252` 역할 표 | 재구현. 값은 design 10.2절로 다시 정한다 | `config/styles/report.yaml`(CC0 분리 제안)의 역할별 글자·문단 값 → `render/styles.py`가 `ensure_run`·`ensure_paragraph_format`으로 ID 확보 |
| 개조식 기호와 내어쓰기 | `text/mdparse.py:60, 128-169`, `markdown.py:148-152`, rules H25·H05·H12 | 재구현 | `render/gaejo.py`: 단계별 기호(□○-·※)를 글자로 넣는다. 첫 줄 `left`, 둘째 줄부터 `left+기호 폭`. 7개 언어 글꼴 지정, 어절 단위 줄바꿈(`BREAK_WORD`) |
| 장 막대·요약 상자 | `markdown.py:89-100, 129-140` | 아이디어 | 장 제목 막대, 거버닝 메시지 상자, 요약(◇) 상자를 1×N 표로 그린다 |
| 표 | `table/table.py:19-78` (배치·격자선), 79-90행 (높이 추정), `core/read.py:730-741` `solve()` | 재구현 | `render/tables.py`: `TableSpec(cols, rows[cs/rs], border, outline, header_rows, repeat_header)` → python-hwpx 호출 |
| 차트 | `chart/ooxml.py:54-208`, `chart/section.py:15-37`, `chart/rules.md` CH01-CH14 | **이식(AGPL) 또는 재구현**. 5장 참고 | `render/charts.py`: `ChartSpec` → chartML → `doc.shapes.add_chart`. server 경로에는 PNG를 함께 둔다 |
| 머리말·꼬리말 | `page/page.py:58-72`, rules S07·S08 | 아이디어 | python-hwpx `set_header(사업명)`, `set_page_number(prefix="- ", suffix=" -")`, 표지 `hide_first_footer` |
| 정적 차례 | `fields/refs.py:138-166` (항목 형식), rules X05 | 아이디어 | server 경로 2단계 빌드 |
| 별지 채우기 | `edit/edit.py:188-209, 218-239, 296-314, 316-329`, `edit/guard.py:24, 27-41` | 아이디어 | python-hwpx `fill_by_path`·`form_fit` 위에 잔여 검사(`○○`, `{{`, `XXX`, `___`)와 구조 지문 비교를 얹는다 |
| HWPX 린트 | `docs/rules.md` 6장 | 아이디어(사실 차용) | `check`의 HWPX 규칙(K03, K06, T04, H16, H17)을 polaris_dvc 결과에 더한다 |

---

## 3. H2Orestart 분석

### 3.1 구조

| 패키지 | 내용 |
|---|---|
| `source/HwpDoc/` | 파서 계층. LibreOffice UNO에 의존하지 않는다. 예외는 `HwpRecord_TabDef.java` 하나뿐이다 |
| | `OLEdoc/CompoundFile.java`: CFB, v4는 4096바이트 섹터 지원(216-219행) |
| | `HwpFile.java`: HWP5. 압축 해제, 배포용 복호화 |
| | `HwpxFile.java`, `OCFdoc/OwpmlFile.java`: HWPX. 배포용 복호화, 구역 번호순 정렬(`OwpmlFile.java:122-132`) |
| | `HwpElement/*`: DocInfo 레코드 |
| | `paragraph/*`: 문단, 컨트롤, 표, 도형 |
| `source/soffice/` | Writer 문서로 옮기는 변환기: `ConvPara`, `ConvTable`, `ConvGraphics`, `ConvPage`, `ConvNumbering`, `ConvEquation`, `ConvFootnote`, `ConvHypua2Unicode`, `FontWidthCorrection` |
| `source/ebandal/libreoffice/comp/H2OrestartImpl.java` | UNO 진입점. `XFilter`, `XImporter`, `XExtendedFilterDetection` 구현 |
| `source/compare/HwpComparer.java` | 독립 CLI. `-print`는 번호 머리를 포함한 문단 출력, `-diff`는 두 문서의 문단 차이 비교(269-316행) |
| `registry/*.xcu` | 타입 `Hwp2002_File`(확장자 `hwpx hwp`), 필터 `Hwp2002_Reader`(가져오기 전용, `IMPORT ALIEN 3RDPARTYFILTER`), 감지 서비스 등록 |

### 3.2 설치와 headless 사용

**설치 (택1)**

```sh
# Debian forky/sid (0.8.0-1), trixie (0.7.2-1); Ubuntu는 README에 같은 이름의 패키지 안내
sudo apt install libreoffice-writer-nogui libreoffice-java-common default-jre-headless libreoffice-h2orestart

# 직접 설치: v0.8.0 .oxt를 LibreOffice 확장 사이트(또는 GitHub Release)에서 받아 시스템 전역에 등록
unopkg add --shared H2Orestart.oxt
unopkg list --shared | grep -i h2orestart
```

- JRE 8 이상이 필요하고, LibreOffice에서 Java가 켜져 있어야 한다(확장 사이트 설명).
- 저장소의 `dist/H2Orestart.oxt`는 v0.5.4라 쓰지 않는다.

**변환** (`README.md` 예시)

```sh
soffice --headless --infilter="Hwp2002_File" --convert-to pdf:writer_pdf_Export 파일.hwp
soffice --headless --convert-to pdf:writer_pdf_Export 파일.hwpx
```

`--infilter`에 대해 확인할 점이 있다.

- README는 **타입 이름**(`Hwp2002_File`)을 넘긴다.
- 그런데 `registry/H2Orestart_filters.xcu`에 등록된 **필터 이름**은 `Hwp2002_Reader`다.
- 기본은 감지에 맡기고(`detect()`, `H2OrestartImpl.java:222-274`), `.hwp`를 LibreOffice 기본 HWP 필터가 가로채는지만 설치 후 검증한다.

우리 파이프라인용 권장 호출(작업 1건당 프로세스 1개):

```sh
JOB=$(mktemp -d)
XDG_CACHE_HOME="$JOB/cache" timeout 120 soffice --headless --norestore --nolockcheck \
  -env:UserInstallation=file://$JOB/profile \
  --convert-to 'pdf:writer_pdf_Export:{"SelectPdfVersion":{"type":"long","value":"2"}}' \
  --outdir "$JOB/out" 입력.hwpx
# 확인: 종료 코드, out/*.pdf 존재, %PDF 시그니처, 쪽수 > 0. 끝나면 $JOB 전체 삭제
```

이렇게 호출하는 이유는 다음과 같다.

- **동시성:** `writerContext`, `detectedFileExt`, `tmpFilePath`가 `static`이다(`H2OrestartImpl.java:110-113`). `WriterContext.hwp/hwpx`도 static이다(`WriterContext.java:77-78`). 한 soffice 프로세스에서 문서를 동시에 열면 상태가 섞일 수 있다. 작업마다 `UserInstallation`과 프로세스를 따로 쓴다.
- **로그와 임시 파일:**
  - 로그는 `$XDG_CACHE_HOME/H2Orestart/import_%g.log`에 쌓인다. 4 MB짜리 10개까지이고, 문서 내용 일부가 남을 수 있다(`H2OrestartImpl.java:434-466, 558-576`, README "버그 신고").
  - 스트림 입력은 같은 폴더에 `H2O_TMP_*`로 복사된다(523-556행).
  - 오래된 파일은 5일이 지나야 지운다(468-493행).
  - 그래서 작업별 `XDG_CACHE_HOME`을 주고 끝나면 지운다. 제안서는 민감 문서다(design 12장).
- **종료 코드:**
  - v0.7.14(#78)부터 `filter()`가 실패하면 `false`를 돌려준다(`H2OrestartImpl.java:297-378`).
  - 커밋 메시지에 따르면 이로써 soffice 종료 코드가 0/1로 갈린다.
  - 그래도 출력 파일 검사는 반드시 한다.
- **PDF/A:**
  - JSON 필터 옵션은 LibreOffice 7.4 이상 문법이다.
  - `SelectPdfVersion=2`는 PDF/A-2b다.
  - 제출 형식에서 PDF/A가 필요한지는 아직 원문 대조 전이다(design 부록 A).
- **글꼴:**
  - `adjustFontIfNotExists`의 주석에 "별 효과 없음. 차라리 미리 font 들을 OS에 설치하는 게 좋겠음"이라고 적혀 있다(`H2OrestartImpl.java:318`).
  - v0.8.0에서 한글·영문 글꼴 이름 별칭(바탕/Batang 등)과 대체 글꼴 폭 보정(`FontWidthCorrection`)이 들어왔다.
  - 서버에는 OFL 글꼴을 설치하고, fontconfig 별칭으로 함초롬·HY·휴먼 계열 이름을 대체 글꼴에 연결한다(design 10.1).

**소스 빌드 (수정이 필요할 때만)**

- 빌드 스크립트가 없다. Eclipse LibreOffice 플러그인 프로젝트이고, `.unoproject`에 SDK 7.5.2.2와 Java가 지정돼 있다.
- 빌드 순서는 다음과 같다.
  1. LibreOffice SDK jar(`libreoffice.jar` 또는 juh·jurt·ridl·unoil)로 `source/**/*.java`를 Java 8 대상으로 컴파일한다.
  2. jar `MANIFEST.MF`에 `RegistrationClassName: ebandal.libreoffice.comp.RegistrationHandler`를 넣는다.
  3. `.oxt`(zip)에 `META-INF/manifest.xml`(jar는 `application/vnd.sun.star.uno-component;type=Java`, xcu는 `configuration-data`), `description.xml`, `registry/*.xcu`, 아이콘을 담는다.
- 구성은 v0.5.4 oxt에서 확인했다.
- 수정본을 배포하면 GPL 의무가 생긴다(5장). 그래서 수정은 **upstream 기여**를 먼저 검토한다.

### 3.3 충실도 한계

이슈 본문은 보지 못했다. 아래는 릴리스 노트, 커밋, 코드로 확인한 내용이다.

| 영역 | 동작 | 근거 | 우리 영향 |
|---|---|---|---|
| 양쪽 정렬 | JUSTIFY를 LibreOffice LEFT로 바꾼다. 주석: "양쪽정렬은 LEFT와 유사. 특히 LINE_BREAK가 있을때" | `ConvPara.java:214-215, 445-446`, 2025-04-06 커밋 | 보고서체 본문(양쪽 정렬)의 PDF가 오른쪽이 들쭉날쭉해지고 줄 나눔이 달라진다 |
| 장평 | 글꼴이 LibreOffice에 없으면 장평을 100%로 고정한다(100% 미만에서 폭이 커지는 버그 회피) | `ConvPara.java:627-632` | 한컴 글꼴이 없는 서버에서는 장평 조정이 사라지고 쪽수가 달라진다 |
| 줄간격 | 비율 줄간격에 경험 계수를 곱한다(HWP 24pt=8.5mm, LO=11mm라는 주석). v0.7.3에서 글꼴별 보정 추가(#52) | `ConvPara.java:286-304` | 줄 높이가 근사값이다 |
| 자간 | v0.8.0에서 자간 계산식을 고치고 대체 글꼴 폭을 보정(#82) | 릴리스 노트, `FontWidthCorrection.java` | 근사값이다 |
| 표 행 높이 | v0.8.0부터 고정 높이 대신 최소 높이. 내용이 잘리지 않는 대신 행이 늘어날 수 있다(#82) | `ConvTable.java:244-253` | 표가 많은 문서의 쪽수가 늘 수 있다 |
| 표 열 | 앵커 셀이 없는 열을 지우고 colSpan을 줄인다. 열 너비는 병합 셀에서 역산한다 | `ConvTable.java:117, 1275-1330, 1435-1505` | 대체로 정상 |
| 표 정렬·배치 | 표 양쪽 정렬은 가운데로 처리. 캡션 있는 표와 쪽 아래 정렬 표는 프레임에 넣는다 | 2025-12-26 커밋, v0.7.5 | 위치가 조금 다를 수 있다 |
| 셀 배경 | 그러데이션 셀은 중간색으로 칠한다(v0.6.0), 표 배경 채움(v0.7.8) | 릴리스 노트 | 장식 차이 |
| 차트 | HWPX `hp:switch`(한글 차트 개체 포함)를 무시한다 | `HwpParagraph.java:286-299` | **차트가 사라진다** |
| OLE·글맵시 | 회색 점선 "Not Supported Object" 상자로 바꾼다 | `ConvGraphics.java:165-168, 727-780` | HWP5의 OLE 차트, 엑셀 개체가 빈 상자가 된다 |
| 양식 개체·덧말·글자 겹침 | 무시한다 | `HwpParagraph.java:276-285` | 별지 체크 상자(양식 개체)가 빠진다. 글자 □/☑는 유지되고, v0.8.0부터 Wingdings 상자 기호를 유니코드로 바꾼다(#82) |
| 바탕쪽 | 바탕쪽 그림은 가운데 표시, 머리말·꼬리말에는 표시하지 않음(임시 조치) | 2025-04-19 커밋 | 워터마크나 로고 위치가 다를 수 있다 |
| 쪽 번호 | 쪽 번호 위치 컨트롤이 여러 번 있어도 한 번만 표시(#53). 머리말·꼬리말 안 표의 쪽 번호는 2026-11-16 커밋에서 출력 | 릴리스 노트, 최신 커밋 | 최신 버전을 쓴다 |
| 옛한글 | 한양 PUA를 첫가끝 코드로 바꾼다(#73). 지원 글꼴(Noto CJK, Un 계열) 필요 | v0.7.12 | 글꼴 설치 |
| 암호·배포용 | 문서 암호는 거부한다(`HwpFile.java:129-131`). 배포용 문서는 읽는다(HWP #42, HWPX v0.7.11) | 코드, 릴리스 노트 | 3.4 |
| 저장 | 가져오기 전용이라 HWP/HWPX로 저장할 수 없다(README) | registry | 생성은 python-hwpx만 |
| 결함 허용 | 맞지 않는 포맷과 도형 속 텍스트 문제로 멈추지 않는다(#78·#79). `META-INF/manifest.xml`이 없는 HWPX도 연다(smtech.go.kr 문서, `HwpxFile.java:145-151`) | v0.7.13~14 | 공공기관 파일 호환성 근거 |

**결론:** server 경로에서 H2Orestart PDF는 **쪽수와 레이아웃 판정의 근거가 될 수 없다.** 쪽수 판정 규칙(PAGE)은 hancom 경로를 쓴다. rhwp를 쓰려면 실측 검증을 먼저 한다. H2Orestart 결과는 미리보기와 원본 열람용으로 표시한다.

### 3.4 HWP 파싱 로직 비교 (vs python-hwpx `hwpx/hwp5/`)

| 항목 | H2Orestart | python-hwpx 6.12.0 | 판단 |
|---|---|---|---|
| CFB | 기본 FAT·MiniFAT·DIFAT. 루프나 크기 제한 검사는 거의 없다(`CompoundFile.java`) | 체인 범위·루프 검출, 스트림·디렉터리 수 제한, v3/v4 확인(`hwp5/cfb.py:100-215`) | python-hwpx |
| 구역 순서 | HWP5: CFB 디렉터리 순서 그대로(`HwpFile.java:381-394`). HWPX: 파일명 번호순(#62) | 번호 정렬 + 0..n-1 연속성 검사(`hwp5/reader.py:120-129`). HWPX는 content.hpf 기준 | python-hwpx |
| PARA_TEXT | 정규식으로 컨트롤 분리. 필드 시작, 숨은 설명, 책갈피, 양식 컨트롤은 무시(`HwpRecord_ParaText.java:51-175`) | 코드 단위로 char/inline/extended를 분해하고 잘못된 컨트롤 수를 센다(`hwp5/bodytext.py:21-80`) | python-hwpx |
| 표 | `cellzone`, 셀 목록 읽기(`Ctrl_Table.java:191-253`). 변환 단계에서 앵커 없는 열 제거 | 셀 목록을 `hp:tbl`로 변환(`hwp5/section_xml.py:1352-1407`). 그리드 조회는 덮이지 않은 칸에서 `IndexError` (`oxml/table.py:1004-1046`) | **H2Orestart의 정규화 아이디어를 DocIR 빌더에 반영** |
| 배포용 HWP5 | **ViewText 복호화.** `DISTRIBUTE_DOC_DATA`(256바이트) 시드로 MSVC `srand/rand` 수열을 만들어 XOR한 뒤 AES-128-ECB로 풀고 raw deflate로 압축 해제(`HwpFile.java:315-364, 396-409, 437-448`). 한컴 공개 문서 「한글문서파일형식_배포용문서_revision1.2」 기반이라고 주석에 적혀 있다(338-343행) | `hwp5-distribution`으로 거부(`hwp5/reader.py:24-28`) | **M1 이식 후보**(법률 검토 후) |
| 배포용 HWPX | manifest의 `odf:encryption-data`(salt, iv, iterCount, keySize, checksum)로 PBKDF2-HMAC-SHA1 키를 유도하고 AES-CBC로 푼 뒤 deflate 해제와 SHA-256 체크섬 확인. 시작 키는 **코드에 박힌 고정 문자열의 SHA-256**이다(`HwpxFile.java:59, 171-308`) | 암호화 파트는 "지원하지 않음" 오류(`opc/package.py:712-731`) | 공개 사양 근거를 확인하지 못했다. **법률 검토 전 보류** |
| PUA 기호 | Wingdings 상자 기호 8종을 유니코드로(F06E ■, F06F ☐, F071 ❑, F072 ❒, F0A7 ▪, F0A8 □, F0FD ☒, F0FE ☑, `ConvHypua2Unicode.java:20-31`). 한양 PUA 옛한글(E0BC-F8F7) 변환표 | 내보내기에서 목록 레이블일 때만 기호를 바꾼다. 매핑도 다르다(F06F→□, F0FE→□, `tools/exporter.py:91-109`). 본문 PUA는 그대로 둔다 | **값이 서로 다르다.** 평가표·별지의 체크(■/☑) 판정에 쓰려면 우리 정규화 표를 따로 두고 Wingdings 대응표로 검증한다 |
| 번호 머리 계산 | `compare/CompNumbering`으로 문단 번호 문자열 계산, `HwpComparer -print` | `tools/exporter.py`의 `_ListLabels` | python-hwpx. H2Orestart는 교차검증용 3번째 경로 후보 |
| 결함 허용 사례 | 커밋에 실제 문서 결함이 기록돼 있다(아래) | 오류 코드 체계(`hwp5/errors.py`) | 회귀 픽스처 시나리오로 쓴다 |

회귀 시험에 넣을 결함 사례(H2Orestart 커밋·릴리스 노트 출처):

- CFB minor revision이 0x3E 미만인 파일 (#68)
- 글꼴 face 이름이 없는 파일 (#68)
- `hp:outMargin`이나 `drawText` 값 4294967295 (#51·#56)
- `centerX`가 int 범위를 넘는 값 (#64)
- 컨트롤 처리 중 `CtrlHeader`가 다시 나와 무한 루프가 생기는 경우
- `ColumnDef` 뒤에 `SectionDef`가 오는 순서
- HWP 문단 정렬 값이 NONE인 경우
- UINT8 스타일 ID를 부호 있는 값으로 읽는 오류
- `META-INF/manifest.xml`이 없는 HWPX
- 도형 안 텍스트 (#79)
- 숨은 셀 병합 (#60)

**M1 결론**

1. 주 경로는 python-hwpx를 유지한다.
2. 배포용 HWP5는 한컴 공개 문서 기준으로 **복호화 모듈을 별도 구현(또는 GPL 이식)** 한다. 이 모듈은 설정으로 켜고, 사용 여부를 감사 로그에 남긴다.
3. 배포용 HWPX와 그 밖의 실패 문서는 **H2Orestart로 PDF·DOCX 변환 후 파싱하는 폴백**을 둔다. DOCX 내보내기는 Writer 문서이므로 가능할 것으로 보이나 검증이 필요하다. 이 경로의 쪽 번호는 한글과 다르므로 Locator에 출처를 표시한다.
4. 표 정규화와 PUA 기호 정규화는 재구현한다.

### 3.5 보안 메모

- **XXE 미방어:** HWPX XML을 기본 설정의 `DocumentBuilderFactory`로 파싱한다(`HwpxFile.java:310-323`). `setFeature` 같은 방어 설정이 저장소 어디에도 없다.

  사용자가 올린 HWPX를 넣으면 외부 엔티티로 서버 파일 내용이 PDF에 섞일 수 있다고 보고 다음과 같이 대비한다.

  - 변환 전에 우리 쪽에서 defusedxml로 모든 XML 파트를 검사한다. DOCTYPE과 ENTITY가 있으면 거부한다.
  - soffice는 네트워크 없는 샌드박스에서 비특권 사용자로, 읽기 전용 입력으로 실행한다.
- **로그 유출:** 3.2절에서 다뤘다. 로그와 임시 파일은 작업 폴더 안에만 두고 끝나면 지운다.
- **배포용 해제:** 결과물이 원본보다 많은 권한을 갖게 된다(편집·복사 가능). 해제한 텍스트는 DocIR 분석 용도로만 쓰고 원문을 재배포하지 않는다는 정책이 필요하다.

---

## 4. 이식 계획표

이식 유형은 네 가지로 나눈다.

- **코드 이식**: 원본 코드를 옮겨 수정한다(파생 저작물).
- **재구현**: 동작과 사실만 참고해 우리 코드로 새로 쓴다.
- **외부 프로세스**: 별도 프로그램으로 호출한다.
- **아이디어**: 설계 참고만 한다.

| # | 그쪽 구성요소 (위치) | 우리 모듈 | 이식 유형 | 제안서용 조정 | 마일스톤 | 이식 시 라이선스 의무 |
|---|---|---|---|---|---|---|
| 1 | hwpx-docs 개조식 프리셋 (`presets/report-gongmun.json`, `text/markdown.py:65-189`, `text/mdparse.py:97-175`) | render (`styles.py`, `gaejo.py`), `config/styles/report.yaml` | 재구현 | 값은 design 10.2절 기준(제목 22, 장 18, 절 16, 항 14 굵게, 본문 13, 표 10.5, 주석 11pt, 줄간격 160/130%). 기호 □→○→-→·→※. 번호 Ⅰ.→1.→가.→1)→가)는 글자로 넣는다. 장 막대와 거버닝 메시지 상자 추가. `끝.` 미사용(공문 아님). 블라인드 모드에서 CI 색 제거 | M2 | 없음(재구현). 값 표를 그대로 복사하면 AGPL 고지 필요 |
| 2 | hwpx-docs 실측 규칙 (`docs/rules.md` H05·H08·H12·H16·H25·S02·S04·S08·T02~T04·W05) | render 구현 규칙, check(HWPX 린트), tests | 아이디어(사실 차용, 우리 문장으로 다시 씀) | 개조식 내어쓰기, 어절 줄바꿈, 기호 글꼴 7개 언어, 표 앞뒤 간격은 표 바깥 여백으로 | M2 | 없음. 출처는 표기 권장 |
| 3 | hwpx-docs 표 배치·격자선 (`table/table.py:19-104`), `core/read.py:730-741` `solve()` | render (`tables.py`), parse (열 너비 복원) | 재구현 | 요구사항 대응표(ID·요구사항·대응방안·쪽), 평가항목 매핑표 템플릿. 머리 행 #D9D9D9 굵게 + 반복. 바깥선 0.4mm, 안쪽 0.12mm. 쪽 나눔은 CELL | M2 | 없음 |
| 4 | hwpx-docs 차트 생성 (`chart/ooxml.py:54-208`, `chart/section.py:15-54`, `chart/rules.md` CH01~CH14) | render (`charts.py`) | **코드 이식** 또는 ECMA-376과 CH 규칙 기반 재구현(권장) | 중립 블루 3색 이내 팔레트, 경로별 글꼴, "(단위: 백만 원)" 축 제목, 출처 캡션. server 경로용 PNG 동시 생성(H2Orestart는 차트를 버림). 블라인드면 CI 색 금지 | M3 (도식·차트 자동 렌더) | 이식하면 AGPL-3.0-or-later 코드가 된다. 저작권 표시와 변경 표시(GPLv3·AGPLv3 §5a), **AGPL §13 네트워크 소스 제공**(M4 Web·API 시점) |
| 5 | hwpx-docs 도형 차트 (`objects/objects.py:134-204`) | render (`charts.py` 대체 경로) | 아이디어 | 한글 차트 개체를 지원하지 않는 렌더러를 위한 벡터 대체본 | M3 | 없음 |
| 6 | hwpx-docs header 등록부 (`core/header.py:10-246`) | render | 아이디어만. python-hwpx `ensure_*`로 대체 | – | M2 | 없음 |
| 7 | hwpx-docs 머리말·꼬리말·쪽 번호 (`page/page.py:58-72`) | render | 아이디어. python-hwpx `page.*` 사용 | 머리말 `{사업명}`(블라인드면 업체명 금지), 꼬리말 `- n -`, 표지·목차 쪽 번호 처리(`restart_page_number`, `hide_first_footer`) | M2 | 없음 |
| 8 | hwpx-docs 정적 차례·2단계 쪽 번호 (`fields/refs.py:138-166`, rules X05) | render (`toc.py`), package (PDF 북마크) | 아이디어 | hancom 경로는 python-hwpx 고유 차례 + 한글 새로 고침. server 경로는 rhwp 쪽 지도로 2단계 빌드. 같은 쪽 지도를 추적표 "쪽" 열에도 쓴다 | M2(골격), M3(쪽 확정) | 없음 |
| 9 | hwpx-docs 별지 편집·검사 (`edit/edit.py:188-329`, `edit/guard.py:24-107`) | render(별지 채우기), check(FORM 규칙) | 아이디어. python-hwpx `fill_by_path`·`find_cell_by_label`·`form_fit` 위에 얹는다 | 별지 라벨 사전(상호, 대표자, 사업자등록번호, 사업명 등). 라벨 앞 ☐→☑. 잔여 `○○`·`{{…}}`·`XXX`·`___` 검출. 구조 지문 비교(셀 격자, 개체 수, header) | M3 | 없음 |
| 10 | hwpx-docs 가독성 점검 (`check/readability.py` RD01~RD13) | check (FMT 규칙) | 재구현 | 하한은 RFP 값 우선(예: 표 12pt 지정 시 RD04 기준 변경). 어절 줄바꿈 권장, 빈 문단 남용, 머리 행 표시·반복 | M2 | 없음 |
| 11 | hwpx-docs pagefit 읽기 단위·유지 규칙 (`pagefit/rules.md` PF15~PF28) | render 후처리, check (PAGE) | 아이디어 | 제목+첫 내용, 표+캡션 묶기. 긴 표는 머리 행 반복과 앞뒤 최소 3행. 평가항목 단위 새 쪽 시작 옵션. 쪽수 예산 안에서만 조정 | M3 | 없음 |
| 12 | hwpx-docs 서식 질의 DSL (`check/check_xml.py`) | check (RFP 서식 요구 검증) | 아이디어. python-hwpx `format_rules` 보완 | "본문 13pt 이상, 표 12pt 이상" 같은 RFP 요구를 유효 서식 질의로 검증 | M2 | 없음 |
| 13 | hwpx-docs Preview·메타데이터 처리 (`edit/edit.py:316-329`, `secure/mask.py`, `core/build.py:225`) | package, check (BLD) | 아이디어 | `Preview/PrvText.txt`·`PrvImage.png` 재생성 또는 삭제, content.hpf `creator`·`lastsaveby` 비우기(python-hwpx `parts.clear_preview`·`clear_document_metadata`). 회사명이 남았는지 검사 | M3 | 없음 |
| 14 | hwpx-docs 한글 COM 운영 지식 (`render/hwpcom.py`, `convert/convert.py`, rules C01~C10) | Windows 렌더 에이전트(hancom 경로) | 아이디어. pyhwpx(MIT) 사용 | 숨김 새 인스턴스, 배치당 한글 1개, 보안 모듈은 사용자가 직접 켬, 새 임시 경로에 SaveAs, 창 응답 대행 금지 | M3 | 없음 |
| 15 | hwpx-docs 픽스처 271개 (`tests/fixtures/*.hwpx`) | tests (parse 회귀 M1, render 비교 M2) | 외부 데이터. 커밋 SHA를 고정해 CI에서 내려받고 저장소에는 넣지 않는다 | 셀 병합, 테두리, 쪽 설정 등 표준 사례를 parse 교차검증에 쓴다 | M1~M2 | 저장소에 넣거나 배포하면 AGPL 사본 고지와 소스 제공. 내려받기 방식이면 배포가 아니다 |
| 16 | hwpx-docs 공문 문장 검사기 (`skills/gongmun-style/scripts/check_gongmun.py`, `references/levels.json`) | check (LANG) | 아이디어. 근거 원문(행정업무운영 편람, 시행규칙, 한글 맞춤법)에서 규칙을 직접 만든다 | 날짜 `2026. 11. 16.(월)` 같은 표기 규칙은 차용. 항목 기호 체계는 제안서 기준(Ⅰ.→1.→가.)으로 따로 정의 | M2·M4 | 없음. 원 출처는 공공저작물·법령 |
| 17 | H2Orestart + LibreOffice (확장 전체) | render PDF(server 보조 경로), parse 폴백(HWP/HWPX→PDF·DOCX) | **외부 프로세스** | OFL 글꼴 설치와 fontconfig 별칭, 작업별 프로필·캐시·타임아웃, 결과 검증. 쪽수 판정에는 쓰지 않음. 결과에 렌더 경로를 표시 | M3 (PDF), M1 (폴백) | 수정하지 않은 패키지를 apt로 쓰면 추가 의무 없음. 우리 Docker 이미지에 넣어 배포하면 GPL 소스 제공(§6)과 고지 |
| 18 | H2Orestart HWP5 배포용 복호화 (`HwpFile.java:315-364, 396-409, 437-448`) | parse (`hwp5_distribution.py`) | 코드 이식(GPL→GPL 호환) 또는 한컴 공개 문서 기반 재구현(권장) | 설정으로 켬, 감사 로그 기록, 해제 텍스트 재배포 금지 고지. 복호화한 레코드 스트림을 python-hwpx 레코드 파서에 넣는 방식은 검증 필요 | M1 | 이식하면 "Copyright (C) 2023 ebandal" 유지, 변경 표시, GPL-3.0-or-later. **저작권법 제104조의2(기술적 보호조치) 관련 법률 검토 선행** |
| 19 | H2Orestart HWPX 배포용 복호화 (`HwpxFile.java:59, 171-308`) | parse | **보류**. 법률 검토 후 결정. 대안은 #17 폴백 | – | M1 이후 | 이식하면 GPL. 고정 키 사용이므로 법률 검토 필수 |
| 20 | H2Orestart 표 정규화 (`ConvTable.java:1275-1330` 앵커 없는 열 제거, 1332-1505 열 너비 역산) | parse (DocIR 빌더) | 재구현 | 요구사항·평가표 셀 주소가 파서마다 같아야 이중 파싱 비교가 된다. 덮이지 않은 칸은 가상 빈 셀로 채운다 | M1 | 없음 |
| 21 | H2Orestart 기호·옛한글 정규화 (`ConvHypua2Unicode.java:8-31, 5700-5724`) | parse (텍스트 정규화) | 재구현. Wingdings 공개 대응표로 검증. 옛한글은 라이선스가 확인된 변환표나 패키지 사용 | ■/□/☑/☒ 체크 판정(평가표 "해당 ■", 별지 체크) | M1 | 변환표를 이식하면 GPL 고지 |
| 22 | H2Orestart 결함 사례 (커밋·릴리스 노트, 3.4절) | tests (parse 회귀) | 아이디어 | 공공기관 실제 파일 유형별 픽스처(합성) | M1 | 없음 |
| 23 | H2Orestart `compare/HwpComparer` (-print/-diff) | parse 교차검증(3번째 경로), 7.11 정정공고 비교 | 외부 프로세스(직접 빌드 필요, 릴리스 jar 포함 여부 확인 필요) 또는 아이디어 | 번호 머리 포함 문단 덤프를 사전규격과 본공고 문단 diff에 활용 | M4 | 빌드한 jar를 배포하면 GPL 소스 제공 |
| 24 | H2Orestart JUSTIFY→LEFT 매핑 (`ConvPara.java:214-215, 445-446`) | (upstream) | 패치 기여 후보. 줄바꿈 컨트롤이 없는 문단은 BLOCK으로 | 보고서체 미리보기 품질 | M3 이후 | 기여는 upstream 라이선스(GPL)로 |

---

## 5. 라이선스 의무 정리

### 5.1 hwpx-docs (AGPL-3.0-or-later)

**결합 가능성**

- GPLv3 제13조는 GPLv3 저작물을 AGPLv3 저작물과 하나로 결합해 전달하는 것을 허용한다.
- 이때 GPL 부분에는 GPL 조건이 남는다. 다만 결합물 전체에 AGPLv3 제13조(네트워크 상호작용)의 특별 요구가 적용된다.
- 그래서 우리 저장소(GPL-3.0)에 hwpx-docs 코드를 넣을 수는 있다.

**네트워크 의무 (AGPLv3 제13조)**

- 의무가 생기는 조건: 수정한 프로그램을 네트워크로 원격 사용자에게 제공할 때다.
- 해야 할 일: 그 사용자들에게 **실행 중인 버전의 대응 소스 전체**를 받을 기회를 눈에 띄게 제공해야 한다.
- 우리 상황에 대입하면 다음과 같다.
  - M1~M3의 local CLI 단일 사용자에게는 원격 사용자가 없다.
  - M4의 FastAPI와 Web UI부터 실제 의무가 생긴다.
  - 고객이 on-prem에서 수정해 서비스로 운영하면 고객에게도 같은 의무가 넘어간다. AGPL을 금지하는 조직의 도입 장벽이 될 수 있다.

**고지 의무**

- 원 저작권 표시를 유지한다. 원본에는 파일별 머리말이 없으므로 "Copyright (C) 2026 BlackBuddle"을 옮긴 파일 머리말과 `NOTICE`에 적는다.
- 라이선스 사본을 함께 둔다(`LICENSES/AGPL-3.0-or-later.txt`).
- 수정 사실과 날짜를 눈에 띄게 적는다(§5a).
- 옮긴 파일에는 `SPDX-License-Identifier: AGPL-3.0-or-later`를 표기한다.

**권고안**

1. 1~3, 5~16번은 재구현이나 아이디어로 처리한다. 코드를 옮기지 않으면 AGPL 의무가 생기지 않는다. 사실, 수치, 실측 규칙은 저작권 보호 대상이 아니다. 단, 문장이나 표를 그대로 복사하면 안 된다.
2. 차트 생성기(4번)만 코드 이식을 검토한다.
   - 이식하면 `src/rfpgen/render/_agpl/chart_ooxml.py`처럼 **별도 하위 패키지로 격리**한다.
   - 파일 머리말에 출처 커밋(`ffe24ee`), 원 저작권, 변경 내역을 적는다.
   - M4에서 API·UI에 "소스 받기" 링크(실행 커밋의 소스 아카이브)를 노출한다.
   - 다만 ECMA-376 사양과 CH 규칙(사실)만으로 재구현하는 비용이 크지 않다. 약 150줄이다. 그래서 **재구현을 우선 권고**한다.
3. 픽스처(15번)는 저장소에 넣지 않는다. 커밋 SHA를 고정해 내려받는다.

### 5.2 H2Orestart (GPL-3.0-or-later)

- 우리와 같은 GPL-3.0 계열이라 코드 이식이 가능하다.
- 이식할 때의 의무는 세 가지다.
  - 저작권 표시("Copyright (C) 2023 ebandal")와 라이선스 고지를 유지한다.
  - 변경 사실과 날짜를 표시한다(§5a).
  - 전달할 때 대응 소스를 제공한다(§6).

  우리 저장소가 GPL 공개 소스이므로 실무 부담은 작다. 머리말이 없는 10개 파일(예: `ConvHypua2Unicode.java`)도 저장소 `COPYING`(GPL-3.0)을 따른다.
- **외부 프로세스로 쓰는 경우**는 GPL의 "집합물"이다. 우리 코드에는 영향이 없다.
  - 사용자가 apt로 설치한 수정 없는 패키지를 호출하면 추가 의무가 없다.
  - 우리가 Docker 이미지나 설치 패키지에 `.oxt`나 LibreOffice를 넣어 배포하면, 그 바이너리에 대한 소스 제공(또는 서면 제안)과 라이선스 고지를 한다.
- 배포용 문서 복호화(18·19번)는 라이선스와 별개로 **저작권법상 기술적 보호조치 무력화 금지(제104조의2)와의 관계**를 법률 검토로 확인한다.
  - 공고 첨부(공공저작물)를 분석 목적으로 읽는 경우의 예외 적용 여부를 본다.
  - 결과가 나오기 전에는 기능을 기본으로 끄고 폴백(#17)으로 처리한다.

### 5.3 design.md에 반영할 제안 (이 문서는 design.md를 수정하지 않음)

- 11.1절 표: hwpx-docs 행을 "참고만(코드 미사용)"에서 다음으로 바꾼다. "재구현·아이디어 중심. 차트 생성기는 격리 이식 후보(AGPL §13 의무 명시)."
- 11.2절: AGPL 코드를 이식할 때의 격리 위치, 고지 방식, M4 "소스 받기" 의무를 적는다.
- 7.2절 parse 표에 배포용 HWP5 경로(복호화 모듈, 기본 꺼짐)와 H2Orestart 변환 폴백을 추가한다. Locator의 쪽 번호에 출처(렌더 경로)를 기록한다.
- 7.9절 PDF 변환 표: H2Orestart를 "열람·폴백 전용. 양쪽 정렬, 장평, 차트 손실 때문에 쪽수 판정에 쓰지 않음"으로 한정한다. 차트는 PNG 대체본을 함께 둔다.
- 7.9절 렌더 검증에 "렌더러가 그리지 못한 개체는 경고로 남김(침묵 금지)" 원칙을 넣는다. hwpx-docs의 `PREVIEW NOT DRAWN` 패턴과 H2Orestart의 "Not Supported Object" 상자를 감지한다.

---

## 6. 확인하지 못한 것과 후속 확인 항목

| 항목 | 상태 | 할 일 |
|---|---|---|
| H2Orestart GitHub 이슈 본문·미해결 목록 | 세션에서 API와 웹 접근이 403 | 이슈 권한이 있는 환경에서 #27·#42·#52·#60·#62~#83 본문 확인 |
| `--infilter="Hwp2002_File"` 동작 | README와 등록 필터 이름(`Hwp2002_Reader`)이 다름 | 설치 후 HWP·HWPX 각각 변환 시험 |
| H2Orestart로 DOCX 내보내기(파싱 폴백) | 가능할 것으로 보이나 미검증 | 표 병합 보존 여부를 시험 |
| 릴리스 jar에 `compare/` 포함 여부 | 저장소 oxt(v0.5.4)는 compare 패키지보다 오래됨 | v0.8.0 jar 목록 확인 |
| Wingdings PUA 대응 | H2Orestart와 python-hwpx 매핑이 다름(F06F, F0FE) | 공개 문자표로 검증하고 우리 정규화 표 확정 |
| rhwp의 한글 차트 개체·누름틀 안내문 렌더 | 미확인 | M2 렌더 비교 시험에 포함 |
| 배포용 문서 해제의 법적 성격 | 미검토 | 법률 검토 (5.2) |
| python-hwpx 사용자 정의 개요 번호(idRef) | python-hwpx 스스로 "미실측"이라 표시 | 번호는 글자로 넣는 방식으로 우회 (2.10) |
| hwpx-docs 차트 CH12~CH14(영역형, 분산형, 보조 축) | 원저자도 "Hangul render still to be checked" | 쓰려면 hancom 경로로 확인 |

---

## 부록. 참조 경로

- hwpx-docs 소스: `/tmp/claude-0/-home-user-auto-rfp-generator/f3d3ff9a-3973-59c5-bd3d-f4f9b614b83d/scratchpad/ext/hwpx-docs/`
- H2Orestart 소스: `/tmp/claude-0/-home-user-auto-rfp-generator/f3d3ff9a-3973-59c5-bd3d-f4f9b614b83d/scratchpad/ext/H2Orestart/`
- python-hwpx 6.12.0 wheel 압축 해제본: `/tmp/claude-0/-home-user-auto-rfp-generator/f3d3ff9a-3973-59c5-bd3d-f4f9b614b83d/scratchpad/hwpx_wheel/hwpx/`
- LibreOffice 확장 페이지 사본(릴리스 노트): `/tmp/claude-0/-home-user-auto-rfp-generator/f3d3ff9a-3973-59c5-bd3d-f4f9b614b83d/scratchpad/web/lo_ext.html`
- 위 경로는 스크래치 영역이라 정리될 수 있다. 다시 받을 때는 1장의 커밋 SHA로 고정한다.
