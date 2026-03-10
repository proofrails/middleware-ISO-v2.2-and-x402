from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any, Dict

from lxml import etree

from .. import iso  # existing pain.001 generator
from ..config import OrgConfigModel

NS_PAIN001 = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.09"


def _round_fiat(val: Decimal) -> str:
    return str(val.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))


def _maybe_add_fx(root: etree._Element, receipt: Dict[str, Any], cfg: OrgConfigModel) -> bytes:
    """
    Optionally add EqvtAmt and XchgRateInf to CdtTrfTxInf/Amt based on fx_policy.
    This is a best-effort post-processing step; if required inputs are missing, it no-ops.
    """
    try:
        if cfg.fx_policy.mode != "eqvt_amt":
            return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8", standalone="yes")
        base_ccy = cfg.fx_policy.base_ccy
        if not base_ccy:
            return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8", standalone="yes")

        # Expect an optional fx_rate injected by the caller (or future provider)
        fx_rate = receipt.get("fx_rate")  # type: ignore
        if fx_rate is None:
            return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8", standalone="yes")

        amt_dec = receipt.get("amount")
        if not isinstance(amt_dec, Decimal):
            try:
                amt_dec = Decimal(str(amt_dec))
            except Exception:
                return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8", standalone="yes")

        rate_dec = Decimal(str(fx_rate))
        eq_amt = _round_fiat(amt_dec * rate_dec)

        # Find CdtTrfTxInf/Amt
        ns = {"p": NS_PAIN001}
        amt_node = root.find(".//p:CdtTrfTxInf/p:Amt", namespaces=ns)
        if amt_node is None:
            return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8", standalone="yes")

        # Insert EqvtAmt and XchgRateInf siblings under Amt
        eq = etree.SubElement(amt_node, "EqvtAmt", Ccy=base_ccy)
        eq.text = eq_amt
        xri = etree.SubElement(amt_node, "XchgRateInf")
        etree.SubElement(xri, "XchgRate").text = str(fx_rate)
        # Optional: add rate source fields as needed in future

        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8", standalone="yes")
    except Exception:
        # Fail-safe: return original
        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8", standalone="yes")


def generate_pain001_with_fx(receipt: Dict[str, Any], cfg: OrgConfigModel) -> bytes:
    """
    Generate base pain.001 via existing generator; optionally enrich with EqvtAmt/XchgRateInf
    depending on fx_policy and provided fx_rate.
    """
    base_xml = iso.generate_pain001_from_cfg(receipt, cfg)
    if cfg.fx_policy.mode == "none":
        return base_xml
    try:
        root = etree.fromstring(base_xml)
        return _maybe_add_fx(root, receipt, cfg)
    except Exception:
        return base_xml
