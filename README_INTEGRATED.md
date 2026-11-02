# AI Knowledge Assistant — source-integrated candidate (2026-10-27)

This is **the supplied `ai_assistant_v2_phase1` project**, merged with `ai_extensions` (not a separate add-on). The original Gemini `agent.py` now uses the existing SentenceTransformer RAG embeddings for approved KB documents, plus five read-only, user-authorized WorkHub tools.

## Features

1. **Gemini automatic function calling**: `search_knowledge`, `get_ticket`, `similar_tickets`, `suggest_resolution`, `suggest_priority`.
2. **Permission-aware retrieval**: historical Ticket snapshots are NOT indexed into shared KB; live Ticket details and candidate lists use WorkHub's current authenticated HTTP API as the requesting human. No shared Manager key, no direct SQL, no Ticket writes.
3. **Grounded answers**: documents cite `[KB:readme-1]` etc; Ticket results cite `[TICKET:16]`. A citation allowlist guard suppresses unsupported citation IDs / missing citations after grounded tool calls. It verifies provenance IDs, **not truth of all natural-language statements**.
4. **Suggestion-only Agent**: priority heuristic and KB+similar-Ticket resolution evidence are **DRAFT_ONLY**, never silently update Ticket state.
5. **Audit Trail**: tool, timestamp, actor hash, outcome, latency; no password, raw prompt or private Ticket contents.
6. **Human-reviewed knowledge feedback**: local SQLite pending suggestions; only a WorkHub Manager may approve and publish into `approved_docs/`. Rebuild KB index to make approved documents searchable. AI has no automatic approval capability.
7. **Hardened tool transport**: URL only on localhost/127.0.0.1 explicit port; no URL credentials, no HTTP redirect following, bounded inputs and responses.
8. **Compatibility**: `rag_answer.py` and `search_knowledge.py` now retrieve **KB-only**; legacy `fetch_tickets.py` and `ticket_to_text.py` require an explicit `--local-export` and their output is never indexed by `build_index.py`.

## Run on Windows (beside the `workhub` directory)

```powershell
cd D:\Desktop\Internship\ai-assistant
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
$env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')
$env:WORKHUB_URL = 'http://localhost:8080'
.\.venv\Scripts\python.exe agent.py
```

`GEMINI_API_KEY` must be set to a valid key. Do not paste it into the terminal log or upload it. Keep the WorkHub server running; use the correct WorkHub user credentials when prompted. The default model is `gemini-3.5-flash-lite`, adjustable with `GEMINI_MODEL`.

The merged ZIP contains **the original 19 README passages and corresponding existing embedding vectors**, with all six historical Ticket embeddings and plaintext export snapshots removed. Index is immediately usable for KB search with the original embedding model, assuming its Python package/model are installed or cached. Rebuild after new docs / model changes:

```powershell
$env:WORKHUB_README_PATH = 'D:\Desktop\Internship\workhub\README.md'
.\.venv\Scripts\python.exe build_index.py
```

## Human review workflow

```powershell
.\.venv\Scripts\python.exe knowledge_feedback.py --propose
.\.venv\Scripts\python.exe knowledge_feedback.py --approve <FEEDBACK_ID>
.\.venv\Scripts\python.exe build_index.py
```

The reviewer must log in as a WorkHub MANAGER, verified by WorkHub `/api/me` — role claims from a model are not accepted.

## Test report and limitations

The sandbox passed **13/13 offline Python tests**, `python -m compileall`, and the 19-item KB index/vector consistency check. It has no Google GenAI SDK / SentenceTransformer model download, API key, running WorkHub, or MySQL; therefore **real Gemini model calls, live Ticket authorization and embedding retrieval have not been executed end-to-end**. Run the commands above on your Windows environment for final acceptance. Historical WorkHub Phase 1 tests do not establish the behavior of this candidate.

Safety scope: locally operated demonstrator; credentials are held in process only for tool requests, not persisted. Do not deploy this Basic-auth design over nonlocal HTTP or to untrusted users without a hardened authenticated service gateway, proper session management, and TLS. Similarity search over Ticket list uses lexical overlap on the first 100 visible Tickets; it is **not a global vector database**. An AI conversation UI is not included; `agent.py` is a CLI. Sources are identifiers, not proof the generated reasoning is factually correct.
