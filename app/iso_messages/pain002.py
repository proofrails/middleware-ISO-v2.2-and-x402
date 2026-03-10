from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from lxml import etree

# Minimal Customer Payment Status Report (pain.002.001.10-like structure)
# Note: We are not enforcing XSD here; this is a pragmatic artifact for PoC/prod-lite.
NS = "urn:iso:std:iso:20022:tech:xsd:pain.002.001.10"
NSMAP = {None: NS}


def _iso_dt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def status_code_from_receipt_status(status: str) -> str:
    # Common external codes: ACSC (AcceptedSettlementCompleted), RJCT (Rejected), PDNG (Pending)
    if status == "anchored":
        return "ACSC"
    if status == "failed":
        return "RJCT"
    if status == "awaiting_anchor":
        return "PDNG"
    return "PDNG"


def generate_pain002(receipt: Dict[str, Any]) -> bytes:
    """
    Create a minimal Status Report for the given receipt.
    - GrpHdr.MsgId: receipt['reference']
    - GrpHdr.CreDtTm
    - OrgnlGrpInfAndSts: OrgnlMsgId=reference, OrgnlNbOfTxs=1, GrpSts based on Receipt.status
    - OrgnlPmtInfAndSts (optional): include EndToEndId
    """
    reference = str(receipt.get("reference"))
    rid = str(receipt.get("id"))
    created_at = receipt.get("created_at")
    if not isinstance(created_at, datetime):
        created_at = datetime.utcnow().replace(tzinfo=timezone.utc)

    grp_sts = status_code_from_receipt_status(str(receipt.get("status", "")))

    root = etree.Element("Document", nsmap=NSMAP)
    rpt = etree.SubElement(root, "CstmrPmtStsRpt")

    hdr = etree.SubElement(rpt, "GrpHdr")
    etree.SubElement(hdr, "MsgId").text = reference
    etree.SubElement(hdr, "CreDtTm").text = _iso_dt(created_at)

    ogi = etree.SubElement(rpt, "OrgnlGrpInfAndSts")
    etree.SubElement(ogi, "OrgnlMsgId").text = reference
    etree.SubElement(ogi, "OrgnlNbOfTxs").text = "1"
    etree.SubElement(ogi, "GrpSts").text = grp_sts

    opt = etree.SubElement(rpt, "OrgnlPmtInfAndSts")
    etree.SubElement(opt, "OrgnlPmtInfId").text = rid
    tx_sts = etree.SubElement(opt, "TxInfAndSts")
    pmt_id = etree.SubElement(tx_sts, "OrgnlEndToEndId")
    pmt_id.text = rid

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8", standalone="yes")
