"""Safe KB-only access to the existing embeddings.

Never include the offline historical Ticket index in model context. Live Ticket data
must pass WorkHub's authenticated REST API and its row-level authorization.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from functools import lru_cache

ROOT = Path(__file__).resolve().parent
KB_SOURCE = re.compile(r'^README Chunk #(\d+)$')
APPROVED_SOURCE = re.compile(r'^Approved KB #([a-zA-Z0-9_-]+)$')


def source_id(source: str) -> str | None:
    readme = KB_SOURCE.fullmatch(source)
    if readme:
        return f'readme-{readme.group(1)}'
    approved = APPROVED_SOURCE.fullmatch(source)
    if approved:
        return f'approved-{approved.group(1)}'
    return None


@lru_cache(maxsize=1)
def load_index():
    import numpy as np
    with (ROOT / 'knowledge_index.json').open('r', encoding='utf-8') as file:
        index = json.load(file)
    vectors = np.load(ROOT / 'knowledge_vectors.npy', allow_pickle=False)
    texts, sources = index['texts'], index['sources']
    if not (len(texts) == len(sources) == len(vectors)):
        raise ValueError('Knowledge index out of sync: run build_index.py')
    allowed = [i for i, source in enumerate(sources) if source_id(source) is not None]
    return texts, sources, vectors, allowed


def search_kb(query: str, top_k: int = 5, *, embedder=None):
    if not 1 <= len(query.strip()) <= 500:
        raise ValueError('Query must contain between 1 and 500 characters')
    if not 1 <= top_k <= 5:
        raise ValueError('top_k must be 1..5')
    texts, sources, vectors, allowed = load_index()
    if not allowed:
        return []
    if embedder is None:
        from sentence_transformers import SentenceTransformer
        embedder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    import numpy as np
    q = np.asarray(embedder.encode(query)).reshape(-1)
    embeddings = np.asarray(vectors[allowed])
    if len(q) != embeddings.shape[1]:
        raise ValueError('Embedding dimensions changed; rebuild the index')
    denom = np.linalg.norm(embeddings, axis=1) * max(np.linalg.norm(q), 1e-12)
    scores = (embeddings @ q) / np.maximum(denom, 1e-12)
    selected = np.argsort(-scores)[:top_k]
    return [dict(id=source_id(sources[allowed[i]]), text=texts[allowed[i]],
                 source_type='KB', score=round(float(scores[i]), 6))
            for i in selected]
