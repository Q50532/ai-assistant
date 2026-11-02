# AI Knowledge Assistant V2 — first Tool Calling implementation

This source package omits `.venv` and `__pycache__` by design.

## Existing code retained

The original RAG pipeline is still in place: `fetch_tickets.py` → `ticket_to_text.py` → `build_index.py`, and `rag_answer.py`.

## New source

- `agent.py`: session-based interactive Gemini Agent with **read-only** `search_knowledge(query)` and `get_ticket(ticket_id)` tools. Google GenAI Python SDK automatic function calling is used; this call path was **not tested against Gemini** in the current environment.
- `agent_access.py`: ticket-source allowlist. Before each retrieval, query WorkHub's backend-scoped `/tickets` list and restrict historical Ticket documents to IDs the current session is allowed to see. README chunks remain available.
- `tests/test_agent_access.py`: authorization source-filter unit tests.

## Windows PowerShell

```powershell
# From ai-assistant folder; existing .venv can be reused
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "User")
$env:WORKHUB_URL = "http://localhost:8080"
.\.venv\Scripts\python.exe agent.py
```

The **WorkHub backend must be running with the V2 database migration and authorization patch**. The Agent prompts for WorkHub credentials, and its tools reuse that authenticated session. It cannot update Ticket status or priority.

## Security boundary / limitation

Do not upload the local `tickets_export.json`, `ticket_documents.json`, `knowledge_index.json` or vector index publicly: they may include real user-generated content. Tool output is filtered based on the user's current visible IDs, but the underlying offline JSON/NPY files are **not encrypted or physically partitioned per user**. This is a local demonstration mechanism, not production-grade multi-tenant storage isolation.

Unknown source types are denied by default. Every live Ticket API tool request is checked again by the backend. Tools should not return an unauthorized ticket, but an end-to-end multi-user verification is still required.

## Tests conducted in this environment

`python -m compileall -q .` — passed on source. `python -m unittest discover -s tests -v` — 3 tests passed. Gemini and embedding model downloads were not exercised here.

## Not yet delivered

Reviewed Resolution publishing and scheduled/approved knowledge synchronization, explicit structured AI Priority / Resolution endpoints, Agent UI, and end-to-end evaluation metrics.
