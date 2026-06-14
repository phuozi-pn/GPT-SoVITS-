from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from voice_platform.job.models import (
    ConsentRow,
    JobRow,
    ProjectRoleRow,
    ProjectRow,
    VoiceAssetRow,
    VoiceRow,
    VoiceVersionRow,
)
from voice_platform.job.schemas import (
    JOB_SCHEMA_VERSION,
    BatchPayload,
    InferPayload,
    JobRecord,
    JobStatus,
    JobType,
    TrainPayload,
)


def _row_to_record(row: JobRow, queue_position: int | None = None) -> JobRecord:
    return JobRecord(
        job_id=row.id,
        job_type=JobType(row.job_type),
        status=JobStatus(row.status),
        trace_id=row.trace_id,
        job_schema_version=row.job_schema_version,
        payload=row.payload,
        result=row.result,
        error_message=row.error_message,
        owner_user_id=row.owner_user_id,
        queue_position=queue_position,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class JobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_synthesize_job(
        self,
        *,
        owner_user_id: UUID,
        payload: InferPayload,
        trace_id: str | None = None,
    ) -> JobRecord:
        return self._create_job(
            job_type=JobType.SYNTHESIZE,
            owner_user_id=owner_user_id,
            payload=payload.model_dump(mode="json"),
            trace_id=trace_id,
        )

    def create_train_job(
        self,
        *,
        owner_user_id: UUID,
        payload: TrainPayload,
        trace_id: str | None = None,
    ) -> JobRecord:
        return self._create_job(
            job_type=JobType.TRAIN,
            owner_user_id=owner_user_id,
            payload=payload.model_dump(mode="json"),
            trace_id=trace_id,
        )

    def create_batch_job(
        self,
        *,
        owner_user_id: UUID,
        payload: BatchPayload,
        trace_id: str | None = None,
    ) -> JobRecord:
        return self._create_job(
            job_type=JobType.BATCH,
            owner_user_id=owner_user_id,
            payload=payload.model_dump(mode="json"),
            trace_id=trace_id,
        )

    def _create_job(
        self,
        *,
        job_type: JobType,
        owner_user_id: UUID,
        payload: dict,
        trace_id: str | None,
    ) -> JobRecord:
        row = JobRow(
            id=uuid4(),
            job_type=job_type.value,
            status=JobStatus.QUEUED.value,
            trace_id=trace_id or str(uuid4()),
            job_schema_version=JOB_SCHEMA_VERSION,
            payload=payload,
            owner_user_id=owner_user_id,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _row_to_record(row)

    def get_job(self, job_id: UUID) -> JobRecord | None:
        row = self._session.get(JobRow, job_id)
        if not row:
            return None
        queue_position = None
        if row.status == JobStatus.QUEUED.value:
            queue_position = self._queued_position(job_id, JobType(row.job_type))
        return _row_to_record(row, queue_position=queue_position)

    def _queued_position(self, job_id: UUID, job_type: JobType) -> int:
        rows = self._session.scalars(
            select(JobRow.id)
            .where(JobRow.status == JobStatus.QUEUED.value, JobRow.job_type == job_type.value)
            .order_by(JobRow.created_at.asc())
        ).all()
        try:
            return rows.index(job_id) + 1
        except ValueError:
            return 0

    def mark_running(self, job_id: UUID) -> JobRecord | None:
        row = self._session.get(JobRow, job_id)
        if not row:
            return None
        row.status = JobStatus.RUNNING.value
        row.updated_at = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(row)
        return _row_to_record(row)

    def mark_succeeded(self, job_id: UUID, result: dict) -> JobRecord | None:
        row = self._session.get(JobRow, job_id)
        if not row:
            return None
        row.status = JobStatus.SUCCEEDED.value
        row.result = result
        row.error_message = None
        row.updated_at = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(row)
        return _row_to_record(row)

    def mark_failed(self, job_id: UUID, error_message: str) -> JobRecord | None:
        row = self._session.get(JobRow, job_id)
        if not row:
            return None
        row.status = JobStatus.FAILED.value
        row.error_message = error_message
        row.updated_at = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(row)
        return _row_to_record(row)


class VoiceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_voice(self, voice_id: UUID) -> VoiceRow | None:
        return self._session.get(VoiceRow, voice_id)

    def user_owns_voice(self, voice_id: UUID, user_id: UUID) -> bool:
        row = self.get_voice(voice_id)
        return row is not None and row.owner_user_id == user_id

    def get_asset(self, asset_id: UUID) -> VoiceAssetRow | None:
        return self._session.get(VoiceAssetRow, asset_id)

    def get_consent(self, consent_id: UUID) -> ConsentRow | None:
        return self._session.get(ConsentRow, consent_id)

    def default_asset_for_voice(self, voice_id: UUID) -> VoiceAssetRow | None:
        return self._session.scalars(
            select(VoiceAssetRow)
            .where(VoiceAssetRow.voice_id == voice_id, VoiceAssetRow.locked.is_(True))
            .order_by(VoiceAssetRow.created_at.desc())
            .limit(1)
        ).first()

    def default_consent_for_voice(self, voice_id: UUID) -> ConsentRow | None:
        return self._session.scalars(
            select(ConsentRow)
            .where(ConsentRow.voice_id == voice_id, ConsentRow.status == "approved")
            .order_by(ConsentRow.approved_at.desc())
            .limit(1)
        ).first()

    def create_voice(self, *, owner_user_id: UUID, name: str) -> VoiceRow:
        row = VoiceRow(id=uuid4(), owner_user_id=owner_user_id, name=name)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_voices(self, owner_user_id: UUID) -> list[VoiceRow]:
        return list(
            self._session.scalars(
                select(VoiceRow)
                .where(VoiceRow.owner_user_id == owner_user_id)
                .order_by(VoiceRow.created_at.desc())
            ).all()
        )

    def create_consent(
        self,
        *,
        owner_user_id: UUID,
        voice_id: UUID,
        status: str,
        approved_at: datetime | None = None,
    ) -> ConsentRow:
        row = ConsentRow(
            id=uuid4(),
            owner_user_id=owner_user_id,
            voice_id=voice_id,
            status=status,
            approved_at=approved_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def create_asset(
        self,
        *,
        voice_id: UUID,
        owner_user_id: UUID,
        storage_uri: str,
    ) -> VoiceAssetRow:
        row = VoiceAssetRow(
            id=uuid4(),
            voice_id=voice_id,
            owner_user_id=owner_user_id,
            storage_uri=storage_uri,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def update_asset_qc(
        self,
        *,
        asset_id: UUID,
        storage_uri: str,
        qc_passed: bool,
        qc_result: dict,
    ) -> VoiceAssetRow | None:
        row = self.get_asset(asset_id)
        if not row:
            return None
        row.storage_uri = storage_uri
        row.qc_passed = qc_passed
        row.qc_result_json = qc_result
        self._session.commit()
        self._session.refresh(row)
        return row

    def lock_asset(self, asset_id: UUID) -> VoiceAssetRow | None:
        row = self.get_asset(asset_id)
        if not row:
            return None
        row.locked = True
        self._session.commit()
        self._session.refresh(row)
        return row

    def delete_asset(self, asset_id: UUID) -> None:
        row = self.get_asset(asset_id)
        if row:
            self._session.delete(row)
            self._session.commit()


class VoiceVersionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, voice_version_id: UUID) -> VoiceVersionRow | None:
        return self._session.get(VoiceVersionRow, voice_version_id)

    def user_can_access(self, voice_version_id: UUID, user_id: UUID) -> bool:
        row = self.get(voice_version_id)
        return row is not None and row.owner_user_id == user_id

    def next_version_number(self, voice_id: UUID) -> int:
        current = self._session.scalar(
            select(func.max(VoiceVersionRow.version)).where(VoiceVersionRow.voice_id == voice_id)
        )
        return (current or 0) + 1

    def create_version(
        self,
        *,
        voice_id: UUID,
        owner_user_id: UUID,
        model_tag: str,
        checkpoint_uri: str,
        ref_audio_uri: str | None = None,
        ref_text: str | None = None,
        metadata: dict | None = None,
    ) -> VoiceVersionRow:
        version = self.next_version_number(voice_id)
        row = VoiceVersionRow(
            id=uuid4(),
            voice_id=voice_id,
            owner_user_id=owner_user_id,
            version=version,
            model_tag=model_tag,
            checkpoint_uri=checkpoint_uri,
            ref_audio_uri=ref_audio_uri,
            ref_text=ref_text,
            metadata_json=metadata or {},
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_for_user(self, owner_user_id: UUID) -> list[VoiceVersionRow]:
        return list(
            self._session.scalars(
                select(VoiceVersionRow)
                .where(VoiceVersionRow.owner_user_id == owner_user_id)
                .order_by(VoiceVersionRow.created_at.desc())
            ).all()
        )

    def list_for_voice(self, voice_id: UUID, owner_user_id: UUID) -> list[VoiceVersionRow]:
        return list(
            self._session.scalars(
                select(VoiceVersionRow)
                .where(
                    VoiceVersionRow.voice_id == voice_id,
                    VoiceVersionRow.owner_user_id == owner_user_id,
                )
                .order_by(VoiceVersionRow.version.desc())
            ).all()
        )


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, owner_user_id: UUID, name: str) -> ProjectRow:
        row = ProjectRow(id=uuid4(), owner_user_id=owner_user_id, name=name)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def get(self, project_id: UUID) -> ProjectRow | None:
        return self._session.get(ProjectRow, project_id)

    def user_owns(self, project_id: UUID, user_id: UUID) -> bool:
        row = self.get(project_id)
        return row is not None and row.owner_user_id == user_id

    def list_for_user(self, owner_user_id: UUID) -> list[ProjectRow]:
        return list(
            self._session.scalars(
                select(ProjectRow)
                .where(ProjectRow.owner_user_id == owner_user_id)
                .order_by(ProjectRow.created_at.desc())
            ).all()
        )

    def upsert_role(
        self,
        *,
        project_id: UUID,
        role_name: str,
        voice_version_id: UUID,
    ) -> ProjectRoleRow:
        existing = self._session.scalars(
            select(ProjectRoleRow).where(
                ProjectRoleRow.project_id == project_id,
                ProjectRoleRow.role_name == role_name,
            )
        ).first()
        if existing:
            existing.voice_version_id = voice_version_id
            self._session.commit()
            self._session.refresh(existing)
            return existing
        row = ProjectRoleRow(
            id=uuid4(),
            project_id=project_id,
            role_name=role_name,
            voice_version_id=voice_version_id,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_roles(self, project_id: UUID) -> list[ProjectRoleRow]:
        return list(
            self._session.scalars(
                select(ProjectRoleRow)
                .where(ProjectRoleRow.project_id == project_id)
                .order_by(ProjectRoleRow.role_name.asc())
            ).all()
        )
