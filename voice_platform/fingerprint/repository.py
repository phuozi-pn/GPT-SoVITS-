from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from voice_platform.fingerprint.models import AudioFingerprintRow


class FingerprintRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert(
        self,
        *,
        job_id: UUID,
        user_id: UUID,
        voice_id: UUID | None,
        storage_url: str | None,
        digest: str,
        hashes: set[int],
    ) -> AudioFingerprintRow:
        row = AudioFingerprintRow(
            id=uuid4(),
            job_id=job_id,
            user_id=user_id,
            voice_id=voice_id,
            storage_url=storage_url,
            digest=digest,
            hashes_json=sorted(hashes),
            hash_count=len(hashes),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_all(self, *, limit: int = 5000) -> list[AudioFingerprintRow]:
        stmt = select(AudioFingerprintRow).order_by(desc(AudioFingerprintRow.enrolled_at)).limit(limit)
        return list(self._session.scalars(stmt).all())

    def count(self) -> int:
        return self._session.scalar(select(func.count()).select_from(AudioFingerprintRow)) or 0
