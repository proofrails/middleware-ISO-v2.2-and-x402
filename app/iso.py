from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

from lxml import etree

try:
    import xmlschema  # type: ignore
except Exception:  # pragma: no cover
    xmlschema = None  # type: ignore


# Namespace for pain.001.001.09
NS_PAIN001 = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.09"
NSMAP = {None: NS_PAIN001}

# XSD path (must be vendored into the repo under schemas/)
SCHEMA_PATH = Path("schemas/pain.001.001.09.xsd")

_schema: Optional["xmlschema.XMLSchema"] = None  # type: ignore


def _get_schema() -> Optional["xmlschema.XMLSchema"]:  # type: ignore
    global _schema
    if _schema is not None:
        return _schema
    if xmlschema is None:
        return None
    if SCHEMA_PATH.exists():
        try:
            _schema = xmlschema.XMLSchema(str(SCHEMA_PATH))
            return _schema
        except Exception:
            return None
    return None


def _iso_dt(dt: datetime) -> str:
    # Ensure UTC Z-format
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    # Use ISO 8601 with Z
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z").replace("+0000", "Z")


def _iso_date(dt: datetime) -> str:
    return dt.date().isoformat()


def _elm(parent, tag: str, text: Optional[str] = None, attrib: Optional[Dict[str, str]] = None):
    if attrib is None:
        elem = etree.SubElement(parent, tag)
    else:
        elem = etree.SubElement(parent, tag, attrib=attrib)
    if text is not None:
        elem.text = text
    return elem


def _wallet_party(parent, role_nm: Optional[str], wallet_addr: str, scheme: str = "WALLET"):
    """Constructs PartyIdentification: Nm (optional) + Id/PrvtId/Othr/{Id,SchmeNm/Prtry}"""
    if role_nm:
        _elm(parent, "Nm", role_nm)
    id_ = _elm(parent, "Id")
    prvt = _elm(id_, "PrvtId")
    othr = _elm(prvt, "Othr")
    _elm(othr, "Id", wallet_addr)
    schme = _elm(othr, "SchmeNm")
    _elm(schme, "Prtry", scheme)


def _wallet_acct(parent, wallet_addr: str, scheme: str = "WALLET_ACCOUNT"):
    """Constructs CashAccount: Id/Othr/{Id,SchmeNm/Prtry}"""
    id_ = _elm(parent, "Id")
    othr = _elm(id_, "Othr")
    _elm(othr, "Id", wallet_addr)
    schme = _elm(othr, "SchmeNm")
    _elm(schme, "Prtry", scheme)


def _agent_not_provided(parent):
    """Constructs FinancialInstitutionIdentification with Othr/Id=NOTPROVIDED"""
    agt = _elm(parent, "FinInstnId")
    othr = _elm(agt, "Othr")
    _elm(othr, "Id", "NOTPROVIDED")


def generate_pain001(receipt: Dict[str, Any]) -> bytes:
    """
    Build a minimal schema-valid pain.001.001.09 for a single credit transfer.
    Mapping decisions per spec:
    - GrpHdr.MsgId = receipt['reference']
    - GrpHdr.CreDtTm = receipt['created_at']
    - GrpHdr.NbOfTxs = '1'
    - GrpHdr.InitgPty.Nm = 'Capella' (or generic)
    - PmtInf:
      - PmtInfId = receipt['id']
      - PmtMtd = TRF
      - ReqdExctnDt = date(created_at)
      - Dbtr (+ WALLET id mapping)
      - DbtrAcct (Othr/Id = sender wallet)
      - DbtrAgt = NOTPROVIDED
      - ChrgBr = SLEV
    - CdtTrfTxInf:
      - PmtId.EndToEndId = receipt['id']
      - Amt.InstdAmt @Ccy = receipt['currency'] (FLR for PoC)
      - CdtrAgt = NOTPROVIDED
      - Cdtr (+ WALLET id mapping)
      - CdtrAcct (Othr/Id = receiver wallet)
      - RmtInf.Ustrd = receipt['reference']
    """
    created_at: datetime = receipt["created_at"]
    reference: str = receipt["reference"]
    rid: str = receipt["id"]
    sender_wallet: str = receipt["sender_wallet"]
    receiver_wallet: str = receipt["receiver_wallet"]
    currency: str = str(receipt["currency"])
    amount = receipt["amount"]
    if isinstance(amount, Decimal):
        amt_str = format(amount, "f")
    else:
        amt_str = str(amount)

    root = etree.Element("Document", nsmap=NSMAP)
    cst = _elm(root, "CstmrCdtTrfInitn")

    # Group Header
    grp = _elm(cst, "GrpHdr")
    _elm(grp, "MsgId", reference)
    _elm(grp, "CreDtTm", _iso_dt(created_at))
    _elm(grp, "NbOfTxs", "1")
    initg = _elm(grp, "InitgPty")
    _elm(initg, "Nm", "Capella")

    # Payment Information
    pmt = _elm(cst, "PmtInf")
    _elm(pmt, "PmtInfId", rid)
    _elm(pmt, "PmtMtd", "TRF")
    _elm(pmt, "NbOfTxs", "1")
    _elm(pmt, "CtrlSum", amt_str)
    _elm(pmt, "ReqdExctnDt", _iso_date(created_at))

    # Debtor
    dbtr = _elm(pmt, "Dbtr")
    _wallet_party(dbtr, role_nm=None, wallet_addr=sender_wallet, scheme="WALLET")

    dbtr_acct = _elm(pmt, "DbtrAcct")
    _wallet_acct(dbtr_acct, wallet_addr=sender_wallet, scheme="WALLET_ACCOUNT")

    dbtr_agt = _elm(pmt, "DbtrAgt")
    _agent_not_provided(dbtr_agt)

    _elm(pmt, "ChrgBr", "SLEV")

    # Credit Transfer Transaction
    cdt = _elm(pmt, "CdtTrfTxInf")
    pmt_id = _elm(cdt, "PmtId")
    _elm(pmt_id, "EndToEndId", rid)

    amt = _elm(cdt, "Amt")
    _elm(amt, "InstdAmt", amt_str, attrib={"Ccy": currency})

    cdtr_agt = _elm(cdt, "CdtrAgt")
    _agent_not_provided(cdtr_agt)

    cdtr = _elm(cdt, "Cdtr")
    _wallet_party(cdtr, role_nm=None, wallet_addr=receiver_wallet, scheme="WALLET")

    cdtr_acct = _elm(cdt, "CdtrAcct")
    _wallet_acct(cdtr_acct, wallet_addr=receiver_wallet, scheme="WALLET_ACCOUNT")

    rmt = _elm(cdt, "RmtInf")
    _elm(rmt, "Ustrd", reference)

    xml_bytes = etree.tostring(
        root,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
        standalone="yes",
    )

    # Validate if schema available
    schema = _get_schema()
    if schema is not None:
        try:
            # xmlschema can validate bytes directly
            schema.validate(xml_bytes)
        except Exception as e:
            # Re-raise with readable error list if possible
            if hasattr(schema, "iter_errors"):
                msgs = []
                for err in schema.iter_errors(xml_bytes):
                    msgs.append(str(err))
                raise ValueError("ISO20022 schema validation failed:\n" + "\n".join(msgs)) from e
            raise

    return xml_bytes


def generate_pain001_from_cfg(receipt: Dict[str, Any], cfg) -> bytes:
    """
    Build pain.001 honoring OrgConfigModel:
      - ID strategies: msg_id, e2e_id, pmt_inf_id with strategies uuid|reference|composite
      - Execution timing: ReqdExctnDt immediate|date with offset days
      - InitgPty name from org.name; optional LEI under InitgPty.Id.OrgId.LEI when org.lei present
      - Optional IBAN/BIC/LEI injection based on mapping flags and defaults
      - Charge bearer / purpose / category purpose from mapping
    """
    from datetime import timedelta

    def _strategy(val: str) -> str:
        return (val or "").strip()

    def _id_for(strategy: str, rid: str, reference: str) -> str:
        s = (strategy or "uuid").lower()
        if s == "uuid":
            return rid
        if s == "reference":
            return reference
        # composite
        return f"{reference}:{rid}"

    created_at: datetime = receipt["created_at"]
    reference: str = str(receipt.get("reference"))
    rid: str = str(receipt.get("id"))
    sender_wallet: str = str(receipt.get("sender_wallet"))
    receiver_wallet: str = str(receipt.get("receiver_wallet"))
    currency: str = str(receipt.get("currency"))
    amount = receipt["amount"]
    if isinstance(amount, Decimal):
        amt_str = format(amount, "f")
    else:
        amt_str = str(amount)

    msg_id = _id_for(getattr(getattr(cfg, "id_strategy", None), "msg_id_strategy", "uuid"), rid, reference)
    e2e_id = _id_for(getattr(getattr(cfg, "id_strategy", None), "e2e_id_strategy", "reference"), rid, reference)
    pmt_inf_id = _id_for(getattr(getattr(cfg, "id_strategy", None), "pmt_inf_id_strategy", "uuid"), rid, reference)

    ex_mode = getattr(getattr(cfg, "id_strategy", None), "reqd_exctn_mode", "immediate")
    offset_days = int(getattr(getattr(cfg, "id_strategy", None), "reqd_exctn_offset_days", 0) or 0)
    if ex_mode == "date":
        exec_date = _iso_date(created_at + timedelta(days=offset_days))
    else:
        exec_date = _iso_date(created_at)

    charge_bearer = getattr(getattr(cfg, "mapping", None), "charge_bearer", "SLEV") or "SLEV"
    purpose_code = getattr(getattr(cfg, "mapping", None), "purpose", None)
    category_purpose = getattr(getattr(cfg, "mapping", None), "category_purpose", None)

    include_iban = bool(getattr(getattr(cfg, "mapping", None), "include_iban", False))
    include_bic = bool(getattr(getattr(cfg, "mapping", None), "include_bic", False))
    include_lei = bool(getattr(getattr(cfg, "mapping", None), "include_lei", False))
    d_debtor_iban = getattr(getattr(cfg, "mapping", None), "default_debtor_iban", None)
    d_creditor_iban = getattr(getattr(cfg, "mapping", None), "default_creditor_iban", None)
    d_debtor_bic = getattr(getattr(cfg, "mapping", None), "default_debtor_bic", None)
    d_creditor_bic = getattr(getattr(cfg, "mapping", None), "default_creditor_bic", None)
    default_org_lei = getattr(getattr(cfg, "mapping", None), "default_org_lei", None)
    org_name = getattr(getattr(cfg, "org", None), "name", "Capella") or "Capella"
    org_lei = getattr(getattr(cfg, "org", None), "lei", None)

    # Document
    root = etree.Element("Document", nsmap=NSMAP)
    cst = _elm(root, "CstmrCdtTrfInitn")

    # Group Header
    grp = _elm(cst, "GrpHdr")
    _elm(grp, "MsgId", msg_id)
    _elm(grp, "CreDtTm", _iso_dt(created_at))
    _elm(grp, "NbOfTxs", "1")
    initg = _elm(grp, "InitgPty")
    _elm(initg, "Nm", org_name)
    if org_lei:
        id_ = _elm(initg, "Id")
        orgid = _elm(id_, "OrgId")
        _elm(orgid, "LEI", org_lei)

    # Payment Information
    pmt = _elm(cst, "PmtInf")
    _elm(pmt, "PmtInfId", pmt_inf_id)
    _elm(pmt, "PmtMtd", "TRF")
    _elm(pmt, "NbOfTxs", "1")
    _elm(pmt, "CtrlSum", amt_str)
    _elm(pmt, "ReqdExctnDt", exec_date)

    # Optional payment type info
    if purpose_code or category_purpose:
        pti = _elm(pmt, "PmtTpInf")
        if purpose_code:
            purp = _elm(pti, "Purp")
            _elm(purp, "Cd", purpose_code)
        if category_purpose:
            cat = _elm(pti, "CtgyPurp")
            _elm(cat, "Cd", category_purpose)

    # Debtor
    dbtr = _elm(pmt, "Dbtr")
    _wallet_party(dbtr, role_nm=None, wallet_addr=sender_wallet, scheme="WALLET")
    # Optional debtor LEI
    if include_lei and (default_org_lei or org_lei):
        id_ = _elm(dbtr, "Id")
        orgid = _elm(id_, "OrgId")
        _elm(orgid, "LEI", default_org_lei or org_lei)

    # Debtor account: IBAN or Wallet account
    dbtr_acct = _elm(pmt, "DbtrAcct")
    id_dbtr = _elm(dbtr_acct, "Id")
    if include_iban and d_debtor_iban:
        _elm(id_dbtr, "IBAN", d_debtor_iban)
    else:
        othr = _elm(id_dbtr, "Othr")
        _elm(othr, "Id", sender_wallet)
        schme = _elm(othr, "SchmeNm")
        _elm(schme, "Prtry", "WALLET_ACCOUNT")

    # Debtor agent: BIC or NOTPROVIDED
    dbtr_agt = _elm(pmt, "DbtrAgt")
    agt = _elm(dbtr_agt, "FinInstnId")
    if include_bic and d_debtor_bic:
        _elm(agt, "BICFI", d_debtor_bic)
    else:
        othr = _elm(agt, "Othr")
        _elm(othr, "Id", "NOTPROVIDED")

    _elm(pmt, "ChrgBr", charge_bearer)

    # Credit Transfer Transaction
    cdt = _elm(pmt, "CdtTrfTxInf")
    pmt_id = _elm(cdt, "PmtId")
    _elm(pmt_id, "EndToEndId", e2e_id)

    amt = _elm(cdt, "Amt")
    _elm(amt, "InstdAmt", amt_str, attrib={"Ccy": currency})

    # Creditor agent
    cdtr_agt = _elm(cdt, "CdtrAgt")
    agt2 = _elm(cdtr_agt, "FinInstnId")
    if include_bic and d_creditor_bic:
        _elm(agt2, "BICFI", d_creditor_bic)
    else:
        othr2 = _elm(agt2, "Othr")
        _elm(othr2, "Id", "NOTPROVIDED")

    # Creditor
    cdtr = _elm(cdt, "Cdtr")
    _wallet_party(cdtr, role_nm=None, wallet_addr=receiver_wallet, scheme="WALLET")
    if include_lei and (default_org_lei or org_lei):
        idc = _elm(cdtr, "Id")
        orgidc = _elm(idc, "OrgId")
        _elm(orgidc, "LEI", default_org_lei or org_lei)

    # Creditor account: IBAN or Wallet account
    cdtr_acct = _elm(cdt, "CdtrAcct")
    id_cdtr = _elm(cdtr_acct, "Id")
    if include_iban and d_creditor_iban:
        _elm(id_cdtr, "IBAN", d_creditor_iban)
    else:
        othr = _elm(id_cdtr, "Othr")
        _elm(othr, "Id", receiver_wallet)
        schme = _elm(othr, "SchmeNm")
        _elm(schme, "Prtry", "WALLET_ACCOUNT")

    # Remittance info
    rmt = _elm(cdt, "RmtInf")
    _elm(rmt, "Ustrd", reference)

    xml_bytes = etree.tostring(
        root,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
        standalone="yes",
    )

    # Validate if schema available
    schema = _get_schema()
    if schema is not None:
        try:
            schema.validate(xml_bytes)
        except Exception as e:
            if hasattr(schema, "iter_errors"):
                msgs = []
                for err in schema.iter_errors(xml_bytes):
                    msgs.append(str(err))
                raise ValueError("ISO20022 schema validation failed:\n" + "\n".join(msgs)) from e
            raise

    return xml_bytes
