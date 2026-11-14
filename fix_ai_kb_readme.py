"""Refresh stale WorkHub README facts used by the AI RAG index.

Run from the AI project directory with its .venv Python.
Backs up the target README, modifies only three known stale sentences,
then rebuilds the KB index. Does not touch Ticket data or Spring Boot code.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:
    from ingest import document_path, split_document
except ImportError as exc:
    raise SystemExit(f"Place fix_ai_kb_readme.py beside ingest.py: {exc}")

path = Path(document_path).resolve()
if not path.is_file():
    raise SystemExit(f"README not found: {path}")
if not (ROOT / "build_index.py").is_file():
    raise SystemExit(f"build_index.py not found in: {ROOT}")

old = path.read_bytes().decode("utf-8")
updates = [
    (
        "Ticket details are cached in Redis with a 60-second TTL.",
        "Ticket details are cached in Redis with a randomized 50-70-second TTL (TTL jitter); missing tickets have a 15-second negative-cache TTL.",
    ),
    (
        "Cache hits avoid repeated database queries.",
        "Cache hits avoid an additional ticket-detail query inside TicketService, but GET /tickets/{id} still queries MySQL through TicketAccessService.visibleTicket() for row-level authorization.",
    ),
    (
        "Ticket detail cache entries use a 60-second TTL.",
        "Ticket detail cache entries use a randomized 50-70-second TTL, with 15-second negative caching for missing tickets.",
    ),
]

updated = old
changes = []
for before, after in updates:
    if before in updated:
        updated = updated.replace(before, after)
        changes.append(before)

print(f"README: {path}")
if changes:
    old_chunks = len(split_document(old))
    new_chunks = len(split_document(updated))
    if old_chunks != new_chunks:
        raise SystemExit(f"Chunk count changed unexpectedly: {old_chunks} -> {new_chunks}; nothing modified")
    backup = path.with_name(path.name + ".before_kb_fix.bak")
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    path.write_bytes(updated.encode("utf-8"))
    print(f"Updated {len(changes)} outdated statement(s); saved backup: {backup}")
else:
    print("No matching outdated sentences; README may already be updated or differs from the audited version.")
    if "randomized 50-70-second TTL" not in old or "visibleTicket()" not in old:
        raise SystemExit("Source text differs; no changes made. Review README before rebuilding.")

print("Rebuilding embeddings and knowledge index ...")
subprocess.run([sys.executable, str(ROOT / "build_index.py")], cwd=ROOT, check=True)
index = json.loads((ROOT / "knowledge_index.json").read_text(encoding="utf-8"))
indexed_text = "\n".join(index.get("texts", []))
if "Ticket details are cached in Redis with a 60-second TTL." in indexed_text or "Ticket detail cache entries use a 60-second TTL." in indexed_text:
    raise SystemExit("ERROR: old TTL still appears in indexed passages; verify source path.")
print(f"OK: {len(index.get('texts', []))} KB passages indexed; old TTL descriptions removed.")
print("Next: run .\\.venv\\Scripts\\python.exe .\\rag_eval.py")
