from __future__ import annotations

from uuid import UUID

from apps.api.deps import get_current_user_id, get_session
from apps.api.exceptions import raise_domain_http
from domains.social.service import SocialService, SocialServiceError
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from voice_platform.social.schemas import (
    AvatarGenerateResponse,
    ConversationPreviewResponse,
    MessageCreateRequest,
    MessageResponse,
    UserDirectoryEntry,
    UserProfileUpdateRequest,
    UserPublicProfileResponse,
)

router = APIRouter()


@router.get("/users/directory", response_model=list[UserDirectoryEntry])
def list_user_directory(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[UserDirectoryEntry]:
    return SocialService(session).list_directory(viewer_user_id=user_id)


@router.get("/users/me/profile", response_model=UserPublicProfileResponse)
def get_my_profile(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> UserPublicProfileResponse:
    return SocialService(session).get_profile(user_id=user_id, viewer_user_id=user_id)


@router.patch("/users/me/profile", response_model=UserPublicProfileResponse)
def update_my_profile(
    body: UserProfileUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> UserPublicProfileResponse:
    return SocialService(session).update_my_profile(user_id=user_id, body=body)


@router.post("/users/me/profile/generate-avatar", response_model=AvatarGenerateResponse)
def generate_my_avatar(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> AvatarGenerateResponse:
    try:
        return SocialService(session).generate_my_avatar(user_id=user_id)
    except SocialServiceError as exc:
        raise_domain_http(exc)


@router.get("/users/{target_user_id}", response_model=UserPublicProfileResponse)
def get_user_profile(
    target_user_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> UserPublicProfileResponse:
    try:
        return SocialService(session).get_profile(user_id=target_user_id, viewer_user_id=user_id)
    except SocialServiceError as exc:
        raise_domain_http(exc)


@router.get("/messages/conversations", response_model=list[ConversationPreviewResponse])
def list_conversations(
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[ConversationPreviewResponse]:
    return SocialService(session).list_conversations(user_id=user_id)


@router.get("/messages/with/{peer_user_id}", response_model=list[MessageResponse])
def list_messages_with_peer(
    peer_user_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> list[MessageResponse]:
    try:
        return SocialService(session).list_thread(user_id=user_id, peer_user_id=peer_user_id)
    except SocialServiceError as exc:
        raise_domain_http(exc)


@router.post("/messages", response_model=MessageResponse, status_code=201)
def send_message(
    body: MessageCreateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
) -> MessageResponse:
    try:
        return SocialService(session).send_message(sender_user_id=user_id, body=body)
    except SocialServiceError as exc:
        raise_domain_http(exc)


@router.get("/catalog/voices/{catalog_id}/demo-download")
def download_catalog_demo(
    catalog_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    try:
        path, filename = SocialService(session).get_demo_download_path(catalog_id=catalog_id, user_id=user_id)
    except SocialServiceError as exc:
        raise_domain_http(exc)
    return FileResponse(path, media_type="audio/wav", filename=filename, headers={"X-AI-Generated": "true"})


@router.get("/catalog/voices/{catalog_id}/voice-pack")
def download_voice_pack(
    catalog_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    try:
        data, filename = SocialService(session).build_voice_pack(catalog_id=catalog_id, user_id=user_id)
    except SocialServiceError as exc:
        raise_domain_http(exc)
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-AI-Generated": "true",
        },
    )
