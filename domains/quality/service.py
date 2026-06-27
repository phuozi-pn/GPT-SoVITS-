"""REQ-006 voice quality evaluation and blind AB trials."""

from __future__ import annotations

import random
from pathlib import Path
from uuid import UUID

from voice_platform.audio_util import pitch_shift_wav
from voice_platform.config import get_settings
from domains.voices.preview import resolve_version_source_audio_url
from voice_platform.job.repository import AbVoteRepository, QualityReportRepository, VoiceVersionRepository
from voice_platform.job.schemas import (
    AbTrialResponse,
    AbVoteRequest,
    AbVoteResponse,
    QualityReportResponse,
)
from voice_platform.storage.local import LocalStorage
from voice_platform.storage.urls import resolve_public_url


class QualityServiceError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class QualityService:
    def __init__(self, session) -> None:
        self._session = session
        self._reports = QualityReportRepository(session)
        self._votes = AbVoteRepository(session)
        self._versions = VoiceVersionRepository(session)

    def _mock_score(self, voice_version_id: UUID) -> float:
        seed = int(voice_version_id.hex[:8], 16)
        return round(0.88 + (seed % 12) / 100.0, 4)

    def _mock_synth_url(
        self,
        *,
        owner_user_id: UUID,
        voice_version_id: UUID,
        ver,
    ) -> str | None:
        from voice_platform.quality.engine_synth import load_ref_wav_bytes_for_voice

        ref_bytes = load_ref_wav_bytes_for_voice(ver)
        if not ref_bytes:
            return None
        shifted = pitch_shift_wav(ref_bytes, 1.08)
        storage = LocalStorage()
        out_rel = storage.save_bytes(
            user_id=owner_user_id,
            job_id=voice_version_id,
            data=shifted,
            ext="wav",
            relative_name=f"quality/{voice_version_id}_synth.wav",
        )
        return storage.public_url(out_rel)

    def _eval_sentences(self) -> list[str]:
        from voice_platform.quality.eval_sentences import EVAL_SENTENCES_ZH

        settings = get_settings()
        n = max(1, min(settings.quality_eval_sentence_count, len(EVAL_SENTENCES_ZH)))
        return list(EVAL_SENTENCES_ZH[:n])

    def _embedding_evaluate(
        self,
        *,
        ver,
        voice_version_id: UUID,
    ) -> tuple[float, str | None, str]:
        from voice_platform.quality.engine_synth import (
            load_ref_wav_bytes_for_voice,
            synthesize_eval_wav,
        )
        from voice_platform.quality.speaker_embedding import cosine_similarity

        ref_bytes = load_ref_wav_bytes_for_voice(ver)
        if not ref_bytes:
            raise QualityServiceError(
                "REF_AUDIO_MISSING",
                "Reference audio required for embedding evaluation",
                422,
            )

        sentences = self._eval_sentences()
        scores: list[float] = []
        first_synth: bytes | None = None
        for sent in sentences:
            synth_bytes = synthesize_eval_wav(
                session=self._session,
                voice=ver,
                text=sent,
            )
            if first_synth is None:
                first_synth = synth_bytes
            scores.append(cosine_similarity(ref_bytes, synth_bytes))

        score = round(sum(scores) / len(scores), 4)
        synth_url: str | None = None
        if first_synth:
            storage = LocalStorage()
            out_rel = storage.save_bytes(
                user_id=ver.owner_user_id,
                job_id=voice_version_id,
                data=first_synth,
                ext="wav",
                relative_name=f"quality/{voice_version_id}_synth.wav",
            )
            synth_url = storage.public_url(out_rel)
        eval_sentence = sentences[0] if len(sentences) == 1 else f"{len(sentences)} sentences"
        return score, synth_url, eval_sentence

    def evaluate(self, *, voice_version_id: UUID, owner_user_id: UUID | None = None) -> QualityReportResponse:
        ver = self._versions.get(voice_version_id)
        if not ver:
            raise QualityServiceError("VOICE_NOT_FOUND", "Voice version not found", 404)
        if owner_user_id and ver.owner_user_id != owner_user_id:
            raise QualityServiceError("FORBIDDEN", "Not your voice version", 403)

        settings = get_settings()
        threshold = settings.quality_similarity_threshold
        ref_url = resolve_version_source_audio_url(self._session, ver)
        if settings.quality_mock:
            method = "mock_embedding"
            score = self._mock_score(voice_version_id)
            synth_url = self._mock_synth_url(
                owner_user_id=ver.owner_user_id,
                voice_version_id=voice_version_id,
                ver=ver,
            )
            eval_sentence = settings.quality_eval_sentence
        else:
            method = "mel_speaker_embedding_v1"
            score, synth_url, eval_sentence = self._embedding_evaluate(
                ver=ver,
                voice_version_id=voice_version_id,
            )

        quality_pass = score >= threshold
        row = self._reports.upsert(
            voice_version_id=voice_version_id,
            owner_user_id=ver.owner_user_id,
            similarity_score=score,
            quality_pass=quality_pass,
            threshold=threshold,
            eval_sentence=eval_sentence,
            ref_audio_url=ref_url,
            synth_audio_url=synth_url,
            method=method,
        )
        return self._report_response(row)

    def get_report(self, *, voice_version_id: UUID) -> QualityReportResponse:
        row = self._reports.get(voice_version_id)
        if not row:
            raise QualityServiceError("QUALITY_NOT_FOUND", "Quality report not found — run evaluate first", 404)
        return self._report_response(row)

    def _report_response(self, row) -> QualityReportResponse:
        count, ref_rate = self._votes.stats(row.voice_version_id)
        return QualityReportResponse(
            voice_version_id=row.voice_version_id,
            similarity_score=row.similarity_score,
            quality_pass=row.quality_pass,
            threshold=row.threshold,
            eval_sentence=row.eval_sentence,
            ref_audio_url=row.ref_audio_url,
            synth_audio_url=row.synth_audio_url,
            method=row.method,
            ab_vote_count=count,
            ref_pick_rate=ref_rate,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create_ab_trial(self, *, voice_version_id: UUID) -> AbTrialResponse:
        row = self._reports.get(voice_version_id)
        if not row or not row.ref_audio_url or not row.synth_audio_url:
            raise QualityServiceError(
                "AB_NOT_READY",
                "Quality evaluation with ref/synth audio required before AB trial",
                404,
            )
        if random.random() < 0.5:
            audio_a, audio_b = row.ref_audio_url, row.synth_audio_url
            slot_a_kind, slot_b_kind = "ref", "synth"
        else:
            audio_a, audio_b = row.synth_audio_url, row.ref_audio_url
            slot_a_kind, slot_b_kind = "synth", "ref"
        return AbTrialResponse(
            voice_version_id=voice_version_id,
            audio_a_url=audio_a,
            audio_b_url=audio_b,
            slot_a_kind=slot_a_kind,
            slot_b_kind=slot_b_kind,
        )

    def submit_ab_vote(
        self,
        *,
        voice_version_id: UUID,
        voter_user_id: UUID,
        body: AbVoteRequest,
        slot_a_kind: str,
        slot_b_kind: str,
    ) -> AbVoteResponse:
        if body.slot_a_kind != slot_a_kind or body.slot_b_kind != slot_b_kind:
            raise QualityServiceError("AB_SLOT_MISMATCH", "Trial slot mapping mismatch — refresh AB page", 400)
        picked_kind = slot_a_kind if body.pick_slot == "a" else slot_b_kind
        row = self._votes.create(
            voice_version_id=voice_version_id,
            voter_user_id=voter_user_id,
            pick_slot=body.pick_slot,
            slot_a_kind=slot_a_kind,
            slot_b_kind=slot_b_kind,
            picked_kind=picked_kind,
            score=body.score,
        )
        correct = picked_kind == "ref"
        msg = "你选择了更接近原素材的片段" if correct else "你选择了合成片段"
        return AbVoteResponse(
            vote_id=row.id,
            picked_kind=picked_kind,
            correct=correct,
            message=msg,
        )

    def evaluate_after_train(self, voice_version_id: UUID) -> None:
        import logging

        logger = logging.getLogger(__name__)
        try:
            self.evaluate(voice_version_id=voice_version_id)
        except QualityServiceError as exc:
            logger.warning(
                "auto quality eval skipped voice_version=%s code=%s msg=%s",
                voice_version_id,
                exc.code,
                exc.message,
            )
        except Exception:
            logger.exception(
                "auto quality eval failed voice_version=%s (train job not affected)",
                voice_version_id,
            )
