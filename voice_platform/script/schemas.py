from __future__ import annotations

from pydantic import BaseModel, Field


class ScreenplayLineSchema(BaseModel):
    character: str
    text: str


class ScriptParseSmartRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)


class ScriptParseSmartResponse(BaseModel):
    mode: str = "llm"
    lines: list[ScreenplayLineSchema]
    line_count: int
    character_count: int


class ScriptParseStatusResponse(BaseModel):
    enabled: bool
    provider: str = "deepseek"
    model: str
