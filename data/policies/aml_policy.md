# ACME Bank — Anti-Money-Laundering (AML) Policy (Illustrative)

Document ID: POL-AML-001 | Version 3.2 | Owner: Financial Crime Compliance

## 1. Purpose
This policy establishes controls to detect, prevent and report money laundering and
terrorist financing in accordance with the Bank Secrecy Act (BSA), the USA PATRIOT Act,
and FATF recommendations.

## 2. Currency Transaction Reporting (CTR)
Rule AML-CTR-01: Any single currency transaction, or aggregation of related transactions,
equal to or exceeding USD 10,000 within a 24-hour period must be reported via a CTR.

## 3. Structuring / Smurfing
Rule AML-STR-02: Multiple transactions deliberately kept below the USD 10,000 CTR
threshold to the same or related beneficiary within a short window constitute STRUCTURING
and must be escalated regardless of individual amounts. Indicators: 3+ transactions
between USD 8,000 and USD 9,999 to a common beneficiary within 72 hours.

## 4. Sanctions Screening
Rule AML-SAN-03: No transaction may complete where the originator, beneficiary, or
beneficiary country appears on an applicable sanctions list (e.g., OFAC SDN). Any hit is
a CRITICAL violation requiring immediate hold and human review. Do not clear automatically.

## 5. Politically Exposed Persons (PEP)
Rule AML-PEP-04: Transactions involving a PEP as counterparty require enhanced due
diligence (EDD) and senior-compliance sign-off before completion.

## 6. Velocity / Behavioural Anomaly
Rule AML-VEL-05: An abnormal spike in transaction frequency from a single originator
(e.g., 6+ transactions within 60 minutes) is a velocity anomaly and must be reviewed for
layering activity.

## 7. Disposition Definitions
- ESCALATE: route to a human investigator; suspected violation.
- CLEAR: no indicators; close alert.
- REQUEST_INFO: insufficient data; request supporting documentation.

## 8. Human-in-the-Loop Mandate
Rule AML-HITL-06: Any disposition with a risk score at or above the CRITICAL threshold,
and ALL sanctions hits, MUST be paused for human compliance-officer approval before the
system records a final disposition.
