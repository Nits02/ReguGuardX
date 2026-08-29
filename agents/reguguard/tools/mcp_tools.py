"""
MCP toolsets (Layer 2 wiring).

Connects ADK agents to the Transaction + Sanctions MCP servers over
streamable-HTTP. On Cloud Run the servers are private; we attach a Google-signed
OIDC id-token so only authorized service accounts can invoke them (server-to-server OAuth).

NOTE: ADK's MCP connection param class names have shifted across versions.
This module tries the current name first and falls back. If import fails,
check `pip show google-adk` and the ADK MCP docs, then set the class accordingly.
"""
import os
from .. import config

try:
    # Current ADK (>=1.x)
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
    try:
        from google.adk.tools.mcp_tool.mcp_toolset import StreamableHTTPConnectionParams as _HTTPParams
    except Exception:  # older name
        from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPServerParams as _HTTPParams
    _ADK_MCP_OK = True
except Exception as e:  # pragma: no cover
    _ADK_MCP_OK = False
    _IMPORT_ERR = e


def _auth_headers(audience_url: str) -> dict:
    """Mint an OIDC id-token for the target Cloud Run URL (server-to-server OAuth).
    Locally (http://localhost) we skip auth.

    On Cloud Run / GCE, fetch_id_token works from the metadata server. Locally with
    user ADC it fails; fall back to `gcloud auth print-identity-token` so a developer
    with roles/run.invoker can still hit private MCP services.
    """
    if audience_url.startswith("http://localhost") or audience_url.startswith("http://127."):
        return {}
    audience = audience_url.rsplit("/", 1)[0] if audience_url.endswith("/mcp") else audience_url
    token = None
    try:
        from google.auth.transport.requests import Request
        import google.oauth2.id_token

        token = google.oauth2.id_token.fetch_id_token(Request(), audience)
    except Exception:
        try:
            import subprocess

            token = subprocess.check_output(
                ["gcloud", "auth", "print-identity-token"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            return {}
    return {"Authorization": f"Bearer {token}"} if token else {}


def transaction_toolset():
    if not _ADK_MCP_OK:
        raise ImportError(f"ADK MCP import failed: {_IMPORT_ERR}")
    url = config.TRANSACTION_MCP_URL
    # Cloud Run cold starts + OIDC minting often exceed the ADK default 5s timeout.
    return McpToolset(
        connection_params=_HTTPParams(
            url=url, headers=_auth_headers(url), timeout=60.0, sse_read_timeout=300.0
        )
    )


def sanctions_toolset():
    if not _ADK_MCP_OK:
        raise ImportError(f"ADK MCP import failed: {_IMPORT_ERR}")
    url = config.SANCTIONS_MCP_URL
    return McpToolset(
        connection_params=_HTTPParams(
            url=url, headers=_auth_headers(url), timeout=60.0, sse_read_timeout=300.0
        )
    )
