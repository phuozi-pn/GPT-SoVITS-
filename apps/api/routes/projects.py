from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session, get_trace_id
from apps.api.exceptions import raise_domain_http
from domains.projects.service import ProjectService, ProjectServiceError
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from voice_platform.job.schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectRoleRequest,
    ProjectRoleResponse,
)

router = APIRouter()


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[ProjectResponse]:
    return ProjectService(session).list_projects(user_id)


@router.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(
    body: ProjectCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> ProjectResponse:
    try:
        return ProjectService(session).create_project(owner_user_id=user_id, name=body.name)
    except ProjectServiceError as exc:
        raise_domain_http(exc)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> ProjectResponse:
    try:
        return ProjectService(session).get_project(project_id, user_id)
    except ProjectServiceError as exc:
        raise_domain_http(exc)


@router.post("/projects/{project_id}/roles", response_model=ProjectRoleResponse, status_code=201)
def bind_project_role(
    project_id: UUID,
    body: ProjectRoleRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> ProjectRoleResponse:
    try:
        return ProjectService(session).bind_role(
            project_id=project_id,
            owner_user_id=user_id,
            role_name=body.role_name,
            voice_version_id=body.voice_version_id,
        )
    except ProjectServiceError as exc:
        raise_domain_http(exc)


@router.post("/projects/{project_id}/batch", status_code=202)
def submit_batch_csv(
    project_id: UUID,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    trace_id: str = Depends(get_trace_id),
    session: Session = Depends(get_session),
):
    raw = file.file.read()
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail={"code": "CSV_TOO_LARGE", "message": "CSV max 2MB"},
        )
    try:
        return ProjectService(session).submit_csv_batch(
            project_id=project_id,
            owner_user_id=user_id,
            csv_bytes=raw,
            trace_id=trace_id,
        )
    except ProjectServiceError as exc:
        raise_domain_http(exc)
