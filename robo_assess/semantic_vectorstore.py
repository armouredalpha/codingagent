"""
robo_assess.semantic_vectorstore
=================================

Semantic vector store backed by Qdrant + OpenRouter text-embedding-3-small.

Replaces the TF-IDF/shingle VectorStore for originality checking when a
Qdrant URL is configured.  The TF-IDF store remains the default so the
system works fully offline without Qdrant credentials.

Usage
-----
Call ``build_vectorstore(settings)`` to get the appropriate implementation:

    store = build_vectorstore(settings)
    store.add("Q001", "publisher node text", topic="ROS2 basics")
    sim, match_id = store.max_similarity("new question text")
    store.save()

Both implementations share the same public API so callers (OriginalityAgent)
need no branching.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Embedding client (OpenAI-compatible, used by SemanticVectorStore)
# ---------------------------------------------------------------------------

def _embed(texts: list[str], model: str, base_url: str, api_key: str) -> list[list[float]]:
    """Return embeddings for a list of texts using an OpenAI-compat endpoint."""
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key or "none")
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in sorted(resp.data, key=lambda x: x.index)]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


# ---------------------------------------------------------------------------
# SemanticVectorStore
# ---------------------------------------------------------------------------

class SemanticVectorStore:
    """Qdrant-backed semantic similarity store.

    Each entry is stored as a vector in a Qdrant collection.  The ``add()``
    method upserts (same id → replace), and ``max_similarity()`` does an
    approximate nearest-neighbour search.

    On first use the collection is created with the right vector size.  If
    Qdrant is unreachable the operation raises — callers should catch and fall
    back to the TF-IDF store.
    """

    COLLECTION_VERSION = 1  # bump when changing vector dimensions

    def __init__(
        self,
        qdrant_url: str,
        qdrant_api_key: str | None,
        collection: str,
        embedding_model: str,
        embedding_base_url: str,
        embedding_api_key: str | None,
    ) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self._embed_model = embedding_model
        self._embed_base_url = embedding_base_url
        self._embed_api_key = embedding_api_key or ""
        self._collection = collection

        self._client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

        # Create collection if it doesn't exist.  Vector size is determined
        # by doing a single probe embedding so we don't hard-code 1536.
        if not self._client.collection_exists(collection):
            probe = _embed(["probe"], embedding_model, embedding_base_url, self._embed_api_key)
            dim = len(probe[0])
            self._client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    @classmethod
    def from_settings(cls, settings) -> "SemanticVectorStore":
        return cls(
            qdrant_url=settings.qdrant_url,
            qdrant_api_key=getattr(settings, "qdrant_api_key", None),
            collection=getattr(settings, "qdrant_collection", "robo_questions"),
            embedding_model=getattr(settings, "embedding_model", "openai/text-embedding-3-small"),
            embedding_base_url=getattr(settings, "embedding_base_url", "https://openrouter.ai/api/v1"),
            embedding_api_key=getattr(settings, "api_key", None),
        )

    def _point_id(self, qid: str) -> int:
        """Deterministic int id from a string question-id (Qdrant requires int/uuid)."""
        import hashlib
        return int(hashlib.md5(qid.encode()).hexdigest(), 16) % (2 ** 63)

    def add(self, qid: str, text: str, topic: str = "") -> None:
        from qdrant_client.models import PointStruct
        vec = _embed([text], self._embed_model, self._embed_base_url, self._embed_api_key)[0]
        self._client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(
                    id=self._point_id(qid),
                    vector=vec,
                    payload={"qid": qid, "topic": topic},
                )
            ],
        )

    def _query_points(self, vec: list[float], limit: int, topic: str | None = None):
        """Unified search using query_points() (qdrant-client >= 1.10)."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        search_filter = None
        if topic:
            search_filter = Filter(must=[FieldCondition(key="topic", match=MatchValue(value=topic))])
        return self._client.query_points(
            collection_name=self._collection,
            query=vec,
            limit=limit,
            query_filter=search_filter,
            with_payload=True,
        ).points

    def max_similarity(
        self,
        text: str,
        exclude_id: str | None = None,
        topic: str | None = None,
    ) -> tuple[float, str | None]:
        """Return (best_cosine_similarity, matching_qid) from Qdrant ANN search."""
        vec = _embed([text], self._embed_model, self._embed_base_url, self._embed_api_key)[0]
        hits = self._query_points(vec, limit=10, topic=topic)
        for hit in hits:
            qid = hit.payload.get("qid", "")
            if exclude_id and qid == exclude_id:
                continue
            return round(hit.score, 3), qid
        return 0.0, None

    def search(self, query: str, top_k: int = 5, topic: str | None = None) -> list[dict]:
        """Return top-k semantically similar items as {id, text, topic, score}."""
        vec = _embed([query], self._embed_model, self._embed_base_url, self._embed_api_key)[0]
        hits = self._query_points(vec, limit=top_k, topic=topic)
        return [{"id": h.payload.get("qid", ""), "text": "", "topic": h.payload.get("topic", ""), "score": h.score}
                for h in hits]

    def all_items(self) -> list[dict]:
        """Return all stored items (scrolls Qdrant collection)."""
        results, _ = self._client.scroll(
            collection_name=self._collection,
            limit=10000,
            with_payload=True,
        )
        return [{"id": r.payload.get("qid", ""), "text": "", "topic": r.payload.get("topic", "")}
                for r in results]

    def save(self) -> None:
        pass  # Qdrant persists automatically on upsert

    def __len__(self) -> int:
        info = self._client.get_collection(self._collection)
        return info.points_count or 0


# ---------------------------------------------------------------------------
# Factory — returns the right implementation based on settings
# ---------------------------------------------------------------------------

def build_vectorstore(settings):
    """Return SemanticVectorStore if Qdrant is configured, TF-IDF store otherwise."""
    qdrant_url = getattr(settings, "qdrant_url", None)
    if qdrant_url:
        try:
            return SemanticVectorStore.from_settings(settings)
        except Exception as exc:
            import logging
            logging.getLogger("robo_assess.semantic_vectorstore").warning(
                "qdrant_init_failed — falling back to TF-IDF vectorstore: %s", exc
            )

    from .vectorstore import VectorStore
    return VectorStore.from_settings(settings)
