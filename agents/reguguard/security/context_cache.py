"""
Context caching helper (Layer 5, token optimization).

Creates a Vertex AI CachedContent object holding the dense, static policy corpus
so it is not re-sent on every audit. Returns the cache resource name to attach to
the Policy agent's model. Run once (or on TTL expiry); store the name in env.

Usage (offline):
    python -m agents.reguguard.security.context_cache
"""
import glob
import os
from pathlib import Path
from .. import config


def create_policy_cache(ttl_hours: int = 6) -> str:
    import vertexai
    from vertexai.generative_models import Part
    try:
        from vertexai.caching import CachedContent
    except Exception:
        from vertexai.preview.caching import CachedContent

    vertexai.init(project=config.PROJECT, location=config.LOCATION)
    policy_dir = Path(__file__).resolve().parents[3] / "data" / "policies"
    corpus = "\n\n".join(Path(p).read_text() for p in glob.glob(str(policy_dir / "*.md")))
    system = ("You are an AML compliance policy oracle. Answer strictly from the "
              "policy corpus provided; cite the rule ID (e.g. AML-SAN-03).")
    cache = CachedContent.create(
        model_name=config.WORKER_MODEL,
        system_instruction=system,
        contents=[Part.from_text(corpus)],
        ttl=__import__("datetime").timedelta(hours=ttl_hours),
        display_name="reguguard-policy-cache",
    )
    print("Created cache:", cache.name)
    return cache.name


if __name__ == "__main__":
    create_policy_cache()
