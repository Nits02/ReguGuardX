"""
RAG grounding tool (Layer 5). Queries a Vertex AI RAG corpus so the Policy
Assessment agent retrieves rule-cited policy text instead of hallucinating.

Implemented as a plain Python callable (ADK FunctionTool-compatible) because
VertexAiRagRetrieval + MCP toolsets can break automatic function calling on
some ADK / google-genai versions.
"""
from .. import config


def retrieve_aml_policy(query: str) -> dict:
    """Retrieve governing AML/sanctions policy rules and citations for a query.
    Returns matching policy passages with rule IDs when available."""
    if not config.RAG_CORPUS_RESOURCE:
        return {"error": "RAG_CORPUS_RESOURCE not configured", "contexts": []}
    try:
        import vertexai
        try:
            from vertexai import rag
        except Exception:
            from vertexai.preview import rag
        from vertexai.rag.utils.resources import Filter, RagRetrievalConfig

        vertexai.init(project=config.PROJECT, location=config.LOCATION)
        # google-cloud-aiplatform>=1.125 moved top_k into RagRetrievalConfig.
        response = rag.retrieval_query(
            rag_resources=[rag.RagResource(rag_corpus=config.RAG_CORPUS_RESOURCE)],
            text=query,
            rag_retrieval_config=RagRetrievalConfig(
                top_k=5,
                filter=Filter(vector_distance_threshold=0.5),
            ),
        )
        contexts = []
        rag_contexts = getattr(response, "contexts", None)
        items = getattr(rag_contexts, "contexts", None) if rag_contexts is not None else None
        if items is None:
            items = []
        for c in items:
            contexts.append({
                "text": getattr(c, "text", "") or "",
                "source": getattr(c, "source_uri", None) or getattr(c, "source_display_name", None),
                "score": getattr(c, "score", None),
            })
        return {"query": query, "contexts": contexts, "count": len(contexts)}
    except Exception as e:  # pragma: no cover
        return {"error": f"RAG retrieval failed: {e}", "contexts": []}


def policy_rag_tool():
    if not config.RAG_CORPUS_RESOURCE:
        return None
    return retrieve_aml_policy
