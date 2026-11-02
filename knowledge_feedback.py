"""Human-reviewed knowledge publishing; AI has no automatic publish privilege.

Drafts are local SQLite records, NOT trusted KB data. A WorkHub Manager must
approve via authenticated /api/me; only then is a UTF-8 KB document published.
Re-run build_index.py to make it searchable. No automatic Ticket write occurs.
"""
from __future__ import annotations
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from ai_extensions.core import WorkHubAPI
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parent


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class FeedbackStore:
    def __init__(self, db_path: str | Path, approved_dir: str | Path):
        self.db_path = Path(db_path)
        self.approved_dir = Path(approved_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.approved_dir.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL,
                source TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING',
                submitted_at TEXT NOT NULL, reviewed_at TEXT,
                reviewer TEXT)''')

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=15)

        try:
            with db:
                yield db
        finally:
            db.close()

    def propose(self, title: str, body: str, source: str) -> str:
        title, body, source = title.strip(), body.strip(), source.strip()
        if not (1 <= len(title) <= 150 and 1 <= len(body) <= 10000
                and 1 <= len(source) <= 250):
            raise ValueError('Invalid feedback length')
        ident = str(uuid.uuid4())
        with self._db() as db:
            db.execute('INSERT INTO feedback (id,title,body,source,submitted_at) VALUES(?,?,?,?,?)',
                       (ident, title, body, source, utc_now()))
        return ident

    def approve(self, ident: str, username: str, password: str, api=None):
        # Credentials are used only to check actual backend MANAGER role.
        api = api or WorkHubAPI()
        me = api.get_json('/api/me', username, password)
        if me.get('role') != 'MANAGER' or me.get('username', '').lower() != username.lower():
            raise PermissionError('Only authenticated WorkHub Managers may approve knowledge')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            entry = db.execute('SELECT title,body,source,status FROM feedback WHERE id=?',
                               (ident,)).fetchone()
            if not entry:
                raise LookupError('Feedback ID not found')
            title, body, source, status = entry
            if status != 'PENDING':
                raise ValueError('Feedback already reviewed')
            # Published file name is a UUID generated on the server, not user path input.
            if not re.fullmatch(r'[0-9a-f-]{36}', ident):
                raise ValueError('Invalid feedback ID')
            doc = self.approved_dir / f'{ident}.txt'
            if doc.exists():
                raise FileExistsError('Approved document already exists')
            # Documentation is source material; never execute instructions from it.
            doc.write_text(f'# {title}\n\nSource: {source}\n\n{body}\n', encoding='utf-8')
            db.execute('UPDATE feedback SET status=?,reviewed_at=?,reviewer=? WHERE id=?',
                       ('APPROVED', utc_now(), username, ident))
        return doc


def main():
    import argparse
    from getpass import getpass
    parser = argparse.ArgumentParser(description='Human-reviewed RAG KB feedback')
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--propose', action='store_true')
    actions.add_argument('--approve', metavar='FEEDBACK_ID')
    args = parser.parse_args()
    store = FeedbackStore(ROOT / 'data' / 'feedback.sqlite3', ROOT / 'approved_docs')
    if args.propose:
        title = input('Title: ')
        source = input('Source Ticket ID / KB citation: ')
        print('Enter proposed knowledge, finish with an empty line:')
        body = '\n'.join(iter(lambda: input(), ''))
        print('PENDING review:', store.propose(title, body, source))
    else:
        username = input('Manager username: ').strip()
        password = getpass('WorkHub password: ')
        path = store.approve(args.approve, username, password)
        print('Approved:', path.name)
        print('Rebuild the KB index with: py build_index.py')


if __name__ == '__main__':
    main()
