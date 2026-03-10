from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from lxml import etree

# Minimal camt.053.001.x BankToCustomerStatement (daily statement)
NS = "urn:iso:std:iso:20022:tech:xsd:camt.053.001.08"
NSMAP = {None: NS}


def _iso_dt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_camt053(date_str: str, entries: List[Dict[str, Any]]) -> bytes:
    """
    Build a minimal daily statement for receipts matching date_str (YYYY-MM-DD).
    Each entry in 'entries' is a dict with fields:
      - id, reference, amount, currency, sender_wallet, receiver_wallet, status, created_at
    """
    # Root document
    root = etree.Element("Document", nsmap=NSMAP)
    stmt = etree.SubElement(root, "BkToCstmrStmt")

    # Group header
    grp = etree.SubElement(stmt, "GrpHdr")
    etree.SubElement(grp, "MsgId").text = f"camt053-{date_str}"
    etree.SubElement(grp, "CreDtTm").text = _iso_dt(datetime.utcnow())

    # Statement
    st = etree.SubElement(stmt, "Stmt")
    etree.SubElement(st, "Id").text = f"STMT-{date_str}"
    etree.SubElement(st, "ElctrncSeqNb").text = "1"
    etree.SubElement(st, "LglSeqNb").text = "1"
    # Statement date
    dt_el = etree.SubElement(st, "CreDtTm")
    dt_el.text = _iso_dt(datetime.utcnow())

    # Account (placeholder based on date)
    acct = etree.SubElement(st, "Acct")
    acct_id = etree.SubElement(acct, "Id")
    othr = etree.SubElement(acct_id, "Othr")
    etree.SubElement(othr, "Id").text = f"ACCT-{date_str.replace('-', '')}"
    etree.SubElement(acct, "Ccy").text = "FLR"

    # For each receipt, produce a Ntry element
    for e in entries:
        ntry = etree.SubElement(st, "Ntry")
        # Amount
        amt = etree.SubElement(ntry, "Amt")
        ccy = str(e.get("currency") or "FLR")
        amt.attrib["Ccy"] = ccy
        amt.text = str(e.get("amount") or "0")
        # Entry status
        etree.SubElement(ntry, "CdtDbtInd").text = "CRDT"
        etree.SubElement(ntry, "Sts").text = "BOOK"

        # Booking/date fields
        bdt = etree.SubElement(ntry, "BookgDt")
        dt_tm = etree.SubElement(bdt, "DtTm")
        created_at = e.get("created_at")
        if isinstance(created_at, datetime):
            dt_tm.text = _iso_dt(created_at)
        else:
            dt_tm.text = _iso_dt(datetime.utcnow())

        # Entry details (single Tx)
        ntry_dtls = etree.SubElement(ntry, "NtryDtls")
        tx_dtls = etree.SubElement(ntry_dtls, "TxDtls")
        refs = etree.SubElement(tx_dtls, "Refs")
        etree.SubElement(refs, "EndToEndId").text = str(e.get("reference") or e.get("id"))
        # Remittance info (free text compact)
        rmt = etree.SubElement(tx_dtls, "RmtInf")
        etree.SubElement(
            rmt, "Ustrd"
        ).text = f"RID={e.get('id')} FROM={str(e.get('sender_wallet'))[:10]} TO={str(e.get('receiver_wallet'))[:10]} STATUS={e.get('status')}"

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8", standalone="yes")
