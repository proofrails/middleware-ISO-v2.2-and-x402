from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Literal, Optional

# Optional outbound HTTP for provider hooks
try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

Decision = Literal["allow", "flag", "deny"]


@dataclass
class TravelRuleResult:
    decision: Decision
    reason: Optional[str] = None


@dataclass
class SanctionsResult:
    decision: Decision
    reason: Optional[str] = None


def _to_decimal(val: Any) -> Optional[Decimal]:
    try:
        if isinstance(val, Decimal):
            return val
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _merge_decisions(a: Decision, b: Decision) -> Decision:
    # deny > flag > allow
    order = {"deny": 2, "flag": 1, "allow": 0}
    return a if order[a] >= order[b] else b


def call_travel_rule_provider(provider: Optional[str], data: Dict[str, Any]) -> TravelRuleResult:
    """
    Pluggable travel-rule provider hook.
    Supported patterns:
      - http+json:<URL>  -> POST JSON { ... } to URL, expect { decision: 'allow'|'flag'|'deny', reason?: str }
      - mock:deny_if_amount_gt:<value> -> deny when amount > value
    Default: allow
    """
    if not provider:
        return TravelRuleResult(decision="allow")
    p = provider.strip()
    try:
        if p.startswith("http+json:") and requests:
            url = p.split(":", 1)[1]
            r = requests.post(url, json=data, timeout=10)
            if r.ok:
                js = r.json() or {}
                dec = js.get("decision", "allow")
                reason = js.get("reason")
                if dec in ("allow", "flag", "deny"):
                    return TravelRuleResult(decision=dec, reason=reason)
        elif p.startswith("mock:deny_if_amount_gt:"):
            thr_s = p.split(":", 2)[2]
            thr = _to_decimal(thr_s)
            amt = _to_decimal(data.get("amount"))
            if thr is not None and amt is not None and amt > thr:
                return TravelRuleResult(decision="deny", reason=f"amount {amt} > {thr}")
    except Exception:
        # On provider error, default to allow (non-blocking)
        return TravelRuleResult(decision="allow", reason="provider_error_ignored")
    return TravelRuleResult(decision="allow")


def call_sanctions_provider(provider: Optional[str], data: Dict[str, Any]) -> SanctionsResult:
    """
    Pluggable sanctions provider hook.
    Supported patterns:
      - http+json:<URL> -> POST JSON { ... } to URL, expect { decision: 'allow'|'flag'|'deny', reason?: str }
      - mock:deny_all -> deny always (testing)
    Default: allow
    """
    if not provider:
        return SanctionsResult(decision="allow")
    p = provider.strip()
    try:
        if p.startswith("http+json:") and requests:
            url = p.split(":", 1)[1]
            r = requests.post(url, json=data, timeout=10)
            if r.ok:
                js = r.json() or {}
                dec = js.get("decision", "allow")
                reason = js.get("reason")
                if dec in ("allow", "flag", "deny"):
                    return SanctionsResult(decision=dec, reason=reason)
        elif p == "mock:deny_all":
            return SanctionsResult(decision="deny", reason="mock_policy")
    except Exception:
        return SanctionsResult(decision="allow", reason="provider_error_ignored")
    return SanctionsResult(decision="allow")


def evaluate_travel_rule(
    amount: Any,
    threshold: Optional[float | str | Decimal],
    provider: Optional[str] = None,
) -> TravelRuleResult:
    """
    Travel rule evaluator:
    - If threshold is None: start with 'allow'
    - If amount >= threshold: 'flag' (PoC historical behavior)
    - Provider hook (optional) can upgrade to 'deny' or 'flag'.
    """
    local_dec = "allow"
    local_reason = None
    amt = _to_decimal(amount)
    thr = _to_decimal(threshold) if threshold is not None else None
    if amt is not None and thr is not None and amt >= thr:
        local_dec = "flag"
        local_reason = f"amount {amt} >= threshold {thr}"

    # Provider merge
    prov = call_travel_rule_provider(provider, {"amount": amount, "threshold": threshold})
    merged = _merge_decisions(prov.decision, local_dec)  # provider can escalate
    reason = prov.reason or local_reason
    return TravelRuleResult(decision=merged, reason=reason)


def check_sanctions(
    sender_wallet: Optional[str],
    receiver_wallet: Optional[str],
    provider: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> SanctionsResult:
    """
    Sanctions check:
    - Default 'allow' as before
    - If provider configured, use hook (http+json or mock) which can result in 'deny' or 'flag'
    """
    data = {
        "sender_wallet": sender_wallet,
        "receiver_wallet": receiver_wallet,
        "metadata": metadata or {},
    }
    return call_sanctions_provider(provider, data)
