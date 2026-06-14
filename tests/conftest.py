from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _skip_db_migrations_in_tests():
    """API unit tests mock services; avoid blocking on PostgreSQL at startup."""
    with patch("apps.api.main._run_migrations"):
        yield
