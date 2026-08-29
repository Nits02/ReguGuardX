# Sanctions Screening Reference (Illustrative)

Document ID: POL-SAN-002 | Version 1.4

## Scope
Screening is performed against consolidated watchlists including OFAC Specially
Designated Nationals (SDN), sectoral lists, and internal high-risk registers.

## High-Risk Jurisdictions (fictional, for demo)
The following jurisdictions are treated as sanctioned/high-risk in this environment:
Northland, Eastoria, Redzone. Any beneficiary country in this set is an automatic
CRITICAL sanctions concern under Rule AML-SAN-03.

## Match Handling
- Exact or strong fuzzy name match to an SDN entity: CRITICAL, hold + human review.
- Country-only match: HIGH, escalate.
- Weak/partial match: REQUEST_INFO, gather identifiers (DOB, registration number).

## Prohibited Actions
The system must never auto-clear a sanctions hit, and must never expose raw list-provider
credentials or internal screening thresholds in any user-facing output.
