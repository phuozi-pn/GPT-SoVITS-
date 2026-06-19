from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from voice_platform.job.repository import (
    VoiceAuthorizationRepository,
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
    if grants.has_active_grant(voice_id=row.voice_id, grantee_user_id=user_id):
        return True
    auths = VoiceAuthorizationRepository(session)
    return auths.has_active_for_voice(buyer_user_id=user_id, voice_version_id=voice_version_id)


def list_accessible_version_ids(session, user_id: UUID) -> set[UUID]:
    versions = VoiceVersionRepository(session)
    catalog = VoiceCatalogRepository(session)
    grants = VoiceGrantRepository(session)
    voices = VoiceRepository(session)

    ids: set[UUID] = {v.id for v in versions.list_for_user(user_id)}
    for entry in catalog.list_published():
        if entry.price_cents == 0:
            ids.add(entry.voice_version_id)
    for grant in grants.list_active_for_grantee(user_id):
        voice = voices.get_voice(grant.voice_id)
        if not voice:
            continue
        for ver in versions.list_for_voice(grant.voice_id, voice.owner_user_id):
            ids.add(ver.id)
    auths = VoiceAuthorizationRepository(session)
    for auth in auths.list_for_buyer(user_id):
        if auth.status == "active":
            ids.add(auth.voice_version_id)
    return ids
