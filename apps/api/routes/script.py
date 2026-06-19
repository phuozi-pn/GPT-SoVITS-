from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id
from apps.api.exceptions import raise_domain_http
from domains.script.service import ScriptParseService, ScriptParseServiceError
from fastapi import APIRouter, Depends
from voice_platform.script.schemas import (
    ScriptParseSmartRequest,
    ScriptParseSmartResponse,
    ScriptParseStatusResponse,
)

router = APIRouter()
_service = ScriptParseService()


@router.get("/script/parse-smart/status", response_model=ScriptParseStatusResponse)
def parse_smart_status(_: UUID = Depends(get_current_user_id)) -> ScriptParseStatusResponse:
    status = _service.status()
    return ScriptParseStatusResponse(**status)


@router.post("/script/parse-smart", response_model=ScriptParseSmartResponse)
def parse_smart(
    body: ScriptParseSmartRequest,
    _: UUID = Depends(get_current_user_id),
) -> ScriptParseSmartResponse:
    try:
        lines = _service.parse_smart(body.text)
    except ScriptParseServiceError as exc:
        raise_domain_http(exc)

    characters = {line.character for line in lines}
    return ScriptParseSmartResponse(
        mode="llm",
        lines=lines,
        line_count=len(lines),
        character_count=len(characters),
    )
