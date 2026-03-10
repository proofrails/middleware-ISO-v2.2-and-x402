from __future__ import annotations

import types

from app import models
from app.jobs import _project_execution_mode


class DummySession:
    def __init__(self, project):
        self._project = project

    def get(self, model, pk):
        if model is models.Project:
            return self._project
        return None


def test_project_execution_mode_defaults_platform():
    rec = types.SimpleNamespace(project_id=None)
    assert _project_execution_mode(DummySession(None), rec) == "platform"


def test_project_execution_mode_tenant():
    proj = types.SimpleNamespace(config={"anchoring": {"execution_mode": "tenant"}})
    rec = types.SimpleNamespace(project_id="p1")
    assert _project_execution_mode(DummySession(proj), rec) == "tenant"
