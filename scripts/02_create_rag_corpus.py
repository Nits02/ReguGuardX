#!/usr/bin/env python
"""Create a Vertex AI RAG corpus and import the policy markdown files.
Prints the corpus resource name to put into .env as RAG_CORPUS_RESOURCE.

The RAG import expects files in GCS or Drive; this uploads the local policy
docs to a temp GCS bucket, then imports. Adjust bucket name as needed.

Note: new projects in us-central1 often require RagEngineConfig.serverless and
a RagManagedVertexVectorSearch backend (Spanner / RagManagedDb is allowlisted).
"""
import glob
import os
import time
from pathlib import Path

import requests
import vertexai
import google.auth
from google.auth.transport.requests import Request

try:
    from vertexai import rag
except Exception:
    from vertexai.preview import rag

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
BUCKET = os.environ.get("RAG_STAGING_BUCKET") or f"{PROJECT}-reguguard-rag"
BASE = f"https://{LOCATION}-aiplatform.googleapis.com/v1beta1"

vertexai.init(project=PROJECT, location=LOCATION)


def _token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token


def ensure_serverless():
    url = f"{BASE}/projects/{PROJECT}/locations/{LOCATION}/ragEngineConfig"
    headers = {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}
    cfg = requests.get(url, headers=headers, timeout=60)
    print("RagEngineConfig:", cfg.text[:300])
    if "serverless" not in cfg.text:
        print("Switching RagEngineConfig to serverless…")
        patch = requests.patch(
            url, headers=headers,
            json={"ragManagedDbConfig": {"serverless": {}}},
            timeout=120,
        )
        print("Switch response:", patch.text[:400])
        # wait briefly for mode flip
        time.sleep(3)


def ensure_bucket():
    from google.cloud import storage
    sc = storage.Client(project=PROJECT)
    b = sc.bucket(BUCKET)
    if not b.exists():
        b = sc.create_bucket(BUCKET, location=LOCATION)
        print("Created bucket", BUCKET)
    return b


def upload_policies(bucket):
    uris = []
    for p in glob.glob(str(Path(__file__).resolve().parents[1] / "data" / "policies" / "*.md")):
        name = f"policies/{Path(p).name}"
        bucket.blob(name).upload_from_filename(p)
        uris.append(f"gs://{BUCKET}/{name}")
    print("Uploaded:", uris)
    return uris


def _poll(op_name: str, label: str, timeout: int = 600):
    headers = {"Authorization": f"Bearer {_token()}"}
    url = f"{BASE}/{op_name}" if not op_name.startswith("http") else op_name
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = requests.get(url, headers=headers, timeout=60)
        r.raise_for_status()
        d = r.json()
        print(f"[{label}] done={d.get('done')}")
        if d.get("done"):
            if "error" in d:
                raise RuntimeError(d["error"])
            return d.get("response", d)
        time.sleep(5)
    raise TimeoutError(label)


def create_corpus_serverless() -> str:
    """Create corpus via REST with Vector Search 2.0 (serverless-compatible)."""
    headers = {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}
    r = requests.post(
        f"{BASE}/projects/{PROJECT}/locations/{LOCATION}/ragCorpora",
        headers=headers,
        json={
            "displayName": "reguguard-aml-policy",
            "description": "ReguGuard AML / sanctions / FATF policy corpus",
            "vectorDbConfig": {"ragManagedVertexVectorSearch": {}},
        },
        timeout=120,
    )
    r.raise_for_status()
    op = r.json()
    resp = _poll(op["name"], "create_corpus") if not op.get("done") else op.get("response", op)
    name = resp["name"]
    # Normalize to project-id form when possible
    if "/locations/" in name and name.startswith("projects/") and PROJECT not in name:
        # keep as returned; list API accepts both
        pass
    print("Corpus:", name)
    return name


def main():
    ensure_serverless()
    bucket = ensure_bucket()
    upload_policies(bucket)

    corpus_name = None
    # Prefer SDK path when it supports serverless backends; else REST.
    try:
        vector_db = rag.RagManagedVertexVectorSearch()
        corpus = rag.create_corpus(
            display_name="reguguard-aml-policy",
            backend_config=rag.RagVectorDbConfig(vector_db=vector_db),
        )
        corpus_name = corpus.name
        print("Corpus (SDK):", corpus_name)
    except Exception as e:
        print(f"[info] SDK create_corpus unavailable/failed ({e}); using REST serverless create")
        corpus_name = create_corpus_serverless()

    # SDK import works reliably against the corpus resource name
    result = rag.import_files(corpus_name, [f"gs://{BUCKET}/policies/"])
    print("Import:", result)

    print("\n>>> Set this in your .env:")
    print(f'export RAG_CORPUS_RESOURCE="{corpus_name}"')


if __name__ == "__main__":
    main()
