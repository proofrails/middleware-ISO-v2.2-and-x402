from __future__ import annotations

from fastapi import Request

from app.auth.api_key_auth import resolve_principal


class DummyReceive:  # pragma: no cover
    async def __call__(self):
        return {"type": "http.request"}


def make_request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "query_string": b"",
        "server": ("test", 80),
        "client": ("test", 1234),
        "scheme": "http",
    }
    return Request(scope, DummyReceive())


def test_public_when_no_keys(monkeypatch):
    monkeypatch.delenv("API_KEYS", raising=False)
    # also ensure DB query won't be hit by making SessionLocal explode
    from app import db

    def boom():
        raise RuntimeError("no db")

    monkeypatch.setattr(db, "SessionLocal", boom)

    p = resolve_principal(make_request({}))
    assert p.is_public


def test_env_admin(monkeypatch):
    monkeypatch.setenv("API_KEYS", "abc,def")
    from app import db

    class Sess:
        def close(self):
            pass

    monkeypatch.setattr(db, "SessionLocal", lambda: Sess())

    p = resolve_principal(make_request({"X-API-Key": "def"}))
    assert p.is_admin
