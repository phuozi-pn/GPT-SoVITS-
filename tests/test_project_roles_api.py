from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from domains.projects.service import ProjectServiceError

USER = UUID("11111111-1111-1111-1111-111111111111")
PROJECT = UUID("22222222-2222-2222-2222-222222222222")
ROLE = UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DEV_SKIP_AUTH", "true")
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_unbind_project_role(client):
    with patch("apps.api.routes.projects.ProjectService") as svc_cls:
        svc_cls.return_value.unbind_role.return_value = None
        r = client.delete(f"/api/v1/projects/{PROJECT}/roles/{ROLE}")
    assert r.status_code == 204
    svc_cls.return_value.unbind_role.assert_called_once()
    kwargs = svc_cls.return_value.unbind_role.call_args.kwargs
    assert kwargs["project_id"] == PROJECT
    assert kwargs["role_id"] == ROLE


def test_unbind_project_role_not_found(client):
    with patch("apps.api.routes.projects.ProjectService") as svc_cls:
        svc_cls.return_value.unbind_role.side_effect = ProjectServiceError(
            "ROLE_NOT_FOUND",
            "Role binding not found",
            404,
        )
        r = client.delete(f"/api/v1/projects/{PROJECT}/roles/{ROLE}")
    assert r.status_code == 404
    assert r.json()["code"] == "ROLE_NOT_FOUND"
