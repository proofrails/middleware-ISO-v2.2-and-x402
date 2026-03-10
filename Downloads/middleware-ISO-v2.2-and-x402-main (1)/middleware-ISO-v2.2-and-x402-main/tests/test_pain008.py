"""Tests for the pain.008 (CustomerDirectDebitInitiation) integration.

Covers:
  1. generate_pain008 is exported from app.iso_messages
  2. generate_pain008 produces valid XML with the expected structure
  3. The POST /v1/iso/pain008/{rid} endpoint exists and behaves correctly:
     - 401 when unauthenticated (public principal)
     - 404 when receipt does not exist
     - 403 when project_id does not match
     - 200 happy-path returns FIMessageResponse-shaped JSON and writes artifact
"""
from __future__ import annotations

import importlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from lxml import etree


# ---------------------------------------------------------------------------
# 1. Export / import tests
# ---------------------------------------------------------------------------


def test_generate_pain008_exported_from_iso_messages():
    """generate_pain008 must be importable directly from app.iso_messages."""
    from app.iso_messages import generate_pain008  # noqa: F401

    assert callable(generate_pain008)


def test_generate_pain008_importable_from_module():
    """The concrete module must also expose the function."""
    from app.iso_messages.pain008 import generate_pain008  # noqa: F401

    assert callable(generate_pain008)


# ---------------------------------------------------------------------------
# 2. XML generation tests
# ---------------------------------------------------------------------------

_SAMPLE_PAYLOAD = {
    "id": "test-receipt-001",
    "reference": "ref-dd-001",
    "sender_wallet": "0xDebtorWallet1234567890abcdef",
    "receiver_wallet": "0xCreditorWallet1234567890abcdef",
    "currency": "FLR",
    "amount": Decimal("42.50"),
    "created_at": datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
}

NS = "urn:iso:std:iso:20022:tech:xsd:pain.008.001.08"


def _parse(xml_bytes: bytes) -> etree._Element:
    return etree.fromstring(xml_bytes)


def _xpath(root, expr: str):
    return root.xpath(expr, namespaces={"p": NS})


def test_generate_pain008_returns_bytes():
    from app.iso_messages.pain008 import generate_pain008

    result = generate_pain008(_SAMPLE_PAYLOAD)
    assert isinstance(result, bytes)


def test_pain008_xml_is_well_formed():
    from app.iso_messages.pain008 import generate_pain008

    xml = generate_pain008(_SAMPLE_PAYLOAD)
    root = _parse(xml)
    assert root.tag == f"{{{NS}}}Document"


def test_pain008_contains_group_header():
    from app.iso_messages.pain008 import generate_pain008

    root = _parse(generate_pain008(_SAMPLE_PAYLOAD))
    grp = _xpath(root, "//p:GrpHdr")
    assert len(grp) == 1

    msg_id = _xpath(root, "//p:GrpHdr/p:MsgId")
    assert msg_id[0].text == _SAMPLE_PAYLOAD["reference"]


def test_pain008_payment_info_fields():
    from app.iso_messages.pain008 import generate_pain008

    root = _parse(generate_pain008(_SAMPLE_PAYLOAD))

    pmt_inf_id = _xpath(root, "//p:PmtInf/p:PmtInfId")
    assert pmt_inf_id[0].text == _SAMPLE_PAYLOAD["id"]

    pmt_mtd = _xpath(root, "//p:PmtInf/p:PmtMtd")
    assert pmt_mtd[0].text == "DD"


def test_pain008_creditor_and_debtor_wallets():
    from app.iso_messages.pain008 import generate_pain008

    root = _parse(generate_pain008(_SAMPLE_PAYLOAD))

    # Creditor = receiver_wallet
    cdtr_ids = _xpath(root, "//p:PmtInf/p:Cdtr/p:Id/p:PrvtId/p:Othr/p:Id")
    assert cdtr_ids[0].text == _SAMPLE_PAYLOAD["receiver_wallet"]

    # Debtor = sender_wallet (inside DrctDbtTxInf)
    dbtr_ids = _xpath(root, "//p:DrctDbtTxInf/p:Dbtr/p:Id/p:PrvtId/p:Othr/p:Id")
    assert dbtr_ids[0].text == _SAMPLE_PAYLOAD["sender_wallet"]


def test_pain008_instructed_amount():
    from app.iso_messages.pain008 import generate_pain008

    root = _parse(generate_pain008(_SAMPLE_PAYLOAD))
    amt = _xpath(root, "//p:DrctDbtTxInf/p:InstdAmt")
    assert amt[0].text == "42.50"
    assert amt[0].attrib["Ccy"] == "FLR"


# ---------------------------------------------------------------------------
# 3. Endpoint / route tests (using FastAPI TestClient)
# ---------------------------------------------------------------------------


def _make_fake_receipt(rid: str, project_id: str):
    """Build a SimpleNamespace that quacks like a models.Receipt row."""
    return SimpleNamespace(
        id=rid,
        project_id=project_id,
        reference="ref-dd-001",
        sender_wallet="0xDebtorWallet",
        receiver_wallet="0xCreditorWallet",
        currency="FLR",
        amount=Decimal("10.00"),
        created_at=datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        tip_tx_hash="0xabc",
        chain="flare",
    )


@pytest.fixture()
def client():
    """Create a FastAPI TestClient with an in-memory SQLite DB."""
    # Patch settings before any app module touches the real DB
    from app.api.app_factory import create_app

    app = create_app()

    from starlette.testclient import TestClient

    return TestClient(app)


def _override_principal(role="project", project_id="proj-1"):
    from app.auth.principal import Principal

    return Principal(role=role, project_id=project_id)


class TestPain008Endpoint:
    """Integration-style tests for POST /v1/iso/pain008/{rid}."""

    def test_route_registered(self):
        """The pain008 route must be registered on the app."""
        from app.api.app_factory import create_app

        app = create_app()
        paths = [r.path for r in app.routes]
        assert "/v1/iso/pain008/{rid}" in paths

    def test_401_when_public(self, client):
        """Unauthenticated (public) requests must get 401."""
        from app.auth.api_key_auth import resolve_principal

        client.app.dependency_overrides[resolve_principal] = lambda: _override_principal(
            role="public", project_id=None
        )
        try:
            resp = client.post("/v1/iso/pain008/any-id")
            assert resp.status_code == 401
        finally:
            client.app.dependency_overrides.pop(resolve_principal, None)

    def test_404_when_receipt_missing(self, client):
        """Requests for a non-existent receipt must get 404."""
        from app.auth.api_key_auth import resolve_principal

        client.app.dependency_overrides[resolve_principal] = lambda: _override_principal()

        # The real session won't have this receipt
        from app.api.deps import get_session

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        client.app.dependency_overrides[get_session] = lambda: mock_session

        try:
            resp = client.post(f"/v1/iso/pain008/{uuid.uuid4()}")
            assert resp.status_code == 404
        finally:
            client.app.dependency_overrides.pop(resolve_principal, None)
            client.app.dependency_overrides.pop(get_session, None)

    def test_403_when_project_mismatch(self, client):
        """Requests whose project_id doesn't match the receipt must get 403."""
        from app.auth.api_key_auth import resolve_principal
        from app.api.deps import get_session

        rid = str(uuid.uuid4())
        fake_receipt = _make_fake_receipt(rid, project_id="proj-OTHER")

        client.app.dependency_overrides[resolve_principal] = lambda: _override_principal(
            project_id="proj-MINE"
        )

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = fake_receipt
        client.app.dependency_overrides[get_session] = lambda: mock_session

        try:
            resp = client.post(f"/v1/iso/pain008/{rid}")
            assert resp.status_code == 403
        finally:
            client.app.dependency_overrides.pop(resolve_principal, None)
            client.app.dependency_overrides.pop(get_session, None)

    def test_200_happy_path(self, client, tmp_path):
        """Successful generation returns 200 with the expected response shape."""
        from app.auth.api_key_auth import resolve_principal
        from app.api.deps import get_session

        rid = str(uuid.uuid4())
        project_id = "proj-1"
        fake_receipt = _make_fake_receipt(rid, project_id=project_id)

        client.app.dependency_overrides[resolve_principal] = lambda: _override_principal(
            project_id=project_id
        )

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = fake_receipt
        client.app.dependency_overrides[get_session] = lambda: mock_session

        with patch.dict("os.environ", {"ARTIFACTS_DIR": str(tmp_path)}):
            try:
                resp = client.post(f"/v1/iso/pain008/{rid}")
            finally:
                client.app.dependency_overrides.pop(resolve_principal, None)
                client.app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200
        body = resp.json()
        assert body["type"] == "pain.008"
        assert body["receipt_id"] == rid
        assert body["url"] == f"/files/{rid}/pain008.xml"
        assert body["message_id"].startswith("pain008-")

    def test_happy_path_writes_xml_file(self, client, tmp_path):
        """The endpoint must write a pain008.xml file into the artifacts dir."""
        from app.auth.api_key_auth import resolve_principal
        from app.api.deps import get_session

        rid = str(uuid.uuid4())
        project_id = "proj-1"
        fake_receipt = _make_fake_receipt(rid, project_id=project_id)

        client.app.dependency_overrides[resolve_principal] = lambda: _override_principal(
            project_id=project_id
        )

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = fake_receipt
        client.app.dependency_overrides[get_session] = lambda: mock_session

        with patch.dict("os.environ", {"ARTIFACTS_DIR": str(tmp_path)}):
            try:
                resp = client.post(f"/v1/iso/pain008/{rid}")
            finally:
                client.app.dependency_overrides.pop(resolve_principal, None)
                client.app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200

        xml_file = tmp_path / rid / "pain008.xml"
        assert xml_file.exists(), "pain008.xml should have been written to disk"

        # Verify the written file is valid XML
        content = xml_file.read_bytes()
        root = etree.fromstring(content)
        assert root.tag == f"{{{NS}}}Document"

    def test_happy_path_creates_db_record(self, client, tmp_path):
        """The endpoint must call session.add with an ISOArtifact(type='pain008')."""
        from app.auth.api_key_auth import resolve_principal
        from app.api.deps import get_session

        rid = str(uuid.uuid4())
        project_id = "proj-1"
        fake_receipt = _make_fake_receipt(rid, project_id=project_id)

        client.app.dependency_overrides[resolve_principal] = lambda: _override_principal(
            project_id=project_id
        )

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = fake_receipt
        client.app.dependency_overrides[get_session] = lambda: mock_session

        with patch.dict("os.environ", {"ARTIFACTS_DIR": str(tmp_path)}):
            try:
                resp = client.post(f"/v1/iso/pain008/{rid}")
            finally:
                client.app.dependency_overrides.pop(resolve_principal, None)
                client.app.dependency_overrides.pop(get_session, None)

        assert resp.status_code == 200

        # session.add should have been called with an ISOArtifact
        assert mock_session.add.called, "session.add must be called"
        artifact = mock_session.add.call_args[0][0]
        assert artifact.type == "pain008"
        assert artifact.receipt_id == rid
        assert "pain008.xml" in artifact.path

        # session.commit should have been called
        assert mock_session.commit.called, "session.commit must be called"
