from __future__ import annotations

from app.auth.principal import Principal
from app.services import receipts as receipts_svc


class DummyQ:
    def __init__(self):
        self.filters = []

    def filter(self, expr):
        self.filters.append(str(expr))
        return self


def test_scope_mine_filters_project():
    q = DummyQ()
    p = Principal(role="project", project_id="123")
    receipts_svc.apply_receipt_scope(q, p, "mine")
    assert q.filters, "expected project filter"


def test_scope_all_requires_admin():
    q = DummyQ()
    p = Principal(role="project", project_id="123")
    try:
        receipts_svc.apply_receipt_scope(q, p, "all")
        assert False, "expected error"
    except Exception:
        pass
