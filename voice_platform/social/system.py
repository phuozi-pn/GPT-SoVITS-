from __future__ import annotations

from uuid import UUID

from voice_platform.auth.repository import UserRepository
from voice_platform.social.repository import UserMessageRepository

SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


def ensure_system_user(session) -> None:
    UserRepository(session).ensure_system_user(SYSTEM_USER_ID)


def send_system_notice(
    session,
    *,
    recipient_user_id: UUID,
    conversation_peer_user_id: UUID,
    body: str,
) -> None:
    ensure_system_user(session)
    UserMessageRepository(session).create(
        sender_user_id=SYSTEM_USER_ID,
        recipient_user_id=recipient_user_id,
        body=body,
        conversation_peer_user_id=conversation_peer_user_id,
    )

