"""API-layer config facade — thin wrapper over voice_platform.config settings.

Routes should import from here instead of reaching directly into voice_platform.config.
This allows us to swap out the underlying config source without touching every route.
"""

from __future__ import annotations

from voice_platform.config import get_settings

__all__ = ["get_settings"]
