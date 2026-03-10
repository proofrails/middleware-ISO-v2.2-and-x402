from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from lxml import etree

# Minimal camt.052.001.x BankToCustomerAccountReport (intraday)
NS = "urn:iso:std:iso:20022:tech:xsd:camt.052.001.08"
NSMAP = {None: NS}


def _iso_dt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_camt052(date_str: str, window: str, entries: List[Dict[str, Any]]) -> bytes:
    """
    Build a minimal intraday account report for receipts matching date/window.
    window format: 'HH:MM-HH:MM' (UTC)
    Each entry in 'entries' is a dict with fields:
      - id, reference, amount, currency, sender_wallet, receiver_wallet, status, created_at
    """
    # Root document
    root = etree.Element("Document", nsmap=NSMAP)
    rpt = etree.SubElement(root, "BkToCstmrAcctRpt")

    # Group header
    grp = etree.SubElement(rpt, "GrpHdr")
    etree.SubElement(grp, "MsgId").text = f"camt052-{date_str}-{window.replace(':', '').replace('-', '')}"
    etree.SubElement(grp, "CreDtTm").text = _iso_dt(datetime.utcnow())

    # Report
    rp = etree.SubElement(rpt, "Rpt")
    etree.SubElement(rp, "Id").text = f"RPT-{date_str}-{window}"
    # Report dateTime
    etree.SubElement(rp, "CreDtTm").text = _iso_dt(datetime.utcnow())

    # Account (placeholder based on date)
    acct = etree.SubElement(rp, "Acct")
    acct_id = etree.SubElement(acct, "Id")
    othr = etree.SubElement(acct_id, "Othr")
    etree.SubElement(othr, "Id").text = f"ACCT-{date_str.replace('-', '')}"
    etree.SubElement(acct, "Ccy").text = "FLR"

    # For each receipt, produce an Ntry
    for e in entries:
        ntry = etree.SubElement(rp, "Ntry")
        # Amount
        amt = etree.SubElement(ntry, "Amt")
        ccy = str(e.get("currency") or "FLR")
        amt.attrib["Ccy"] = ccy
        amt.text = str(e.get("amount") or "0")
        # Credit/Debit and status
        etree.SubElement(ntry, "CdtDbtInd").text = "CRDT"
        etree.SubElement(ntry, "Sts").text = "BOOK"

        # Date/time
        bdt = etree.SubElement(ntry, "BookgDt")
        dt_tm = etree.SubElement(bdt, "DtTm")
        created_at = e.get("created_at")
        dt_tm.text = _iso_dt(created_at) if isinstance(created_at, datetime) else _iso_dt(datetime.utcnow())

        # Details
        ntry_dtls = etree.SubElement(ntry, "NtryDtls")
        tx_dtls = etree.SubElement(ntry_dtls, "TxDtls")
        refs = etree.SubElement(tx_dtls, "Refs")
        etree.SubElement(refs, "EndToEndId").text = str(e.get("reference") or e.get("id"))
        rmt = etree.SubElement(tx_dtls, "RmtInf")
        etree.SubElement(
            rmt, "Ustrd"
        ).text = f"RID={e.get('id')} FROM={str(e.get('sender_wallet'))[:10]} TO={str(e.get('receiver_wallet'))[:10]} STATUS={e.get('status')}"

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8", standalone="yes")
