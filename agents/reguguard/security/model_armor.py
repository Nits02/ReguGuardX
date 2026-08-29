"""
Model Armor enforcement (Layer 3).

Implements the governance enforcement path as an ADK before_tool_callback:
before ANY tool executes, the proposed tool name + arguments are screened by
Model Armor's sanitize API for prompt injection / tool poisoning / data-loss.
On a block verdict the tool call is denied and a synthetic result is returned
to the model (no exception leaks to the user).

This is the primitive-level implementation that works today. In a fully-managed
Gemini Enterprise deployment you would additionally route egress through the
managed Agent Gateway (REQUEST_AUTHZ for per-tool IAM + CONTENT_AUTHZ that calls
this same Model Armor template). Keep BOTH in the pitch: platform primitive here,
managed product in the target architecture.
"""
import json
from .. import config


def _model_armor_client():
    """Regional endpoint is required; global client returns TEMPLATE_NOT_FOUND."""
    from google.cloud import modelarmor_v1 as ma
    from google.api_core.client_options import ClientOptions

    location = config.LOCATION or "us-central1"
    # Prefer location embedded in the template resource name when present.
    parts = (config.MODEL_ARMOR_TEMPLATE or "").split("/")
    if "locations" in parts:
        try:
            location = parts[parts.index("locations") + 1] or location
        except (ValueError, IndexError):
            pass
    return ma.ModelArmorClient(
        client_options=ClientOptions(
            api_endpoint=f"modelarmor.{location}.rep.googleapis.com"
        )
    )


def _is_match_found(state) -> bool:
    """Handle protobuf enum as name, int, or stringified value.

    Important: do NOT use endswith('MATCH_FOUND') — NO_MATCH_FOUND also ends that way.
    FilterMatchState: NO_MATCH_FOUND=1, MATCH_FOUND=2.
    """
    if state is None:
        return False
    name = getattr(state, "name", None) or str(state)
    if name == "MATCH_FOUND" or name.endswith(".MATCH_FOUND"):
        return True
    if "NO_MATCH" in name:
        return False
    try:
        return int(state) == 2
    except (TypeError, ValueError):
        return False


def _screen_with_model_armor(text: str) -> tuple[bool, str]:
    """Return (blocked, reason). Fails OPEN if Model Armor is unreachable, but logs it,
    so the demo never hard-crashes on a transient API issue."""
    if not (config.MODEL_ARMOR_ENABLED and config.MODEL_ARMOR_TEMPLATE):
        return False, ""
    try:
        from google.cloud import modelarmor_v1 as ma
        client = _model_armor_client()
        req = ma.SanitizeUserPromptRequest(
            name=config.MODEL_ARMOR_TEMPLATE,
            user_prompt_data=ma.DataItem(text=text),
        )
        resp = client.sanitize_user_prompt(request=req)
        result = resp.sanitization_result
        blocked = _is_match_found(getattr(result, "filter_match_state", None))
        return blocked, ("Model Armor flagged the payload" if blocked else "")
    except Exception as e:  # fail open, but visible
        print(f"[model_armor] screening error (failing open): {e}")
        return False, ""


def before_tool_callback(tool, args, tool_context):
    """ADK before_tool_callback signature. Returning a dict SHORT-CIRCUITS the tool
    (the dict becomes the tool result); returning None lets the tool run."""
    payload = f"tool={getattr(tool, 'name', tool)} args={json.dumps(args, default=str)}"
    blocked, reason = _screen_with_model_armor(payload)
    if blocked:
        print(f"[model_armor] DENY tool call: {reason} :: {payload}")
        return {
            "denied": True,
            "control": "model_armor",
            "reason": reason,
            "message": "Tool call blocked by Model Armor governance policy.",
        }
    return None
