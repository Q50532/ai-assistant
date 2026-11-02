import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import kb_store
from ai_extensions.core import EvidenceAgent, Evidence, ToolError
from knowledge_feedback import FeedbackStore
from agent import registered_tools, answer_is_supported


class DummyEmbedder:
    def encode(self, query):
        return np.array([1., 0.])


class FakeAPI:
    def __init__(self, role):
        self.role = role
    def get_json(self, path, user, password):
        if path == '/api/me':
            return {'username': user, 'role': self.role}
        if path == '/tickets/16' and user == 'Alice':
            raise ToolError(403, 'Ticket access denied')
        if path == '/tickets/16':
            return {'id': 16, 'title': 'Visible to manager'}
        if path.startswith('/tickets?'):
            return {'data': [{'id': 18, 'title': 'Known service failure'}]}
        raise AssertionError(path)


class FinalTests(unittest.TestCase):
    def test_kb_index_never_returns_private_ticket_snapshots(self):
        texts = ['README public', 'SECRET TICKET RECORD', 'Approved workflow']
        sources = ['README Chunk #1', 'Ticket #16', 'Approved KB #published-1']
        vectors = np.array([[1., 0.], [1., 0.], [0.5, 0.5]])
        with patch.object(kb_store, 'load_index', return_value=(texts,sources,vectors,[0,2])):
            hits = kb_store.search_kb('test', 5, embedder=DummyEmbedder())
        self.assertEqual(len(hits), 2)
        self.assertTrue(all('SECRET' not in x['text'] for x in hits))
        self.assertTrue(all(x['source_type'] == 'KB' for x in hits))

    def test_gemini_bridge_no_password_arg_and_acl(self):
        agent = EvidenceAgent(FakeAPI('USER'), lambda q,k:[{'id':'readme-1','text':'safe', 'source_type':'KB'}])
        evidence, called = [], []
        tools = registered_tools(agent, 'Alice', 'DO_NOT_LOG_THIS', evidence, called)
        self.assertEqual(len(tools), 5)
        denied = tools[1](16)
        self.assertEqual(denied['http_status'], 403)
        self.assertNotIn('DO_NOT_LOG_THIS', json.dumps(denied))
        info = tools[0]('technical help')
        self.assertEqual(info['evidence'][0]['citation'], '[KB:readme-1]')
        self.assertTrue(answer_is_supported('Document [KB:readme-1]', evidence, called))
        self.assertFalse(answer_is_supported('Invented fact [TICKET:16]', evidence, called))

    def test_human_approval_requires_backend_manager(self):
        with tempfile.TemporaryDirectory() as d:
            store=FeedbackStore(Path(d)/'feedback.db', Path(d)/'approved')
            ident=store.propose('Test', 'Suggested fix', 'Ticket 17')
            with self.assertRaises(PermissionError):
                store.approve(ident, 'Alice', 'pwd', FakeAPI('USER'))
            path=store.approve(ident, 'Tom', 'pwd', FakeAPI('MANAGER'))
            self.assertTrue(path.is_file())
            with self.assertRaises(ValueError):
                store.approve(ident, 'Tom', 'pwd', FakeAPI('MANAGER'))


if __name__=='__main__':
    unittest.main()

class TransportSecurityTests(unittest.TestCase):
    def test_rejects_credential_exfiltration_url(self):
        from ai_extensions.core import WorkHubAPI
        for uri in ['http://localhost:1234@evil.com',
                    'http://localhost:8080.evil.com', 'http://localhost:8080/?next=https://evil.com',
                    'https://example.com:443']:
            with self.subTest(uri=uri):
                with self.assertRaises(ValueError):
                    WorkHubAPI(uri)
        self.assertEqual(WorkHubAPI('http://localhost:8080').base_url,
                         'http://localhost:8080')
