from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request

from apps.api.config import get_settings
from apps.api.trace import ensure_trace_id, get_current_trace_id
from domains.auth.service import AuthError, AuthService, VIEWER_ANONYMOUS
from voice_platform.config import get_db_session


def get_trace_id(request: Request) -> str:
    return ensure_trace_id(
        get_current_trace_id()
        or request.headers.get("X-Trace-Id")
        or request.headers.get("X-Request-Id")
    )


def _resolve_auth(
    authorization: str | None,
    x_api_key: str | None,
    x_user_id: str | None,
    *,
    required: bool,
) -> UUID:
    """Shared authentication resolver used by both viewer and required-user deps."""
    settings = get_settings()

    if authorization:
        scheme, _, token = authorization.partition(" ")
        if required and (scheme.lower() != "bearer" or not token):
            raise HTTPException(
                status_code=401,
                detail={"code": "AUTH_REQUIRED", "message": "Invalid Authorization header"},
            )
        if scheme.lower() == "bearer" and token:
            try:
                return AuthService.decode_token(token)
            except AuthError as exc:
                if required:
                    raise HTTPException(
                        status_code=401,
                        detail={"code": exc.code, "message": exc.message},
                    ) from exc
                # 公开浏览：过期/无效 token 按未登录访客处理，避免误拦首页试听等接口

    if x_api_key and x_api_key.startswith("vsk_"):
        from domains.developer.service import DeveloperService, DeveloperServiceError

        session = get_db_session()
        try:
            dev = DeveloperService(session)
            user_id, _ = dev.resolve_user_from_key(x_api_key)
            return user_id
        except DeveloperServiceError as exc:
            raise HTTPException(
                status_code=exc.http_status,
                detail={"code": exc.code, "message": exc.message},
            ) from exc
        finally:
            session.close()

    if settings.dev_skip_auth:
        raw = x_user_id or settings.dev_user_id
        try:
            user_id = UUID(raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=401,
                detail={"code": "AUTH_REQUIRED", "message": "Invalid user id"},
            ) from exc
        session = get_db_session()
        try:
            auth = AuthService(session)
            auth.ensure_dev_user(user_id)
            auth.ensure_system_user()
        finally:
            session.close()
        return user_id

    if required:
        raise HTTPException(status_code=401, detail={"code": "AUTH_REQUIRED", "message": "Login required"})

    return VIEWER_ANONYMOUS


def get_viewer_user_id(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> UUID:
    """已登录用户、开发用户，或未登录访客（公开浏览）。"""
    return _resolve_auth(authorization, x_api_key, x_user_id, required=False)


def get_current_user_id(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> UUID:
    return _resolve_auth(authorization, x_api_key, x_user_id, required=True)


def require_admin_user(user_id: UUID = Depends(get_current_user_id)) -> UUID:
    settings = get_settings()
    try:
        admin_id = UUID(settings.dev_admin_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "CONFIG_ERROR", "message": "Invalid dev_admin_user_id"},
        ) from exc
    if user_id != admin_id:
        raise HTTPException(
            status_code=403,
            detail={"code": "ADMIN_REQUIRED", "message": "Operator permission required"},
        )
    return user_id


def get_session():
    """Shared DB session dependency — yields a SQLAlchemy Session and closes it."""
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()
