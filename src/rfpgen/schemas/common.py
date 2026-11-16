"""모든 산출물이 공유하는 기본 타입: 근거 위치와 추출값."""

from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

Method = Literal["rule", "llm", "human"]
Status = Literal["proposed", "confirmed", "rejected"]


class Locator(BaseModel):
    """추출값이 RFP 원문의 어디에서 왔는지 가리킨다.

    ``quote``는 블록 텍스트에 실제로 포함되어야 하며, 검증 대상이다.
    """

    doc_id: str
    block_id: str
    page: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    quote: str = ""


class Extracted(BaseModel, Generic[T]):
    """값과 근거, 추출 방법, 확정 상태를 함께 담는다."""

    value: T
    locators: list[Locator] = Field(default_factory=list)
    method: Method = "rule"
    confidence: float = 1.0
    status: Status = "proposed"
    note: str | None = None
