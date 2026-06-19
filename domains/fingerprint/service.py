"""REQ-025 Audio fingerprint enrollment & search domain service."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from voice_platform.fingerprint.encoder import (
    fingerprint_similarity,
    generate_fingerprint,
)
from voice_platform.fingerprint.schemas import (
    FingerprintEnrollResponse,
    FingerprintMatch,
    FingerprintSearchResponse,
    FingerprintStatusResponse,
)


class FingerprintServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class FingerprintService:
    """Audio fingerprint enrollment, search, and status use cases."""

    def __init__(self) -> None:
        # In-memory store — production would use a DB table
        self._store: dict[UUID, dict] = {}

    def enroll(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        voice_id: UUID | None = None,
        storage_url: str | None = None,
    ) -> FingerprintEnrollResponse:
        """Register a fingerprint placeholder (actual hashes filled by worker)."""
        fp_id = uuid4()
        enrolled_at = datetime.now(timezone.utc)
        self._store[fp_id] = {
            "fingerprint_id": fp_id,
            "job_id": job_id,
            "user_id": user_id,
            "voice_id": voice_id,
            "storage_url": storage_url,
            "hashes": set(),
            "hash_count": 0,
            "enrolled_at": enrolled_at,
        }
        return FingerprintEnrollResponse(
            fingerprint_id=fp_id,
            hash_count=0,
            enrolled_at=enrolled_at,
        )

    def enroll_audio(
        self,
        *,
        wav_bytes: bytes,
        job_id: UUID,
        user_id: UUID,
    ) -> FingerprintEnrollResponse:
        """Enroll a fingerprint from uploaded WAV bytes."""
        hashes = generate_fingerprint(wav_bytes)
        fp_id = uuid4()
        enrolled_at = datetime.now(timezone.utc)
        self._store[fp_id] = {
            "fingerprint_id": fp_id,
            "job_id": job_id,
            "user_id": user_id,
            "voice_id": None,
            "storage_url": None,
            "hashes": hashes,
            "hash_count": len(hashes),
            "enrolled_at": enrolled_at,
        }
        return FingerprintEnrollResponse(
            fingerprint_id=fp_id,
            hash_count=len(hashes),
            enrolled_at=enrolled_at,
        )

    def search(
        self,
        *,
        wav_bytes: bytes,
        threshold: float = 0.05,
        max_results: int = 10,
    ) -> FingerprintSearchResponse:
        """Search for matching fingerprints from WAV bytes."""
        t0 = time.perf_counter()
        query_hashes = generate_fingerprint(wav_bytes)

        matches: list[FingerprintMatch] = []
        for fp_id, entry in self._store.items():
            entry_hashes: set[int] = entry.get("hashes", set())
            if not entry_hashes:
                continue
            sim = fingerprint_similarity(query_hashes, entry_hashes)
            if sim >= threshold:
                matches.append(
                    FingerprintMatch(
                        fingerprint_id=fp_id,
                        job_id=entry["job_id"],
                        user_id=entry.get("user_id"),
                        voice_id=entry.get("voice_id"),
                        enrolled_at=entry["enrolled_at"],
                        similarity=round(sim, 4),
                    )
                )

        matches.sort(key=lambda m: m.similarity, reverse=True)
        matches = matches[:max_results]
        elapsed = (time.perf_counter() - t0) * 1000
        return FingerprintSearchResponse(matches=matches, search_duration_ms=round(elapsed, 2))

    def status(self) -> FingerprintStatusResponse:
        """Get fingerprint store status."""
        return FingerprintStatusResponse(total_enrolled=len(self._store))
