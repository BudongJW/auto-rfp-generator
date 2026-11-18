"""도식 스펙(설계서 6.6절 DiagramSpec, 7.9절 '도식').

도식은 그림 파일이 아니라 스펙(JSON)으로 저장한다. 렌더러가 스펙을 SVG로 그리고 PNG(200dpi)로 바꿔
HWPX 본문과 PPTX 장표에 넣는다. 사람은 스펙을 고쳐 다시 렌더한다(strategy/figures/<id>.json).

종류
- org    조직도·추진체계도: nodes의 parent로 나무를 만든다. group="external"은 발주기관·감리 같은 바깥 조직
         (뿌리 위·옆에 점선으로), group="support"는 PM 옆 지원 조직(품질보증 등)
- wbs    작업 분할: nodes 나무(뿌리 → 단계 가로 → 활동 세로)
- flow   추진 절차: nodes 순서대로 화살표 단계, note는 단계별 세부 항목(줄바꿈 구분)
- gantt  일정: months 칸, tasks 막대(개월 단위, 소수 허용)와 이정표(milestone)
- layers 시스템 구성도: layers 위→아래 띠(side=True는 오른쪽 세로 띠)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DiagramKind = Literal["org", "wbs", "flow", "gantt", "layers"]
KIND_KO: dict[str, str] = {"org": "조직도", "wbs": "WBS", "flow": "추진 절차", "gantt": "추진 일정", "layers": "시스템 구성도"}


class DiagramNode(BaseModel):
    id: str
    label: str
    parent: str = ""
    group: str = ""                 # org: external | support
    note: str = ""                  # 둘째 줄(인원·등급) 또는 flow 단계의 세부 항목(줄바꿈 구분)


class DiagramEdge(BaseModel):
    src: str
    dst: str
    label: str = ""
    style: Literal["solid", "dashed"] = "solid"


class GanttTask(BaseModel):
    label: str
    start: float                    # 착수 기준 개월(0부터)
    end: float
    group: str = ""
    milestone: bool = False


class DiagramLayer(BaseModel):
    name: str
    items: list[str] = Field(default_factory=list)
    side: bool = False


class DiagramSpec(BaseModel):
    schema_version: str = "1"
    id: str                         # 절 ID + 종류, 예: "S-3-2-gantt"
    kind: DiagramKind
    title: str                      # 캡션
    origin: Literal["auto", "human", "llm"] = "auto"
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    months: int = 0
    tasks: list[GanttTask] = Field(default_factory=list)
    layers: list[DiagramLayer] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)   # 만들 때의 가정(점검 결과로 보고, 그림에는 안 넣음)

    def labels(self) -> list[str]:
        """그림에 들어가는 글(블라인드·자리표시자 점검용). 눈금 숫자는 넣지 않는다."""
        out = [self.title]
        out += [n.label for n in self.nodes] + [n.note for n in self.nodes if n.note]
        out += [e.label for e in self.edges if e.label]
        out += [t.label for t in self.tasks]          # group은 막대 색 구분용(그림에 쓰지 않음)
        for layer in self.layers:
            out += [layer.name, *layer.items]
        return [x for x in out if x]
