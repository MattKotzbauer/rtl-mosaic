"""Embedding-similarity IP router (alternative to keyword router in ip_router.py).

Uses OpenAI text-embedding-3-small. Caches IP embeddings to disk so we only
embed each IP once. Same return shape as ip_router.resolve_subblock.
"""
import os, json, math
from openai import OpenAI

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "mcp", "corpus", "catalog.json")
CACHE_PATH = os.path.join(os.path.dirname(__file__), "_ip_embeddings.json")
EMBED_MODEL = "text-embedding-3-small"
THRESHOLD = 0.30

_client = None
_corpus_embeddings = None  # {ip_id: vec}
_corpus_meta = None        # {ip_id: ip_dict}


def _client_lazy():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def _embed(text):
    resp = _client_lazy().embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


def _embed_batch(texts):
    resp = _client_lazy().embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def _cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _ip_text(ip):
    kw = " ".join(ip.get("keywords", []))
    return f"{ip['name']}. {ip['description']} Keywords: {kw}"


def _load_corpus_embeddings():
    """Embed every catalog IP once, cache to disk."""
    global _corpus_embeddings, _corpus_meta
    if _corpus_embeddings is not None:
        return _corpus_embeddings
    catalog = json.load(open(CATALOG_PATH))
    ips = catalog["ips"]
    _corpus_meta = {ip["id"]: ip for ip in ips}

    if os.path.exists(CACHE_PATH):
        cache = json.load(open(CACHE_PATH))
        if set(cache.keys()) == {ip["id"] for ip in ips}:
            _corpus_embeddings = cache
            return _corpus_embeddings
    # rebuild cache
    print(f"[ip_router_embed] embedding {len(ips)} corpus IPs...")
    texts = [_ip_text(ip) for ip in ips]
    vecs = _embed_batch(texts)
    _corpus_embeddings = {ip["id"]: v for ip, v in zip(ips, vecs)}
    json.dump(_corpus_embeddings, open(CACHE_PATH, "w"))
    return _corpus_embeddings


def resolve_subblock(subblock):
    """Same shape as ip_router.resolve_subblock. Returns dict with kind+id."""
    embeds = _load_corpus_embeddings()
    query = subblock.get("search_query") or subblock.get("name", "")
    if not query.strip():
        return {"kind": "generate"}
    q_vec = _embed(query)
    best_id, best_score = None, -1.0
    for ip_id, ip_vec in embeds.items():
        s = _cosine(q_vec, ip_vec)
        if s > best_score:
            best_score = s
            best_id = ip_id
    if best_score < THRESHOLD:
        return {"kind": "generate", "score": best_score}
    return {"kind": "ip", "id": best_id, "score": best_score}


if __name__ == "__main__":
    # smoke
    import sys
    _load_corpus_embeddings()
    test_queries = ["32-bit adder", "synchronous fifo", "register file", "shift register", "counter"]
    for q in test_queries:
        r = resolve_subblock({"search_query": q})
        print(f"{q!r:30s} -> {r}")
