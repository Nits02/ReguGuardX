"""
Build eval/evalset.json (ADK evalset format) from the generated data: pick a few
representative txn_ids per violation category plus clean controls, and turn each
into an eval case whose expected outcome mentions the correct disposition/violation.

We keep this human-readable and small so it runs fast during the demo.
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
labels = [json.loads(l) for l in open(ROOT / "data" / "generated" / "labels.jsonl")]

by_label = defaultdict(list)
for l in labels:
    by_label[l["label"]].append(l)

# expected disposition per label
EXPECT = {
    "sanctions_hit":    ("escalate", "AML-SAN-03"),
    "structuring":      ("escalate", "AML-STR-02"),
    "pep_counterparty": ("escalate", "AML-PEP-04"),
    "velocity_anomaly": ("escalate", "AML-VEL-05"),
    "clean":            ("clear",    ""),
}

cases = []
for label, rows in by_label.items():
    for r in rows[:3]:  # 3 per category
        disp, rule = EXPECT[label]
        cases.append({
            "txn_id": r["txn_id"],
            "label": label,
            "expected_disposition": disp,
            "expected_rule": rule,
            "query": f"Audit transaction {r['txn_id']} and return its disposition with rule citations.",
        })

out = {"eval_set_id": "reguguard_core", "name": "ReguGuard core AML eval", "eval_cases": cases}
(Path(__file__).parent / "evalset.json").write_text(json.dumps(out, indent=2))
print(f"Wrote {len(cases)} eval cases to eval/evalset.json")
