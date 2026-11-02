"""Create a KB-only index (README and Manager-approved knowledge).

Ticket snapshots must never be included in the shared local index. Agent Ticket
retrieval uses WorkHub API with per-user authorization, not exported JSON.
"""
import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from ingest import document_path, load_document, split_document

ROOT = Path(__file__).resolve().parent
chunks = split_document(load_document(document_path))
texts = list(chunks)
sources = [f'README Chunk #{i + 1}' for i in range(len(chunks))]
for path in sorted((ROOT / 'approved_docs').glob('*.txt')):
    if not path.stem.replace('-', '').replace('_', '').isalnum():
        continue
    content = path.read_text(encoding='utf-8')
    for i, chunk in enumerate(split_document(content)):
        texts.append(chunk)
        sources.append(f'Approved KB #{path.stem}-{i + 1}')
if not texts:
    raise ValueError('No approved knowledge was found')
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
vectors = model.encode(texts)
np.save(ROOT / 'knowledge_vectors.npy', vectors)
(ROOT / 'knowledge_index.json').write_text(
    json.dumps({'texts': texts, 'sources': sources}, ensure_ascii=False, indent=2),
    encoding='utf-8')
print(f'Indexed {len(texts)} approved KB passages (no Ticket snapshots)')
