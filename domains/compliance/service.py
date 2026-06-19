"""Compliance service – unified entry for compliance validation, labeling, and export operations.

Re-exports the gateway for backward compatibility while providing
a service facade for export-related operations.
"""

from __future__ import annotations

from domains.compliance.gateway import ComplianceError, ComplianceGateway  # noqa: F401
from domains.compliance.export import (
    apply_compliance_label,
    build_manifest,
    manifest_json,
    rhythm_label_wav,
    COMPLIANCE_README,
)


class ComplianceService:
    """Unified compliance operations: validation, labeling, manifest generation.

    This service delegates text/content validation to ComplianceGateway
    and provides a single entry for export/label operations.
    """

    def __init__(self, *, wordlist_path: str | None = None) -> None:
        self._gateway = ComplianceGateway(wordlist_path=wordlist_path)

    @property
    def gateway(self) -> ComplianceGateway:
        return self._gateway

    # ---- Delegated validation ----

    def validate_text(self, text: str, *, max_len: int = 5000) -> str:
        """Validate and clean text for compliance."""
        return self._gateway._validate_text(text, max_len=max_len)

    def validate_batch_line(self, text: str) -> str:
        """Validate a single batch line text."""
        return self._gateway.validate_batch_line_text(text)

    # ---- Export / labeling ----

    @staticmethod
    def apply_label(
        wav_bytes: bytes,
        *,
        sample_rate: int = 32000,
        label_type: str = "rhythm",
        watermark=None,
    ) -> tuple[bytes, dict]:
        """Apply compliance label to audio bytes."""
        return apply_compliance_label(
            wav_bytes,
            sample_rate=sample_rate,
            label_type=label_type,
            watermark=watermark,
        )

    @staticmethod
    def build_manifest(
        *,
        job_id: str,
        items: list[dict],
        failures: list[dict],
    ) -> dict:
        """Build a compliance manifest dict."""
        return build_manifest(
            job_id=job_id,
            items=items,
            failures=failures,
        )

    @staticmethod
    def manifest_json_bytes(manifest: dict) -> bytes:
        """Serialize a manifest dict to JSON bytes."""
        return manifest_json(manifest)

    @staticmethod
    def readme() -> str:
        """Compliance README text."""
        return COMPLIANCE_README
