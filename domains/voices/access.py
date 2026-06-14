from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from voice_platform.job.repository import (
    VoiceCatalogRepository,
    VoiceGrantRepository,
    VoiceRepository,
    VoiceVersionRepository,
)


def user_can_access_voice_version(session, voice_version_id: UUID, user_id: UUID) -> bool:
    versions = VoiceVersionRepository(session)
    row = versions.get(voice_version_id)
    if not row:
        return False
    if row.owner_user_id == user_id:
        return True
    catalog = VoiceCatalogRepository(session)
    if catalog.is_publicly_listed(voice_version_id):
        return True
    grants = VoiceGrantRepository(session)
    return grants.has_active_grant(voice_id=row.voice_id, grantee_user_id=user_id)


def list_accessible_version_ids(session, user_id: UUID) -> set[UUID]:
    versions = VoiceVersionRepository(session)
    catalog = VoiceCatalogRepository(session)
    grants = VoiceGrantRepository(session)
    voices = VoiceRepository(session)

    ids: set[UUID] = {v.id for v in versions.list_for_user(user_id)}
    for entry in catalog.list_published():
        ids.add(entry.voice_version_id)
    for grant in grants.list_active_for_grantee(user_id):
        voice = voices.get_voice(grant.voice_id)
        if not voice:
            continue
        for ver in versions.list_for_voice(grant.voice_id, voice.owner_user_id):
            ids.add(ver.id)
    return ids
