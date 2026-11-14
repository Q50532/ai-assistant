"""Read-only WorkHub Ticket triage through authenticated API and approved RAG KB.

Run in the AI project root (WorkHub must be running):
    py -3 ticket_triage.py --ticket 16 --user Tom
No Gemini API key is required to verify this deterministic multi-tool workflow.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path

from ai_extensions.core import AuditTrail, EvidenceAgent, ToolError, WorkHubAPI
from kb_store import search_kb


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ticket', type=int, required=True, help='WorkHub Ticket ID')
    parser.add_argument('--user', required=True, help='WorkHub username')
    parser.add_argument('--base', default=os.getenv('WORKHUB_URL', 'http://localhost:8080'))
    args = parser.parse_args()
    if not 1 <= len(args.user) <= 128:
        parser.error('--user must contain 1..128 characters')
    password = getpass.getpass('WorkHub password: ')
    root = Path(__file__).resolve().parent
    agent = EvidenceAgent(WorkHubAPI(args.base), search_kb,
                          AuditTrail(root / 'logs' / 'tool_audit.jsonl'))
    try:
        report = agent.run_tool('triage_ticket', {'ticket_id': args.ticket},
                                args.user, password)
    except ToolError as exc:
        print(json.dumps({'error': str(exc), 'http_status': exc.status},
                         ensure_ascii=False, indent=2))
        return 1
    except Exception:
        # Do not expose credentials or private backend errors.
        print(json.dumps({'error': 'Triage failed; check WorkHub and KB availability.'}))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
