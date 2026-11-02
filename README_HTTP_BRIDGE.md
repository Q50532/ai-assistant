# AI Assistant HTTP bridge

This release adds `chat_server.py` to the existing read-only Agent; it does not replace `agent.py` or change the knowledge index. Start WorkHub first, then run:

```powershell
$env:WORKHUB_URL = 'http://localhost:8080'
$env:WORKHUB_AGENT_SHARED_KEY = '<same random 32+-character key as Spring Boot>'
$env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')
.\.venv\Scripts\python.exe chat_server.py
```

The HTTP bridge binds **127.0.0.1:8765**, accepts only `POST /chat` with the shared service header and a delegated authenticated WorkHub `JSESSIONID` or Basic header, then calls `/api/me` to confirm the user identity. Each Gemini tool uses that exact session for authorization at WorkHub; the Python bridge does not trust a model-provided user ID or role. Cross-host deployments are deliberately not supported.

The browser never calls Python directly; instead call the secured, CSRF-protected Spring Boot `POST /api/ai/chat` endpoint. Frontend entrypoint: `/ai.html`. For full setup and acceptance checks, see `workhub/AI_CHAT_SETUP.md` in the companion ZIP.

Offline tests: `py -m unittest discover -s tests -v` (requires the packages in `requirements.txt`). Gemini API access, a live WorkHub database, and a local SentenceTransformer model are needed to complete real E2E validation.
