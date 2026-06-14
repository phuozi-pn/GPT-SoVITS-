from __future__ import annotations

import csv
import io
from uuid import UUID

from domains.compliance.gateway import ComplianceGateway, ComplianceError
from voice_platform.job.repository import JobRepository, ProjectRepository, VoiceVersionRepository
from voice_platform.job.schemas import (
    BatchLinePayload,
    BatchPayload,
    BatchSubmitResponse,
    JobStatus,
    ProjectResponse,
    ProjectRoleResponse,
)
from voice_platform.quota.exceptions import QuotaExceededError
from voice_platform.quota.repository import QuotaRepository


class ProjectServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class ProjectService:
    def __init__(self, session) -> None:
        self._session = session
        self._projects = ProjectRepository(session)
        self._versions = VoiceVersionRepository(session)
        self._jobs = JobRepository(session)
        self._quota = QuotaRepository(session)
        self._gateway = ComplianceGateway()

    def create_project(self, *, owner_user_id: UUID, name: str) -> ProjectResponse:
        row = self._projects.create(owner_user_id=owner_user_id, name=name)
        return ProjectResponse(project_id=row.id, name=row.name, roles=[])

    def list_projects(self, owner_user_id: UUID) -> list[ProjectResponse]:
        out: list[ProjectResponse] = []
        for p in self._projects.list_for_user(owner_user_id):
            roles = [
                ProjectRoleResponse(
                    role_id=r.id,
                    project_id=r.project_id,
                    role_name=r.role_name,
                    voice_version_id=r.voice_version_id,
                )
                for r in self._projects.list_roles(p.id)
            ]
            out.append(ProjectResponse(project_id=p.id, name=p.name, roles=roles))
        return out

    def get_project(self, project_id: UUID, owner_user_id: UUID) -> ProjectResponse:
        if not self._projects.user_owns(project_id, owner_user_id):
            raise ProjectServiceError("PROJECT_NOT_FOUND", "Project not found", 404)
        p = self._projects.get(project_id)
        assert p is not None
        roles = [
            ProjectRoleResponse(
                role_id=r.id,
                project_id=r.project_id,
                role_name=r.role_name,
                voice_version_id=r.voice_version_id,
            )
            for r in self._projects.list_roles(project_id)
        ]
        return ProjectResponse(project_id=p.id, name=p.name, roles=roles)

    def bind_role(
        self,
        *,
        project_id: UUID,
        owner_user_id: UUID,
        role_name: str,
        voice_version_id: UUID,
    ) -> ProjectRoleResponse:
        if not self._projects.user_owns(project_id, owner_user_id):
            raise ProjectServiceError("PROJECT_NOT_FOUND", "Project not found", 404)
        if not self._versions.user_can_access(voice_version_id, owner_user_id):
            raise ProjectServiceError("VOICE_NOT_FOUND", "Voice version not accessible", 404)
        row = self._projects.upsert_role(
            project_id=project_id,
            role_name=role_name.strip(),
            voice_version_id=voice_version_id,
        )
        return ProjectRoleResponse(
            role_id=row.id,
            project_id=row.project_id,
            role_name=row.role_name,
            voice_version_id=row.voice_version_id,
        )

    def submit_csv_batch(
        self,
        *,
        project_id: UUID,
        owner_user_id: UUID,
        csv_bytes: bytes,
        trace_id: str,
    ) -> BatchSubmitResponse:
        if not self._projects.user_owns(project_id, owner_user_id):
            raise ProjectServiceError("PROJECT_NOT_FOUND", "Project not found", 404)

        role_map = {
            r.role_name: r.voice_version_id for r in self._projects.list_roles(project_id)
        }
        if not role_map:
            raise ProjectServiceError(
                "ROLES_EMPTY",
                "Bind at least one role before batch synthesis",
                400,
            )

        lines = _parse_csv(csv_bytes, role_map)
        total_chars = sum(len(line.text) for line in lines)
        try:
            self._quota.ensure_chars_available(owner_user_id, total_chars)
        except QuotaExceededError as exc:
            raise ProjectServiceError("QUOTA_EXCEEDED", exc.message, 402) from exc

        for line in lines:
            if not self._versions.user_can_access(line.voice_version_id, owner_user_id):
                raise ProjectServiceError(
                    "VOICE_NOT_GRANTED",
                    f"Role {line.role} voice not accessible",
                    403,
                )
            try:
                self._gateway.validate_synthesis(
                    user_id=owner_user_id,
                    voice_version_id=line.voice_version_id,
                    text=line.text,
                    has_voice_access=True,
                )
            except ComplianceError as exc:
                raise ProjectServiceError(exc.code, exc.message, exc.http_status) from exc

        payload = BatchPayload(project_id=project_id, lines=lines)
        record = self._jobs.create_batch_job(
            owner_user_id=owner_user_id,
            payload=payload,
            trace_id=trace_id,
        )
        from voice_platform.job.queue import RedisJobQueue

        depth = RedisJobQueue().enqueue_batch(record.job_id)
        return BatchSubmitResponse(
            job_id=record.job_id,
            status=JobStatus(record.status),
            line_count=len(lines),
            queue_position=depth,
        )


def _parse_csv(csv_bytes: bytes, role_map: dict[str, UUID]) -> list[BatchLinePayload]:
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ProjectServiceError("CSV_INVALID", "CSV must have header row", 400)

    fields = {f.strip().lower(): f for f in reader.fieldnames if f}
    role_key = fields.get("role") or fields.get("角色") or fields.get("role_name")
    text_key = fields.get("text") or fields.get("台词") or fields.get("line")
    if not role_key or not text_key:
        raise ProjectServiceError(
            "CSV_INVALID",
            "CSV headers must include role,角色 and text,台词",
            400,
        )

    lines: list[BatchLinePayload] = []
    for idx, row in enumerate(reader, start=1):
        role = (row.get(role_key) or "").strip()
        line_text = (row.get(text_key) or "").strip()
        if not role and not line_text:
            continue
        if not role or not line_text:
            raise ProjectServiceError(
                "CSV_INVALID",
                f"Row {idx}: role and text required",
                400,
            )
        if role not in role_map:
            raise ProjectServiceError(
                "ROLE_UNBOUND",
                f"Row {idx}: role '{role}' not bound in project",
                400,
            )
        lines.append(
            BatchLinePayload(
                index=idx,
                role=role,
                text=line_text,
                voice_version_id=role_map[role],
            )
        )

    if not lines:
        raise ProjectServiceError("CSV_EMPTY", "No data rows in CSV", 400)
    if len(lines) > 500:
        raise ProjectServiceError("CSV_TOO_LARGE", "Max 500 lines per batch", 400)
    return lines
