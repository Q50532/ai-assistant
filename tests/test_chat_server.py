"""Offline regression for the new HTTP bridge (no Gemini/network required)."""
import http.client
import json
import os
import threading
import unittest
from unittest.mock import patch

from ai_extensions.core import ToolError
from chat_server import ChatHandler, ThreadingHTTPServer, answer_chat, DelegatedWorkHubAPI


class FakeWorkHub:
    def __init__(self, username='Alice', deny=False):
        self.username = username
        self.deny = deny
        self.calls = []

    def get_json(self, path, username, password):
        self.calls.append(path)
        if path == '/api/me':
            return {'username': self.username, 'role': 'USER'}
        if path == '/tickets/16':
            if self.deny:
                raise ToolError(403, 'Ticket access denied by WorkHub')
            return {'id': 16, 'status': 'OPEN', 'title': 'Allowed'}
        raise AssertionError('unexpected request: ' + path)


class ChatBridgeTests(unittest.TestCase):
    def test_live_tool_uses_user_acl_and_returns_citation(self):
        api = FakeWorkHub()
        def fake_generate(question, tools):
            ticket = tools[1](16)
            self.assertEqual(ticket['ticket']['status'], 'OPEN')
            return 'Ticket is OPEN [TICKET:16]'
        result = answer_chat('Read Ticket 16', 'Alice', api, generate=fake_generate)
        self.assertEqual(result['tools'], ['get_ticket'])
        self.assertEqual(result['citations'], ['[TICKET:16]'])
        self.assertEqual(api.calls, ['/api/me', '/tickets/16'])

    def test_forbidden_ticket_is_never_returned_as_success(self):
        api = FakeWorkHub(deny=True)
        def fake_generate(question, tools):
            self.assertEqual(tools[1](16)['http_status'], 403)
            return 'Here is a ticket summary.'
        with self.assertRaises(ToolError) as error:
            answer_chat('Get ticket 16', 'Alice', api, generate=fake_generate)
        self.assertEqual(error.exception.status, 403)

    def test_identity_mismatch_denied_before_model(self):
        api = FakeWorkHub(username='Tom')
        with self.assertRaises(ToolError) as error:
            answer_chat('ticket 16', 'Alice', api, generate=lambda q, tools: 'unsafe')
        self.assertEqual(error.exception.status, 403)
        self.assertEqual(api.calls, ['/api/me'])

    def test_citation_verification_still_applies(self):
        api = FakeWorkHub()
        def fake_generate(q, tools):
            tools[1](16)
            return 'Not grounded [TICKET:999]'
        with self.assertRaises(ToolError) as error:
            answer_chat('ticket 16', 'Alice', api, generate=fake_generate)
        self.assertEqual(error.exception.status, 502)

    def test_delegated_credentials_are_restricted(self):
        with self.assertRaises(ValueError):
            DelegatedWorkHubAPI('http://attacker.example:8080', session_id='abcdefgh123')
        with self.assertRaises(ValueError):
            DelegatedWorkHubAPI('http://localhost:8080', session_id='hello\r\nunsafe')
        with self.assertRaises(ValueError):
            DelegatedWorkHubAPI('http://localhost:8080', session_id='abcdefgh123',
                                basic_auth='Basic Zm9vOmJhcg==')
        obj = DelegatedWorkHubAPI('http://localhost:8080', session_id='abcdefgh123')
        self.assertEqual(obj.auth_header, ('Cookie', 'JSESSIONID=abcdefgh123'))

    def test_http_valid_request_and_user_session_forwarding(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), ChatHandler)
        runner = threading.Thread(target=server.serve_forever, daemon=True)
        runner.start()
        try:
            with patch.dict(os.environ, {'WORKHUB_AGENT_SHARED_KEY': 'X' * 40}), \
                 patch('chat_server.answer_chat', return_value={
                     'answer': 'Ticket is OPEN [TICKET:16]',
                     'tools': ['get_ticket'], 'citations': ['[TICKET:16]']}) as ask:
                conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                conn.request('POST', '/chat', body=json.dumps({'message':'Ticket #16?', 'username':'Alice'}),
                             headers={'X-Agent-Internal-Key': 'X' * 40,
                                      'X-Workhub-Session': 'abcdefgh123',
                                      'Content-Type': 'application/json'})
                response = conn.getresponse()
                data = json.loads(response.read())
                self.assertEqual(response.status, 200)
                self.assertEqual(data['tools'], ['get_ticket'])
                self.assertEqual(ask.call_args.args[1], 'Alice')
                self.assertEqual(ask.call_args.args[2].auth_header,
                                 ('Cookie', 'JSESSIONID=abcdefgh123'))
                conn.close()
        finally:
            server.shutdown()
            server.server_close()
            runner.join(timeout=3)

    def test_bad_shared_secret_is_rejected_before_agent(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), ChatHandler)
        runner = threading.Thread(target=server.serve_forever, daemon=True)
        runner.start()
        try:
            with patch.dict(os.environ, {'WORKHUB_AGENT_SHARED_KEY': 'X' * 40}):
                conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                conn.request('POST', '/chat', body='{}',
                             headers={'X-Agent-Internal-Key': 'wrong',
                                      'Content-Type': 'application/json'})
                response = conn.getresponse()
                self.assertEqual(response.status, 403)
                self.assertEqual(json.loads(response.read())['error'], 'Service authorization failed')
                conn.close()
        finally:
            server.shutdown()
            server.server_close()
            runner.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
