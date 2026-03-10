from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import bundle, models  # type: ignore

# Optional OpenAI provider (server-side only)
try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

ARTIFACTS_DIR = os.getenv("ARTIFACTS_DIR", "artifacts")
AI_SESSIONS_DIR = Path(ARTIFACTS_DIR) / "ai_sessions"
AI_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _log_session(session_id: str, entry: Dict[str, Any]) -> None:
    try:
        p = AI_SESSIONS_DIR / f"{session_id}.log"
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.utcnow().isoformat(), **entry}, separators=(",", ":")) + "\n")
    except Exception:
        pass


def _summarize_receipt(r: models.Receipt) -> Dict[str, Any]:
    return {
        "id": str(r.id),
        "status": r.status,
        "amount": str(r.amount),
        "currency": r.currency,
        "chain": r.chain,
        "reference": r.reference,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "anchored_at": r.anchored_at.isoformat() if r.anchored_at else None,
        "bundle_hash": r.bundle_hash,
        "flare_txid": r.flare_txid,
    }


def _list_receipts_tool(db_session, principal, scope: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    if not scope.get("allow_read_receipts"):
        return {"error": "scope_violation", "detail": "Assistant is not allowed to read receipts."}

    q = db_session.query(models.Receipt)

    # Enforce principal scoping (do not allow AI endpoint to bypass auth model)
    if not getattr(principal, "is_admin", False):
        project_id = getattr(principal, "project_id", None)
        if project_id:
            q = q.filter(models.Receipt.project_id == project_id)

    # optional filters
    if params.get("status"):
        q = q.filter(models.Receipt.status == params["status"])
    if params.get("chain"):
        q = q.filter(models.Receipt.chain == params["chain"])

    all_rows = q.all()

    # allowed subset (optional extra restriction)
    allowed_ids = scope.get("allowed_receipt_ids") or []
    if allowed_ids:
        all_rows = [r for r in all_rows if str(r.id) in allowed_ids]

    # truncate to 50
    rows = all_rows[:50]
    return {"items": [_summarize_receipt(r) for r in rows], "total": len(all_rows)}


def _get_receipt_tool(db_session, principal, scope: Dict[str, Any], rid: str) -> Dict[str, Any]:
    if not scope.get("allow_read_receipts"):
        return {"error": "scope_violation", "detail": "Assistant is not allowed to read receipts."}

    allowed_ids = scope.get("allowed_receipt_ids") or []
    if allowed_ids and rid not in allowed_ids:
        return {"error": "scope_violation", "detail": f"Receipt {rid} not in allowed list."}

    r: Optional[models.Receipt] = db_session.get(models.Receipt, rid)
    if not r:
        return {"error": "not_found", "detail": f"Receipt {rid} not found"}

    # Enforce principal scoping
    if not getattr(principal, "is_admin", False):
        project_id = getattr(principal, "project_id", None)
        if project_id and str(getattr(r, "project_id", "")) != str(project_id):
            return {"error": "scope_violation", "detail": "Receipt not accessible for this principal."}

    return {"item": _summarize_receipt(r)}


def _list_artifacts_tool(db_session, principal, scope: Dict[str, Any], rid: str) -> Dict[str, Any]:
    if not scope.get("allow_read_receipts"):
        return {"error": "scope_violation", "detail": "Assistant is not allowed to read receipts."}

    allowed_ids = scope.get("allowed_receipt_ids") or []
    if allowed_ids and rid not in allowed_ids:
        return {"error": "scope_violation", "detail": f"Receipt {rid} not in allowed list."}

    # Enforce principal scoping using Receipt.project_id
    if not getattr(principal, "is_admin", False):
        project_id = getattr(principal, "project_id", None)
        if project_id:
            rec = db_session.get(models.Receipt, rid)
            if not rec:
                return {"error": "not_found", "detail": f"Receipt {rid} not found"}
            if str(getattr(rec, "project_id", "")) != str(project_id):
                return {"error": "scope_violation", "detail": "Receipt not accessible for this principal."}

    arts = db_session.query(models.ISOArtifact).filter(models.ISOArtifact.receipt_id == rid).all()
    out = []
    for a in arts:
        name = Path(a.path).name if a.path else ""
        if not name:
            continue
        out.append(
            {
                "type": a.type,
                "url": f"/files/{rid}/{name}",
                "sha256": a.sha256,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
        )
    return {"items": out}


def _read_vc_tool(db_session, principal, scope: Dict[str, Any], rid: str) -> Dict[str, Any]:
    # vc.json access is the most sensitive: require BOTH receipts access and artifacts access.
    if not scope.get("allow_read_receipts"):
        return {"error": "scope_violation", "detail": "Assistant is not allowed to read receipts."}
    if not scope.get("allow_read_artifacts"):
        return {"error": "scope_violation", "detail": "Assistant is not allowed to read artifacts."}

    allowed_ids = scope.get("allowed_receipt_ids") or []
    if allowed_ids and rid not in allowed_ids:
        return {"error": "scope_violation", "detail": f"Receipt {rid} not in allowed list."}

    # Enforce principal scoping
    if not getattr(principal, "is_admin", False):
        project_id = getattr(principal, "project_id", None)
        if project_id:
            rec = db_session.get(models.Receipt, rid)
            if not rec:
                return {"error": "not_found", "detail": f"Receipt {rid} not found"}
            if str(getattr(rec, "project_id", "")) != str(project_id):
                return {"error": "scope_violation", "detail": "Receipt not accessible for this principal."}

    vc_path = Path(ARTIFACTS_DIR) / rid / "vc.json"
    if not vc_path.exists():
        return {"error": "not_found", "detail": "vc.json not found"}

    try:
        txt = vc_path.read_text(encoding="utf-8")
        return {"vc": json.loads(txt)}
    except Exception as e:
        return {"error": "read_error", "detail": str(e)}


def _read_iso_payload_tool(db_session, principal, scope: Dict[str, Any], rid: str) -> Dict[str, Any]:
    """Read ISO 20022 XML payload with detailed parsing for AI analysis."""
    if not scope.get("allow_read_receipts"):
        return {"error": "scope_violation", "detail": "Assistant is not allowed to read receipts."}
    if not scope.get("allow_read_artifacts"):
        return {"error": "scope_violation", "detail": "Assistant is not allowed to read artifacts."}

    allowed_ids = scope.get("allowed_receipt_ids") or []
    if allowed_ids and rid not in allowed_ids:
        return {"error": "scope_violation", "detail": f"Receipt {rid} not in allowed list."}

    # Enforce principal scoping
    if not getattr(principal, "is_admin", False):
        project_id = getattr(principal, "project_id", None)
        if project_id:
            rec = db_session.get(models.Receipt, rid)
            if not rec:
                return {"error": "not_found", "detail": f"Receipt {rid} not found"}
            if str(getattr(rec, "project_id", "")) != str(project_id):
                return {"error": "scope_violation", "detail": "Receipt not accessible for this principal."}

    # Find ISO XML artifact
    arts = db_session.query(models.ISOArtifact).filter(
        models.ISOArtifact.receipt_id == rid,
        models.ISOArtifact.type.in_(["pain.001", "pacs.008", "camt.053", "camt.052"])
    ).all()
    
    if not arts:
        return {"error": "not_found", "detail": "No ISO XML artifacts found"}

    result = {"receipt_id": rid, "payloads": []}
    for art in arts:
        if not art.path:
            continue
        try:
            payload_path = Path(art.path)
            if payload_path.exists():
                xml_content = payload_path.read_text(encoding="utf-8")
                # Parse key fields from XML (simplified extraction)
                payload_info = {
                    "type": art.type,
                    "sha256": art.sha256,
                    "size_bytes": len(xml_content),
                    "preview": xml_content[:500] + "..." if len(xml_content) > 500 else xml_content,
                }
                result["payloads"].append(payload_info)
        except Exception as e:
            result["payloads"].append({"type": art.type, "error": str(e)})
    
    return result


def _verify_tool(req: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if req.get("bundle_url"):
            v = bundle.verify_bundle(req["bundle_url"])
            return {"bundle_hash": v.bundle_hash, "errors": list(v.errors)}
        elif req.get("bundle_hash"):
            return {"bundle_hash": req["bundle_hash"], "errors": []}
        return {"error": "invalid_request", "detail": "Provide bundle_url or bundle_hash"}
    except Exception as e:
        return {"error": "verify_failed", "detail": str(e)}


INTEGRATION_GUIDE = """Project / API key model (important):
- A Project is created by SIWE (wallet signature) via POST /v1/projects/register.
- That endpoint returns an API key ONCE; in the web-alt UI it is stored server-side in an httpOnly cookie.
- All browser requests must go through /api/proxy so the cookie can inject X-API-Key server-side.
- Receipts are scoped by key:
  - project keys: scope=mine sees only that project's receipts.
  - admin keys: can use scope=all to see all receipts.
- Tenant anchoring mode:
  - receipts can reach status=awaiting_anchor.
  - tenant submits flare_txid via POST /v1/iso/confirm-anchor.
"""


def _sdk_help_tool(lang: str, packaging: Optional[str], base_url: Optional[str]) -> Dict[str, Any]:
    base = base_url or os.getenv("PUBLIC_BASE_URL") or "http://localhost:8000"
    if lang == "ts":
        tip = (
            "TypeScript SDK usage:\n"
            "- If you are integrating from a backend service: pass your project API key as X-API-Key.\n"
            "- If you are integrating from web-alt: use baseUrl='/api/proxy' (cookie injects X-API-Key server-side).\n"
            f"Base URL: {base}. Packaging: {packaging or 'none'}."
        )
        snippet = (
            "import IsoMiddlewareClient from 'iso-middleware-sdk';\n"
            f"const api = new IsoMiddlewareClient({{ baseUrl: '{base}', apiKey: process.env.API_KEY }});\n"
            "const page = await api.listReceipts({ page: 1, page_size: 10, scope: 'mine' });\n"
            "console.log(page.items);\n"
        )
        return {"tip": tip, "snippet": snippet}
    elif lang == "python":
        tip = (
            "Python SDK usage:\n"
            "- Use your project API key in X-API-Key.\n"
            f"Base URL: {base}. Packaging: {packaging or 'none'}."
        )
        snippet = (
            "from iso_client import ISOClient\n"
            f"api = ISOClient(base_url='{base}', api_key='YOUR_KEY')\n"
            "print(api.list_receipts(page=1, page_size=10, scope='mine'))\n"
        )
        return {"tip": tip, "snippet": snippet}
    else:
        return {"tip": "Unsupported lang; use ts | python", "snippet": ""}


def assist(payload: Dict[str, Any], db_session, *, principal=None) -> Dict[str, Any]:
    """
    Lightweight assistant endpoint with scope-checked tools and simple heuristic replies.
    This avoids exposing provider keys in the UI. If AI_PROVIDER is configured (optional),
    you can extend to call an external LLM; by default we answer with tool results + guide hints.
    """
    messages: List[Dict[str, str]] = payload.get("messages") or []
    scope: Dict[str, Any] = payload.get("scope") or {}
    session_id: str = payload.get("session_id") or "default"
    params: Dict[str, Any] = payload.get("params") or {}
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = m.get("content") or ""
            break

    principal_role = getattr(principal, "role", "public") if principal is not None else "public"
    principal_project_id = getattr(principal, "project_id", None) if principal is not None else None

    _log_session(
        session_id,
        {"dir": "in", "user": last_user, "scope": scope, "principal": {"role": principal_role, "project_id": principal_project_id}},
    )

    reply_sections: List[str] = []
    used_tools: List[Dict[str, Any]] = []

    # Heuristic routing
    text = last_user.lower()
    # receipts listing
    if "list receipts" in text or "show receipts" in text:
        res = _list_receipts_tool(db_session, principal, scope, params.get("filters") or {})
        used_tools.append({"tool": "list_receipts", "ok": "error" not in res})
        if "error" in res:
            reply_sections.append(f"Receipts error: {res.get('detail')}")
        else:
            items = res.get("items", [])[:10]
            reply_sections.append(f"Showing {len(items)}/{res.get('total', 0)} receipts:")
            for it in items:
                reply_sections.append(
                    f"- {it['id']} | {it['status']} | {it['amount']} {it['currency']} | ref={it['reference']}"
                )
    # single receipt
    rid = None
    if "receipt " in text:
        try:
            rid = text.split("receipt ", 1)[1].strip().split()[0]
        except Exception:
            rid = None
    if rid:
        res = _get_receipt_tool(db_session, principal, scope, rid)
        used_tools.append({"tool": "get_receipt", "rid": rid, "ok": "error" not in res})
        if "error" in res:
            reply_sections.append(f"Receipt {rid} error: {res.get('detail')}")
        else:
            it = res.get("item", {})
            reply_sections.append(
                f"Receipt {rid}: status={it.get('status')} amount={it.get('amount')} {it.get('currency')} chain={it.get('chain')}"
            )
            # artifacts
            arts = _list_artifacts_tool(db_session, principal, scope, rid)
            used_tools.append({"tool": "list_artifacts", "rid": rid, "ok": "error" not in arts})
            if "error" not in arts:
                if arts.get("items"):
                    reply_sections.append("Artifacts:")
                    for a in arts["items"][:10]:
                        reply_sections.append(f"  - {a['type']}: {a['url']} (sha256={a.get('sha256')})")
            # vc.json if allowed
            if scope.get("allow_read_artifacts"):
                vc = _read_vc_tool(db_session, principal, scope, rid)
                used_tools.append({"tool": "read_vc", "rid": rid, "ok": "error" not in vc})
                if "error" not in vc:
                    reply_sections.append("Found vc.json. Key fields:")
                    issuer = vc["vc"].get("issuer") if isinstance(vc.get("vc"), dict) else None
                    reply_sections.append(f" - issuer: {issuer}")
    # verify
    if "verify " in text or "check bundle" in text:
        req = {}
        if "http" in text and ".zip" in text:
            start = text.find("http")
            end = text.find(".zip") + 4
            req["bundle_url"] = text[start:end]
        if "bundle_hash" in params:
            req["bundle_hash"] = params["bundle_hash"]
        v = _verify_tool(req)
        used_tools.append({"tool": "verify", "ok": "error" not in v})
        if "error" in v:
            reply_sections.append(f"Verify error: {v.get('detail')}")
        else:
            reply_sections.append(f"Bundle hash: {v.get('bundle_hash')}; errors={v.get('errors')}")

    # sdk
    if "sdk" in text or "client" in text or "typescript" in text or "python" in text:
        lang = "ts" if "ts" in text or "typescript" in text else ("python" if "python" in text else "ts")
        res = _sdk_help_tool(lang, params.get("packaging"), params.get("base_url"))
        used_tools.append({"tool": "sdk_help", "lang": lang, "ok": True})
        reply_sections.append(res["tip"])
        if res.get("snippet"):
            reply_sections.append("Example:\n" + res["snippet"])

    if not reply_sections:
        reply_sections.append(
            "I can help you:\n- Explain SDK generation and usage (ts/python)\n- List receipts or inspect a receipt (if allowed)\n- Show artifacts (if allowed)\n- Verify a bundle URL or hash\nTry: 'List receipts', 'Receipt <id>', 'Verify <bundle_url>', or 'SDK help (ts)'."
        )

    reply = "\n".join(reply_sections)

    # Optional LLM-enhanced reply (server-side; scope-enforced)
    try:
        provider = (os.getenv("AI_PROVIDER") or "").strip().lower()
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            model = os.getenv("AI_MODEL") or "gpt-4o-mini"
            temperature = float(os.getenv("AI_TEMPERATURE") or "0.2")
            max_tokens = int(os.getenv("AI_MAX_TOKENS") or "512")
            if OpenAI is None or not api_key:
                raise RuntimeError("openai_unavailable")
            # Build a scope-aware system prompt; never send secrets or unrestricted content
            scope_lines = [
                f"- allow_read_receipts={bool(scope.get('allow_read_receipts'))}",
                f"- allow_read_artifacts={bool(scope.get('allow_read_artifacts'))}",
                f"- allow_config_changes={bool(scope.get('allow_config_changes'))}",
                f"- allowed_receipt_ids={','.join(scope.get('allowed_receipt_ids') or []) or '(none)'}",
            ]
            sys_prompt = (
                "You are a helpful payments middleware assistant for an ISO 20022 evidence/anchoring platform.\n"
                "Always follow *both* the authenticated principal constraints and the explicit UI scope toggles.\n\n"
                f"Principal role: {principal_role}; project_id: {principal_project_id or '(none)'}\n\n"
                + INTEGRATION_GUIDE
                + "\nScope toggles:\n"
                + "\n".join(scope_lines)
                + "\n\nRules:\n"
                "- Never claim access to data not present in the provided Context/tool outputs.\n"
                "- For receipts, respect project scoping; if user asks for scope=all but key is not admin, explain it.\n"
                "- For SDK guidance, show how to set base_url and X-API-Key and mention /api/proxy pattern for web-alt.\n"
                "- Do not invent on-chain results; verification must come from verify endpoints/tool output."
            )
            # Provide tool summaries/context (already scope-filtered by our tools)
            context = "\n".join(reply_sections)
            client = OpenAI(api_key=api_key)
            completion = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"Context:\n{context}\n\nUser: {last_user or '(no message)'}"},
                ],
            )
            maybe = (completion.choices[0].message.content or "").strip()
            if maybe:
                reply = maybe
    except Exception:
        # Best-effort; fall back to heuristic reply if provider unavailable or any error occurs
        pass

    _log_session(session_id, {"dir": "out", "assistant": reply, "used_tools": used_tools})
    return {"reply": reply, "used_tools": used_tools}
