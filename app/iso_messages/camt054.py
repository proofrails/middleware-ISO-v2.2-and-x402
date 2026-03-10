from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

from lxml import etree

# Minimal camt.054.001.x Debit/Credit Notification (DCN)
# This is a pragmatic artifact indicating a credit event tied to a receipt.
NS = "urn:iso:std:iso:20022:tech:xsd:camt.054.001.09"
NSMAP = {None: NS}


def _iso_dt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_camt054(receipt: Dict[str, Any]) -> bytes:
    """
    Create a minimal DCN for a credited receipt.
    - BkToCstmrDbtCdtNtfctn/GrpHdr/MsgId = reference
    - Ntfctn/Id = receipt id
    - Ntfctn/Acct/Id/Othr/Id = receiver wallet
    - Ntfctn/Ntry/ Amt = amount @ currency
    - Ntry/CdtDbtInd = CRDT when status anchored else PDNG
    - AddtlNtryInf = reference + optional tx context
    """
    reference = str(receipt.get("reference"))
    rid = str(receipt.get("id"))
    created_at = receipt.get("created_at")
    if not isinstance(created_at, datetime):
        created_at = datetime.utcnow().replace(tzinfo=timezone.utc)

    receiver_wallet = str(receipt.get("receiver_wallet"))
    currency = str(receipt.get("currency"))
    amount = receipt.get("amount")
    if not isinstance(amount, Decimal):
        try:
            from decimal import Decimal as D  # type: ignore

            amount = D(str(amount))
        except Exception:
            amount = None

    cdt = "CRDT" if str(receipt.get("status")) == "anchored" else "PDNG"
    amt_str = str(amount) if amount is not None else "0"

    root = etree.Element("Document", nsmap=NSMAP)
    ntf = etree.SubElement(root, "BkToCstmrDbtCdtNtfctn")

    grp = etree.SubElement(ntf, "GrpHdr")
    etree.SubElement(grp, "MsgId").text = reference
    etree.SubElement(grp, "CreDtTm").text = _iso_dt(created_at)

    noti = etree.SubElement(ntf, "Ntfctn")
    etree.SubElement(noti, "Id").text = rid

    acct = etree.SubElement(noti, "Acct")
    acct_id = etree.SubElement(acct, "Id")
    othr = etree.SubElement(acct_id, "Othr")
    etree.SubElement(othr, "Id").text = receiver_wallet

    entry = etree.SubElement(noti, "Ntry")
    amt = etree.SubElement(entry, "Amt", Ccy=currency)
    amt.text = amt_str
    etree.SubElement(entry, "CdtDbtInd").text = cdt
    etree.SubElement(entry, "AddtlNtryInf").text = reference

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8", standalone="yes")
