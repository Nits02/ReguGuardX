"""
ReguGuard synthetic data generator.

Produces:
  data/generated/transactions.jsonl   - transactions for the demo + eval
  data/generated/labels.jsonl         - ground-truth labels (kept SEPARATE from txns)
  data/sanctions/sample_watchlist.csv - already provided; regenerated if missing

Design goal: DETERMINISTIC planted violations so the eval in eval/ can score
precision/recall reproducibly. Seed is fixed.
"""
import csv
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

SEED = 42
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

OUT = Path(__file__).parent / "generated"
OUT.mkdir(exist_ok=True)
SANCTIONS = Path(__file__).parent / "sanctions"
SANCTIONS.mkdir(exist_ok=True)

# --- Sanctioned / high-risk reference data (illustrative, NOT a real OFAC list) ---
SANCTIONED_COUNTRIES = ["Northland", "Eastoria", "Redzone"]      # fictional high-risk
SANCTIONED_ENTITIES = [
    ("Vega Holdings Ltd", "1975-03-02", "Northland"),
    ("Orion Trade FZE", "1980-11-14", "Eastoria"),
    ("Pallas Group", "1968-06-30", "Redzone"),
]
PEP_NAMES = ["Marta Kovic", "Idris Bello", "Chen Wei"]
NORMAL_COUNTRIES = ["USA", "UK", "Germany", "India", "Japan", "Canada", "Brazil"]

STRUCTURING_THRESHOLD = 10000  # classic CTR threshold; sub-threshold clustering = structuring

# violation types the eval understands
V_SANCTIONS = "sanctions_hit"
V_STRUCTURING = "structuring"
V_PEP = "pep_counterparty"
V_VELOCITY = "velocity_anomaly"
V_CLEAN = "clean"


def _ts(days_ago_max=60):
    return (datetime.utcnow() - timedelta(
        days=random.randint(0, days_ago_max),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )).isoformat() + "Z"


def make_clean(i):
    txn = {
        "txn_id": f"T-{i:06d}",
        "timestamp": _ts(),
        "amount": round(random.uniform(50, 9000), 2),
        "currency": "USD",
        "originator": fake.company(),
        "beneficiary": fake.company(),
        "beneficiary_country": random.choice(NORMAL_COUNTRIES),
        "vendor_id": f"V-{random.randint(1000, 1999)}",
        "channel": random.choice(["wire", "ach", "card"]),
        "existing_alert_flag": False,
    }
    return txn, {"txn_id": txn["txn_id"], "label": V_CLEAN, "detail": ""}


def make_sanctions(i):
    ent, dob, country = random.choice(SANCTIONED_ENTITIES)
    txn = {
        "txn_id": f"T-{i:06d}",
        "timestamp": _ts(),
        "amount": round(random.uniform(5000, 250000), 2),
        "currency": "USD",
        "originator": fake.company(),
        "beneficiary": ent,
        "beneficiary_country": country,
        "vendor_id": f"V-{random.randint(2000, 2099)}",
        "channel": "wire",
        "existing_alert_flag": True,
    }
    return txn, {"txn_id": txn["txn_id"], "label": V_SANCTIONS,
                 "detail": f"Beneficiary {ent} on watchlist; country {country} sanctioned"}


def make_pep(i):
    txn = {
        "txn_id": f"T-{i:06d}",
        "timestamp": _ts(),
        "amount": round(random.uniform(20000, 400000), 2),
        "currency": "USD",
        "originator": fake.company(),
        "beneficiary": random.choice(PEP_NAMES),
        "beneficiary_country": random.choice(NORMAL_COUNTRIES),
        "vendor_id": f"V-{random.randint(3000, 3099)}",
        "channel": "wire",
        "existing_alert_flag": True,
    }
    return txn, {"txn_id": txn["txn_id"], "label": V_PEP,
                 "detail": "Beneficiary is a Politically Exposed Person"}


def make_structuring(i, group):
    # multiple sub-threshold txns to same beneficiary within a short window
    beneficiary = fake.company()
    vendor = f"V-{random.randint(4000, 4099)}"
    base_ts = datetime.utcnow() - timedelta(days=random.randint(1, 20))
    txns, labels = [], []
    for k in range(random.randint(3, 5)):
        tid = f"T-{i + k:06d}"
        txns.append({
            "txn_id": tid,
            "timestamp": (base_ts + timedelta(hours=k * 3)).isoformat() + "Z",
            "amount": round(random.uniform(8500, 9950), 2),  # just under 10k
            "currency": "USD",
            "originator": fake.company(),
            "beneficiary": beneficiary,
            "beneficiary_country": random.choice(NORMAL_COUNTRIES),
            "vendor_id": vendor,
            "channel": "ach",
            "existing_alert_flag": True,
        })
        labels.append({"txn_id": tid, "label": V_STRUCTURING,
                       "detail": f"Sub-threshold clustering to {beneficiary}"})
    return txns, labels


def make_velocity(i, group):
    # many txns from one originator in a very short window
    originator = fake.company()
    base_ts = datetime.utcnow() - timedelta(days=random.randint(1, 10))
    txns, labels = [], []
    for k in range(random.randint(6, 9)):
        tid = f"T-{i + k:06d}"
        txns.append({
            "txn_id": tid,
            "timestamp": (base_ts + timedelta(minutes=k * 7)).isoformat() + "Z",
            "amount": round(random.uniform(1000, 15000), 2),
            "currency": "USD",
            "originator": originator,
            "beneficiary": fake.company(),
            "beneficiary_country": random.choice(NORMAL_COUNTRIES),
            "vendor_id": f"V-{random.randint(5000, 5099)}",
            "channel": "card",
            "existing_alert_flag": True,
        })
        labels.append({"txn_id": tid, "label": V_VELOCITY,
                       "detail": f"High velocity from {originator}"})
    return txns, labels


def main(n_clean=400):
    transactions, labels = [], []
    i = 0
    # clean bulk
    for _ in range(n_clean):
        t, l = make_clean(i); transactions.append(t); labels.append(l); i += 1
    # planted sanctions hits
    for _ in range(15):
        t, l = make_sanctions(i); transactions.append(t); labels.append(l); i += 1
    # planted PEP
    for _ in range(10):
        t, l = make_pep(i); transactions.append(t); labels.append(l); i += 1
    # planted structuring groups
    for g in range(8):
        ts, ls = make_structuring(i, g); transactions += ts; labels += ls; i += len(ts)
    # planted velocity groups
    for g in range(6):
        ts, ls = make_velocity(i, g); transactions += ts; labels += ls; i += len(ts)

    random.shuffle(transactions)

    with open(OUT / "transactions.jsonl", "w") as f:
        for t in transactions:
            f.write(json.dumps(t) + "\n")
    with open(OUT / "labels.jsonl", "w") as f:
        for l in labels:
            f.write(json.dumps(l) + "\n")

    # regenerate sanctions watchlist CSV if missing
    wl = SANCTIONS / "sample_watchlist.csv"
    if not wl.exists():
        with open(wl, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["entity_name", "dob", "country", "list_type"])
            for name, dob, country in SANCTIONED_ENTITIES:
                w.writerow([name, dob, country, "SDN"])
            for name in PEP_NAMES:
                w.writerow([name, "", "", "PEP"])

    counts = {}
    for l in labels:
        counts[l["label"]] = counts.get(l["label"], 0) + 1
    print(f"Wrote {len(transactions)} transactions to {OUT/'transactions.jsonl'}")
    print(f"Wrote {len(labels)} labels to {OUT/'labels.jsonl'}")
    print("Label distribution:", json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
