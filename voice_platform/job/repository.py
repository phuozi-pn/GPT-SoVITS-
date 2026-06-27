from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from voice_platform.job.models import (
    BatchLineRow,
    ConsentRow,
    JobRow,
    ProjectRoleRow,
    ProjectRow,
    VoiceAssetRow,
    VoiceAuthorizationRow,
    VoiceCatalogEntryRow,
    VoiceComplaintRow,
    VoiceGrantRow,
    PaymentOrderRow,
    VoiceQualityReportRow,
    AbVoteRow,
    VoiceRow,
    VoiceVersionRow,
)
from voice_platform.job.schemas import (
    JOB_SCHEMA_VERSION,
    BatchLineResponse,
    BatchLinesResponse,
    BatchLineStatus,
    BatchPayload,
    InferPayload,
    JobRecord,
    JobStatus,
    JobType,
    TrainPayload,
)
from voice_platform.observability.alerts import maybe_alert_job_failed


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
        record = _row_to_record(row)
        maybe_alert_job_failed(record)
        return record

    def list_recent(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        owner_user_id: UUID | None = None,
        limit: int = 50,
    ) -> list[JobRecord]:
        stmt = select(JobRow).order_by(JobRow.created_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(JobRow.status == status)
        if job_type:
            stmt = stmt.where(JobRow.job_type == job_type)
        if owner_user_id is not None:
            stmt = stmt.where(JobRow.owner_user_id == owner_user_id)
        rows = self._session.scalars(stmt).all()
        return [_row_to_record(row) for row in rows]

    def delete_non_displayable_synthesis_jobs(self, *, owner_user_id: UUID) -> int:
        rows = self._session.scalars(
            select(JobRow).where(
                JobRow.job_type == JobType.SYNTHESIZE.value,
                JobRow.owner_user_id == owner_user_id,
            )
        ).all()
        to_delete = [
            row
            for row in rows
            if row.status != JobStatus.SUCCEEDED.value
            or not (row.result or {}).get("audio_url")
        ]
        for row in to_delete:
            self._session.delete(row)
        if to_delete:
            self._session.commit()
        return len(to_delete)

    def count_by_status(self, status: str) -> int:
        return int(
            self._session.scalar(
                select(func.count()).select_from(JobRow).where(JobRow.status == status)
            )
            or 0
        )

    def count_failed_since(self, *, hours: int = 24) -> int:
        from datetime import timedelta

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(JobRow)
                .where(JobRow.status == JobStatus.FAILED.value, JobRow.updated_at >= since)
            )
            or 0
        )


class BatchLineRepository:
    """批量合成行级状态持久化 — 支持实时进度查询、失败行重试、Worker 崩溃恢复。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_lines(self, *, job_id: UUID, lines: list[dict]) -> list[BatchLineRow]:
        """批量创建行记录（入队时调用）。"""
        rows = [
            BatchLineRow(
                job_id=job_id,
                line_index=line["index"],
                role=line["role"],
                text=line["text"],
                voice_version_id=line["voice_version_id"],
                status=BatchLineStatus.QUEUED.value,
            )
            for line in lines
        ]
        self._session.add_all(rows)
        self._session.commit()
        return rows

    def get_lines(self, job_id: UUID) -> BatchLinesResponse:
        """查询指定 job 的所有行状态。"""
        rows = (
            self._session.query(BatchLineRow)
            .filter(BatchLineRow.job_id == job_id)
            .order_by(BatchLineRow.line_index)
            .all()
        )
        lines = [
            BatchLineResponse(
                line_index=r.line_index,
                role=r.role,
                text=r.text,
                voice_version_id=r.voice_version_id,
                status=BatchLineStatus(r.status),
                audio_url=r.audio_url,
                duration_sec=r.duration_sec,
                export_compliant=r.export_compliant or False,
                label_type=r.label_type,
                labeled_at=r.labeled_at,
                error_code=r.error_code,
                error_message=r.error_message,
            )
            for r in rows
        ]
        return BatchLinesResponse(
            job_id=job_id,
            lines=lines,
            total=len(lines),
            succeeded=sum(1 for l in lines if l.status == BatchLineStatus.SUCCEEDED),
            failed=sum(1 for l in lines if l.status == BatchLineStatus.FAILED),
            queued=sum(1 for l in lines if l.status == BatchLineStatus.QUEUED),
            running=sum(1 for l in lines if l.status == BatchLineStatus.RUNNING),
        )

    def mark_line_running(self, job_id: UUID, line_index: int) -> None:
        """标记某行开始执行。"""
        row = (
            self._session.query(BatchLineRow)
            .filter(BatchLineRow.job_id == job_id, BatchLineRow.line_index == line_index)
            .first()
        )
        if row:
            row.status = BatchLineStatus.RUNNING.value
            row.updated_at = datetime.now(timezone.utc)
            self._session.commit()

    def mark_line_succeeded(
        self,
        job_id: UUID,
        line_index: int,
        *,
        audio_url: str,
        duration_sec: float,
        export_compliant: bool = False,
        label_type: str | None = None,
        labeled_at: datetime | None = None,
    ) -> None:
        """标记某行合成成功。"""
        row = (
            self._session.query(BatchLineRow)
            .filter(BatchLineRow.job_id == job_id, BatchLineRow.line_index == line_index)
            .first()
        )
        if row:
            row.status = BatchLineStatus.SUCCEEDED.value
            row.audio_url = audio_url
            row.duration_sec = duration_sec
            row.export_compliant = export_compliant
            row.label_type = label_type
            row.labeled_at = labeled_at or datetime.now(timezone.utc)
            row.error_code = None
            row.error_message = None
            row.updated_at = datetime.now(timezone.utc)
            self._session.commit()

    def mark_line_failed(
        self,
        job_id: UUID,
        line_index: int,
        *,
        error_code: str,
        error_message: str,
    ) -> None:
        """标记某行合成失败。"""
        row = (
            self._session.query(BatchLineRow)
            .filter(BatchLineRow.job_id == job_id, BatchLineRow.line_index == line_index)
            .first()
        )
        if row:
            row.status = BatchLineStatus.FAILED.value
            row.error_code = error_code
            row.error_message = error_message
            row.updated_at = datetime.now(timezone.utc)
            self._session.commit()

    def reset_lines_for_retry(self, job_id: UUID, line_indices: list[int]) -> int:
        """将指定失败行重置为 queued 状态以支持重试。返回重置行数。"""
        rows = (
            self._session.query(BatchLineRow)
            .filter(
                BatchLineRow.job_id == job_id,
                BatchLineRow.line_index.in_(line_indices),
                BatchLineRow.status == BatchLineStatus.FAILED.value,
            )
            .all()
        )
        for row in rows:
            row.status = BatchLineStatus.QUEUED.value
            row.error_code = None
            row.error_message = None
            row.audio_url = None
            row.duration_sec = None
            row.updated_at = datetime.now(timezone.utc)
        self._session.commit()
        return len(rows)

    def get_queued_lines(self, job_id: UUID) -> list[BatchLineRow]:
        """获取所有待处理的行（用于 Worker 恢复）。"""
        return (
            self._session.query(BatchLineRow)
            .filter(
                BatchLineRow.job_id == job_id,
                BatchLineRow.status == BatchLineStatus.QUEUED.value,
            )
            .order_by(BatchLineRow.line_index)
            .all()
        )

    def has_pending_lines(self, job_id: UUID) -> bool:
        """检查是否还有待处理的行。"""
        return (
            self._session.query(BatchLineRow)
            .filter(
                BatchLineRow.job_id == job_id,
                BatchLineRow.status.in_(
                    [BatchLineStatus.QUEUED.value, BatchLineStatus.RUNNING.value]
                ),
            )
            .first()
            is not None
        )


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

    def update_name(self, *, voice_id: UUID, owner_user_id: UUID, name: str) -> VoiceRow | None:
        row = self.get_voice(voice_id)
        if not row or row.owner_user_id != owner_user_id:
            return None
        row.name = name.strip()
        self._session.commit()
        self._session.refresh(row)
        return row

    def delete_voice_tree(self, voice_id: UUID) -> None:
        from sqlalchemy import delete

        self._session.execute(delete(VoiceAssetRow).where(VoiceAssetRow.voice_id == voice_id))
        self._session.execute(delete(ConsentRow).where(ConsentRow.voice_id == voice_id))
        self._session.execute(delete(VoiceVersionRow).where(VoiceVersionRow.voice_id == voice_id))
        row = self.get_voice(voice_id)
        if row:
            self._session.delete(row)
        self._session.commit()

    def list_assets_for_voice(self, voice_id: UUID, owner_user_id: UUID) -> list[VoiceAssetRow]:
        return list(
            self._session.scalars(
                select(VoiceAssetRow)
                .where(
                    VoiceAssetRow.voice_id == voice_id,
                    VoiceAssetRow.owner_user_id == owner_user_id,
                )
                .order_by(VoiceAssetRow.created_at.desc())
            ).all()
        )

    def list_consents_for_voice(self, voice_id: UUID, owner_user_id: UUID) -> list[ConsentRow]:
        return list(
            self._session.scalars(
                select(ConsentRow)
                .where(
                    ConsentRow.voice_id == voice_id,
                    ConsentRow.owner_user_id == owner_user_id,
                )
                .order_by(ConsentRow.created_at.desc())
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

    def list_pending_consents(self, *, limit: int = 50) -> list[ConsentRow]:
        return list(
            self._session.scalars(
                select(ConsentRow)
                .where(ConsentRow.status == "pending")
                .order_by(ConsentRow.created_at.asc())
                .limit(limit)
            )
        )

    def update_consent_review(
        self,
        *,
        consent_id: UUID,
        status: str,
        reviewed_by: UUID,
        reject_reason: str | None = None,
    ) -> ConsentRow | None:
        row = self.get_consent(consent_id)
        if not row:
            return None
        now = datetime.now(timezone.utc)
        row.status = status
        row.reviewed_by = reviewed_by
        row.reviewed_at = now
        row.reject_reason = reject_reason
        if status == "approved":
            row.approved_at = now
            row.reject_reason = None
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
        from domains.voices.access import user_can_access_voice_version

        return user_can_access_voice_version(self._session, voice_version_id, user_id)

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

    def update_metadata(
        self,
        voice_version_id: UUID,
        *,
        owner_user_id: UUID,
        label: str | None = None,
        ref_text: str | None = None,
    ) -> VoiceVersionRow | None:
        row = self.get(voice_version_id)
        if not row or row.owner_user_id != owner_user_id:
            return None
        meta = dict(row.metadata_json or {})
        if label is not None:
            meta["label"] = label.strip() or None
        row.metadata_json = meta
        if ref_text is not None:
            row.ref_text = ref_text.strip() or None
        self._session.commit()
        self._session.refresh(row)
        return row

    def merge_metadata(self, voice_version_id: UUID, patch: dict) -> None:
        row = self.get(voice_version_id)
        if not row or not patch:
            return
        meta = dict(row.metadata_json or {})
        meta.update(patch)
        row.metadata_json = meta
        self._session.commit()

    def delete_version(self, voice_version_id: UUID) -> bool:
        row = self.get(voice_version_id)
        if not row:
            return False
        self._session.delete(row)
        self._session.commit()
        return True


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

    def delete_role(self, *, project_id: UUID, role_id: UUID) -> bool:
        row = self._session.get(ProjectRoleRow, role_id)
        if not row or row.project_id != project_id:
            return False
        self._session.delete(row)
        self._session.commit()
        return True

    def version_in_use(self, voice_version_id: UUID) -> bool:
        count = self._session.scalar(
            select(func.count())
            .select_from(ProjectRoleRow)
            .where(ProjectRoleRow.voice_version_id == voice_version_id)
        )
        return bool(count and count > 0)


class VoiceCatalogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def publish(
        self,
        *,
        voice_version_id: UUID,
        owner_user_id: UUID,
        title: str,
        description: str,
        tags: list[str],
        featured: bool,
        demo_text: str = "",
        license_type: str = "personal_non_commercial",
        price_cents: int = 0,
        billing_unit: str = "per_1k_chars",
        included_chars: int = 50000,
        prohibited_domains: list[str] | None = None,
        cover_image_url: str | None = None,
    ) -> VoiceCatalogEntryRow:
        prohibited_domains = prohibited_domains or []
        existing = self._session.scalars(
            select(VoiceCatalogEntryRow).where(
                VoiceCatalogEntryRow.voice_version_id == voice_version_id
            )
        ).first()
        if existing:
            existing.title = title
            existing.description = description
            existing.tags_json = tags
            existing.featured = featured
            existing.demo_text = demo_text
            existing.license_type = license_type
            existing.price_cents = price_cents
            existing.billing_unit = billing_unit
            existing.included_chars = included_chars
            existing.prohibited_domains_json = prohibited_domains
            if cover_image_url is not None:
                existing.cover_image_url = cover_image_url or None
            existing.policy_version = (existing.policy_version or 1) + 1
            existing.status = "pending"
            self._session.commit()
            self._session.refresh(existing)
            return existing
        row = VoiceCatalogEntryRow(
            id=uuid4(),
            voice_version_id=voice_version_id,
            owner_user_id=owner_user_id,
            title=title,
            description=description,
            tags_json=tags,
            featured=featured,
            status="pending",
            demo_text=demo_text,
            license_type=license_type,
            price_cents=price_cents,
            billing_unit=billing_unit,
            included_chars=included_chars,
            prohibited_domains_json=prohibited_domains,
            cover_image_url=cover_image_url or None,
            policy_version=1,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def update_license_policy(
        self,
        catalog_id: UUID,
        *,
        owner_user_id: UUID,
        license_type: str,
        price_cents: int,
        billing_unit: str,
        included_chars: int,
        prohibited_domains: list[str],
    ) -> VoiceCatalogEntryRow | None:
        row = self.get(catalog_id)
        if not row or row.owner_user_id != owner_user_id:
            return None
        row.license_type = license_type
        row.price_cents = price_cents
        row.billing_unit = billing_unit
        row.included_chars = included_chars
        row.prohibited_domains_json = prohibited_domains
        row.policy_version = (row.policy_version or 1) + 1
        self._session.commit()
        self._session.refresh(row)
        return row

    def takedown(self, catalog_id: UUID) -> VoiceCatalogEntryRow | None:
        row = self.get(catalog_id)
        if not row:
            return None
        row.status = "takedown"
        self._session.commit()
        self._session.refresh(row)
        return row

    def set_demo_job(self, catalog_id: UUID, demo_job_id: UUID) -> None:
        row = self.get(catalog_id)
        if not row:
            return
        row.demo_job_id = demo_job_id
        self._session.commit()

    def set_demo_audio(self, catalog_id: UUID, *, demo_audio_url: str) -> None:
        row = self.get(catalog_id)
        if not row:
            return
        row.demo_audio_url = demo_audio_url
        self._session.commit()

    def set_cover_image_url(self, catalog_id: UUID, *, cover_image_url: str) -> VoiceCatalogEntryRow | None:
        row = self.get(catalog_id)
        if not row:
            return None
        row.cover_image_url = cover_image_url or None
        self._session.commit()
        self._session.refresh(row)
        return row

    def update_owner_entry(
        self,
        catalog_id: UUID,
        owner_user_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        cover_image_url: str | None = None,
    ) -> VoiceCatalogEntryRow | None:
        row = self.get(catalog_id)
        if not row or row.owner_user_id != owner_user_id:
            return None
        if title is not None:
            row.title = title
        if description is not None:
            row.description = description
        if tags is not None:
            row.tags_json = tags
        if cover_image_url is not None:
            row.cover_image_url = cover_image_url or None
        self._session.commit()
        self._session.refresh(row)
        return row

    def get(self, catalog_id: UUID) -> VoiceCatalogEntryRow | None:
        return self._session.get(VoiceCatalogEntryRow, catalog_id)

    def list_pending(self) -> list[VoiceCatalogEntryRow]:
        return list(
            self._session.scalars(
                select(VoiceCatalogEntryRow)
                .where(VoiceCatalogEntryRow.status == "pending")
                .order_by(VoiceCatalogEntryRow.created_at.asc())
            ).all()
        )

    def list_for_owner(self, owner_user_id: UUID) -> list[VoiceCatalogEntryRow]:
        return list(
            self._session.scalars(
                select(VoiceCatalogEntryRow)
                .where(VoiceCatalogEntryRow.owner_user_id == owner_user_id)
                .order_by(VoiceCatalogEntryRow.created_at.desc())
            ).all()
        )

    def approve(self, catalog_id: UUID) -> VoiceCatalogEntryRow | None:
        row = self.get(catalog_id)
        if not row or row.status != "pending":
            return None
        row.status = "published"
        self._session.commit()
        self._session.refresh(row)
        return row

    def reject(self, catalog_id: UUID, *, reason: str | None = None) -> VoiceCatalogEntryRow | None:
        row = self.get(catalog_id)
        if not row or row.status != "pending":
            return None
        row.status = "rejected"
        row.reject_reason = (reason or "").strip() or None
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_published(
        self,
        *,
        featured_only: bool = False,
        tags: list[str] | None = None,
        owner_user_id: UUID | None = None,
    ) -> list[VoiceCatalogEntryRow]:
        stmt = select(VoiceCatalogEntryRow).where(VoiceCatalogEntryRow.status == "published")
        if owner_user_id is not None:
            stmt = stmt.where(VoiceCatalogEntryRow.owner_user_id == owner_user_id)
        if featured_only:
            stmt = stmt.where(VoiceCatalogEntryRow.featured.is_(True))
        if tags:
            for tag in tags:
                stmt = stmt.where(VoiceCatalogEntryRow.tags_json.contains([tag]))
        return list(self._session.scalars(stmt.order_by(VoiceCatalogEntryRow.created_at.desc())).all())

    def list_distinct_tags(self) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for row in self.list_published():
            for tag in row.tags_json or []:
                text = str(tag).strip()
                if text and text not in seen:
                    seen.add(text)
                    out.append(text)
        return sorted(out)

    def get_by_version(self, voice_version_id: UUID) -> VoiceCatalogEntryRow | None:
        return self._session.scalars(
            select(VoiceCatalogEntryRow).where(
                VoiceCatalogEntryRow.voice_version_id == voice_version_id,
                VoiceCatalogEntryRow.status == "published",
            )
        ).first()

    def find_by_version(self, voice_version_id: UUID) -> VoiceCatalogEntryRow | None:
        return self._session.scalars(
            select(VoiceCatalogEntryRow).where(
                VoiceCatalogEntryRow.voice_version_id == voice_version_id,
            )
        ).first()

    def find_active_by_version(self, voice_version_id: UUID) -> VoiceCatalogEntryRow | None:
        """优先返回已上架条目，与公开音色馆/首页展示一致。"""
        published = self.get_by_version(voice_version_id)
        if published:
            return published
        return self._session.scalars(
            select(VoiceCatalogEntryRow)
            .where(VoiceCatalogEntryRow.voice_version_id == voice_version_id)
            .order_by(VoiceCatalogEntryRow.created_at.desc())
        ).first()

    def is_publicly_listed(self, voice_version_id: UUID) -> bool:
        row = self.get_by_version(voice_version_id)
        return row is not None and row.price_cents == 0


class VoiceGrantRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_grant(
        self,
        *,
        voice_id: UUID,
        granter_user_id: UUID,
        grantee_user_id: UUID,
        expires_at: datetime | None = None,
    ) -> VoiceGrantRow:
        row = VoiceGrantRow(
            id=uuid4(),
            voice_id=voice_id,
            granter_user_id=granter_user_id,
            grantee_user_id=grantee_user_id,
            scope="synthesize",
            expires_at=expires_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def revoke(self, grant_id: UUID, granter_user_id: UUID) -> bool:
        row = self._session.get(VoiceGrantRow, grant_id)
        if not row or row.granter_user_id != granter_user_id:
            return False
        row.revoked_at = datetime.now(timezone.utc)
        self._session.commit()
        return True

    def list_for_granter(self, granter_user_id: UUID) -> list[VoiceGrantRow]:
        return list(
            self._session.scalars(
                select(VoiceGrantRow)
                .where(VoiceGrantRow.granter_user_id == granter_user_id)
                .order_by(VoiceGrantRow.created_at.desc())
            ).all()
        )

    def list_active_for_grantee(self, grantee_user_id: UUID) -> list[VoiceGrantRow]:
        now = datetime.now(timezone.utc)
        rows = list(
            self._session.scalars(
                select(VoiceGrantRow).where(
                    VoiceGrantRow.grantee_user_id == grantee_user_id,
                    VoiceGrantRow.revoked_at.is_(None),
                )
            ).all()
        )
        active: list[VoiceGrantRow] = []
        for row in rows:
            if row.expires_at and row.expires_at < now:
                continue
            active.append(row)
        return active

    def has_active_grant(self, *, voice_id: UUID, grantee_user_id: UUID) -> bool:
        now = datetime.now(timezone.utc)
        rows = list(
            self._session.scalars(
                select(VoiceGrantRow).where(
                    VoiceGrantRow.voice_id == voice_id,
                    VoiceGrantRow.grantee_user_id == grantee_user_id,
                    VoiceGrantRow.revoked_at.is_(None),
                )
            ).all()
        )
        for row in rows:
            if row.expires_at is None or row.expires_at >= now:
                return True
        return False


class VoiceAuthorizationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, authorization_id: UUID) -> VoiceAuthorizationRow | None:
        return self._session.get(VoiceAuthorizationRow, authorization_id)

    def create_purchase(
        self,
        *,
        catalog_id: UUID,
        voice_version_id: UUID,
        voice_id: UUID,
        seller_user_id: UUID,
        buyer_user_id: UUID,
        license_type: str,
        billing_unit: str,
        char_quota_total: int,
        price_paid_cents: int,
        payment_ref: str,
        expires_at: datetime | None = None,
    ) -> VoiceAuthorizationRow:
        for row in self.list_active_for_buyer_catalog(buyer_user_id, catalog_id):
            row.status = "revoked"
            row.revoked_at = datetime.now(timezone.utc)
        row = VoiceAuthorizationRow(
            id=uuid4(),
            catalog_id=catalog_id,
            voice_version_id=voice_version_id,
            voice_id=voice_id,
            seller_user_id=seller_user_id,
            buyer_user_id=buyer_user_id,
            license_type=license_type,
            billing_unit=billing_unit,
            char_quota_total=char_quota_total,
            char_quota_used=0,
            price_paid_cents=price_paid_cents,
            payment_ref=payment_ref,
            status="active",
            expires_at=expires_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_active_for_buyer_catalog(
        self, buyer_user_id: UUID, catalog_id: UUID
    ) -> list[VoiceAuthorizationRow]:
        now = datetime.now(timezone.utc)
        rows = list(
            self._session.scalars(
                select(VoiceAuthorizationRow).where(
                    VoiceAuthorizationRow.buyer_user_id == buyer_user_id,
                    VoiceAuthorizationRow.catalog_id == catalog_id,
                    VoiceAuthorizationRow.status == "active",
                )
            ).all()
        )
        out: list[VoiceAuthorizationRow] = []
        for row in rows:
            if row.expires_at and row.expires_at < now:
                row.status = "expired"
                continue
            if row.char_quota_total > 0 and row.char_quota_used >= row.char_quota_total:
                row.status = "expired"
                continue
            out.append(row)
        self._session.commit()
        return out

    def has_active_for_voice(self, *, buyer_user_id: UUID, voice_version_id: UUID) -> bool:
        now = datetime.now(timezone.utc)
        rows = list(
            self._session.scalars(
                select(VoiceAuthorizationRow).where(
                    VoiceAuthorizationRow.buyer_user_id == buyer_user_id,
                    VoiceAuthorizationRow.voice_version_id == voice_version_id,
                    VoiceAuthorizationRow.status == "active",
                )
            ).all()
        )
        for row in rows:
            if row.revoked_at:
                continue
            if row.expires_at and row.expires_at < now:
                continue
            if row.char_quota_total > 0 and row.char_quota_used >= row.char_quota_total:
                continue
            return True
        return False

    def get_active_for_voice(
        self, *, buyer_user_id: UUID, voice_version_id: UUID
    ) -> VoiceAuthorizationRow | None:
        now = datetime.now(timezone.utc)
        rows = list(
            self._session.scalars(
                select(VoiceAuthorizationRow)
                .where(
                    VoiceAuthorizationRow.buyer_user_id == buyer_user_id,
                    VoiceAuthorizationRow.voice_version_id == voice_version_id,
                    VoiceAuthorizationRow.status == "active",
                )
                .order_by(VoiceAuthorizationRow.created_at.desc())
            ).all()
        )
        for row in rows:
            if row.revoked_at:
                continue
            if row.expires_at and row.expires_at < now:
                continue
            if row.char_quota_total > 0 and row.char_quota_used >= row.char_quota_total:
                continue
            return row
        return None

    def record_chars(self, authorization_id: UUID, char_count: int) -> None:
        row = self.get(authorization_id)
        if not row or row.status != "active":
            return
        row.char_quota_used += char_count
        if row.char_quota_total > 0 and row.char_quota_used >= row.char_quota_total:
            row.status = "expired"
        self._session.commit()

    def list_active_for_catalog(self, catalog_id: UUID) -> list[VoiceAuthorizationRow]:
        return list(
            self._session.scalars(
                select(VoiceAuthorizationRow).where(
                    VoiceAuthorizationRow.catalog_id == catalog_id,
                    VoiceAuthorizationRow.status == "active",
                )
            ).all()
        )

    def revoke_for_catalog(self, catalog_id: UUID) -> int:
        rows = list(
            self._session.scalars(
                select(VoiceAuthorizationRow).where(
                    VoiceAuthorizationRow.catalog_id == catalog_id,
                    VoiceAuthorizationRow.status == "active",
                )
            ).all()
        )
        now = datetime.now(timezone.utc)
        for row in rows:
            row.status = "revoked"
            row.revoked_at = now
        self._session.commit()
        return len(rows)

    def list_for_buyer(self, buyer_user_id: UUID) -> list[VoiceAuthorizationRow]:
        return list(
            self._session.scalars(
                select(VoiceAuthorizationRow)
                .where(VoiceAuthorizationRow.buyer_user_id == buyer_user_id)
                .order_by(VoiceAuthorizationRow.created_at.desc())
            ).all()
        )

    def list_for_seller(self, seller_user_id: UUID) -> list[VoiceAuthorizationRow]:
        return list(
            self._session.scalars(
                select(VoiceAuthorizationRow)
                .where(VoiceAuthorizationRow.seller_user_id == seller_user_id)
                .order_by(VoiceAuthorizationRow.created_at.desc())
            ).all()
        )


class VoiceComplaintRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        reporter_user_id: UUID,
        description: str,
        target_url: str = "",
        catalog_id: UUID | None = None,
        voice_version_id: UUID | None = None,
        evidence: list[str] | None = None,
    ) -> VoiceComplaintRow:
        row = VoiceComplaintRow(
            id=uuid4(),
            reporter_user_id=reporter_user_id,
            description=description.strip(),
            target_url=target_url.strip(),
            catalog_id=catalog_id,
            voice_version_id=voice_version_id,
            evidence_json=evidence or [],
            status="open",
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def get(self, complaint_id: UUID) -> VoiceComplaintRow | None:
        return self._session.get(VoiceComplaintRow, complaint_id)

    def list_open(self) -> list[VoiceComplaintRow]:
        return list(
            self._session.scalars(
                select(VoiceComplaintRow)
                .where(VoiceComplaintRow.status == "open")
                .order_by(VoiceComplaintRow.created_at.asc())
            ).all()
        )

    def resolve(
        self,
        complaint_id: UUID,
        *,
        resolved_by: UUID,
        status: str,
        resolution_note: str,
    ) -> VoiceComplaintRow | None:
        row = self.get(complaint_id)
        if not row or row.status != "open":
            return None
        row.status = status
        row.resolution_note = resolution_note
        row.resolved_by = resolved_by
        row.resolved_at = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(row)
        return row


class QualityReportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, voice_version_id: UUID) -> VoiceQualityReportRow | None:
        return self._session.scalars(
            select(VoiceQualityReportRow).where(
                VoiceQualityReportRow.voice_version_id == voice_version_id
            )
        ).first()

    def upsert(
        self,
        *,
        voice_version_id: UUID,
        owner_user_id: UUID,
        similarity_score: float,
        quality_pass: bool,
        threshold: float,
        eval_sentence: str,
        ref_audio_url: str | None,
        synth_audio_url: str | None,
        method: str,
    ) -> VoiceQualityReportRow:
        row = self.get(voice_version_id)
        if row:
            row.similarity_score = similarity_score
            row.quality_pass = quality_pass
            row.threshold = threshold
            row.eval_sentence = eval_sentence
            row.ref_audio_url = ref_audio_url
            row.synth_audio_url = synth_audio_url
            row.method = method
        else:
            row = VoiceQualityReportRow(
                id=uuid4(),
                voice_version_id=voice_version_id,
                owner_user_id=owner_user_id,
                similarity_score=similarity_score,
                quality_pass=quality_pass,
                threshold=threshold,
                eval_sentence=eval_sentence,
                ref_audio_url=ref_audio_url,
                synth_audio_url=synth_audio_url,
                method=method,
            )
            self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row


class AbVoteRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        voice_version_id: UUID,
        voter_user_id: UUID,
        pick_slot: str,
        slot_a_kind: str,
        slot_b_kind: str,
        picked_kind: str,
        score: int | None,
    ) -> AbVoteRow:
        row = AbVoteRow(
            id=uuid4(),
            voice_version_id=voice_version_id,
            voter_user_id=voter_user_id,
            pick_slot=pick_slot,
            slot_a_kind=slot_a_kind,
            slot_b_kind=slot_b_kind,
            picked_kind=picked_kind,
            score=score,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def stats(self, voice_version_id: UUID) -> tuple[int, float | None]:
        rows = list(
            self._session.scalars(
                select(AbVoteRow).where(AbVoteRow.voice_version_id == voice_version_id)
            ).all()
        )
        if not rows:
            return 0, None
        ref_picks = sum(1 for r in rows if r.picked_kind == "ref")
        return len(rows), ref_picks / len(rows)


class PaymentOrderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        authorization_id: UUID | None,
        catalog_id: UUID,
        buyer_user_id: UUID,
        seller_user_id: UUID,
        amount_cents: int,
        provider: str,
        provider_ref: str,
        currency: str = "CNY",
        status: str = "paid",
        paid_at: datetime | None = None,
    ) -> PaymentOrderRow:
        row = PaymentOrderRow(
            id=uuid4(),
            authorization_id=authorization_id,
            catalog_id=catalog_id,
            buyer_user_id=buyer_user_id,
            seller_user_id=seller_user_id,
            amount_cents=amount_cents,
            currency=currency,
            status=status,
            provider=provider,
            provider_ref=provider_ref,
            paid_at=paid_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def get(self, order_id: UUID) -> PaymentOrderRow | None:
        return self._session.get(PaymentOrderRow, order_id)

    def get_by_provider_ref(self, provider: str, provider_ref: str) -> PaymentOrderRow | None:
        stmt = select(PaymentOrderRow).where(
            PaymentOrderRow.provider == provider,
            PaymentOrderRow.provider_ref == provider_ref,
        )
        return self._session.scalars(stmt).first()

    def mark_paid(self, order_id: UUID, *, authorization_id: UUID) -> PaymentOrderRow | None:
        row = self.get(order_id)
        if not row:
            return None
        row.status = "paid"
        row.authorization_id = authorization_id
        row.paid_at = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_recent(self, *, limit: int = 50) -> list[PaymentOrderRow]:
        from sqlalchemy import desc

        stmt = select(PaymentOrderRow).order_by(desc(PaymentOrderRow.created_at)).limit(limit)
        return list(self._session.scalars(stmt).all())
