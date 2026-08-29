"""
Sanctions/Watchlist MCP Server (Layer 2).

Screens an entity against a watchlist (loaded from CSV for the demo; swap the
loader for a real list-provider API in production — that's the whole point of the
MCP decoupling: agents don't change, only this server does).
"""
import csv
import os
from pathlib import Path

from fastmcp import FastMCP

PORT = int(os.environ.get("PORT", "8081"))
WATCHLIST = Path(os.environ.get("WATCHLIST_PATH", "sample_watchlist.csv"))

mcp = FastMCP("sanctions-screening")

# fictional high-risk jurisdictions for the demo
SANCTIONED_COUNTRIES = {"Northland", "Eastoria", "Redzone"}


def _load():
    rows = []
    if WATCHLIST.exists():
        with open(WATCHLIST) as f:
            rows = list(csv.DictReader(f))
    return rows


_LIST = _load()


@mcp.tool()
def screen_entity(name: str, country: str = "", dob: str = "") -> dict:
    """Screen an entity name (and optional country/dob) against the sanctions + PEP
    watchlist. Returns match strength and list type. CRITICAL if an SDN or a
    sanctioned country is matched."""
    name_l = (name or "").strip().lower()
    hits = []
    for row in _LIST:
        entity = row.get("entity_name", "").strip().lower()
        if entity and (entity in name_l or name_l in entity):
            hits.append({"matched_entity": row["entity_name"],
                         "list_type": row.get("list_type", ""),
                         "strength": "strong"})
    country_hit = country in SANCTIONED_COUNTRIES
    severity = "critical" if any(h["list_type"] == "SDN" for h in hits) or country_hit \
        else ("high" if hits else "none")
    return {
        "name": name,
        "country": country,
        "match": bool(hits) or country_hit,
        "hits": hits,
        "sanctioned_country": country_hit,
        "severity": severity,
    }


@mcp.tool()
def is_sanctioned_country(country: str) -> dict:
    """Return whether a country is on the sanctioned/high-risk list."""
    return {"country": country, "sanctioned": country in SANCTIONED_COUNTRIES}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=PORT)
