"""Read-only cross-tool Ticket triage regression tests; no network/LLM required."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chat_server import answer_chat

from ai_extensions.core import AuditTrail, CitationGate, Evidence, EvidenceAgent, ToolError
from agent import answer_is_supported, registered_tools


class API:
    def __init__(self, deny=False, malformed=False, no_similar=False):
        self.calls = []
        self.deny = deny
        self.malformed = malformed
        self.no_similar = no_similar

    def get_json(self, path, username, password):
        self.calls.append((path, username))
        if path == '/api/me':
            return {'username': username, 'role': 'MANAGER' if username == 'Tom' else 'USER'}
        if path == '/tickets/16':
            if self.deny or username == 'Alice':
                raise ToolError(403, 'Ticket access denied by WorkHub')
            return {'id': 17 if self.malformed else 16,
                    'title': 'Production service unavailable',
                    'description': 'production down: service unavailable',
                    'status': 'OPEN', 'priority': 'HIGH', 'version': 1}
        if path == '/tickets?page=1&size=100':
            rows = [] if self.no_similar else [
                {'id': 16, 'title': 'Production service unavailable'},
                {'id': 19, 'title': 'Production service unavailable incident'},
            ]
            return {'data': rows}
        raise AssertionError('unexpected REST call: ' + path)


def kb(query, top_k):
    return [{'source_type': 'KB', 'id': 'runbook-7',
             'text': 'Check deployment logs and service health.', 'score': 0.88}]


class TriageTests(unittest.TestCase):
    def test_triage_four_steps_evidence_and_read_only(self):
        api = API()
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / 'tool_audit.jsonl'
            agent = EvidenceAgent(api, kb, AuditTrail(log))
            result = agent.run_tool('triage_ticket', {'ticket_id': 16}, 'Tom', 'hidden')
            self.assertEqual(result['status'], 'DRAFT_ONLY')
            self.assertEqual(result['evidence_status'], 'EVIDENCE_READY')
            self.assertEqual(result['suggested_priority'], 'URGENT')
            self.assertTrue(result['human_review_required'])
            self.assertFalse(result['automatic_update'])
            self.assertEqual(result['tool_trace'], ['get_ticket', 'search_knowledge',
                                                    'similar_tickets', 'suggest_priority'])
            citations = [e['citation'] for e in result['evidence']]
            self.assertEqual(citations, ['[TICKET:16]', '[KB:runbook-7]', '[TICKET:19]'])
            self.assertTrue(CitationGate.verify('See [TICKET:16] and [KB:runbook-7]',
                [Evidence(e['source_type'], e['source_id'], e['excerpt']) for e in result['evidence']]))
            self.assertEqual([c[0] for c in api.calls], ['/tickets/16', '/tickets?page=1&size=100'])
            audit = log.read_text()
            self.assertEqual(len(audit.splitlines()), 5)
            self.assertNotIn('hidden', audit)
            self.assertNotIn('production down', audit)
            self.assertNotIn('Tom', audit)

    def test_acl_denial_stops_before_kb_and_other_ticket_queries(self):
        api = API(deny=True)
        def forbidden_search(*args):
            self.fail('KB must not be queried when primary Ticket is denied')
        agent = EvidenceAgent(api, forbidden_search)
        with self.assertRaises(ToolError) as cm:
            agent.run_tool('triage_ticket', {'ticket_id': 16}, 'Alice', 'secret')
        self.assertEqual(cm.exception.status, 403)
        self.assertEqual(api.calls, [('/tickets/16', 'Alice')])

    def test_wrong_ticket_id_is_rejected(self):
        agent = EvidenceAgent(API(malformed=True), kb)
        with self.assertRaises(ToolError) as cm:
            agent.run_tool('triage_ticket', {'ticket_id': 16}, 'Tom', 'secret')
        self.assertEqual(cm.exception.status, 502)

    def test_bad_ticket_id_never_calls_workhub(self):
        api = API()
        agent = EvidenceAgent(api, kb)
        for bad in (0, -3, 'ABC', True, 2_147_483_648):
            with self.subTest(bad=bad), self.assertRaises(ToolError):
                agent.run_tool('triage_ticket', {'ticket_id': bad}, 'Tom', 'secret')
        self.assertEqual(api.calls, [])

    def test_no_knowledge_and_no_similar_reports_insufficient(self):
        agent = EvidenceAgent(API(no_similar=True), lambda q, k: [])
        result = agent.run_tool('triage_ticket', {'ticket_id': 16}, 'Tom', 'secret')
        self.assertEqual(result['evidence_status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual([x['citation'] for x in result['evidence']], ['[TICKET:16]'])
        self.assertFalse(result['automatic_update'])

    def test_sixth_gemini_tool_is_opt_in_and_uses_citation_gate(self):
        agent = EvidenceAgent(API(), kb)
        collected, called = [], []
        self.assertEqual(len(registered_tools(agent, 'Tom', 'secret', [], [])), 5)
        tools = registered_tools(agent, 'Tom', 'secret', collected, called, include_triage=True)
        self.assertEqual(len(tools), 6)
        answer = tools[-1](16)
        self.assertEqual(answer['tool'], 'triage_ticket')
        self.assertEqual(called, ['triage_ticket'])
        self.assertTrue(answer_is_supported('Draft priority [TICKET:16]', collected, called))
        self.assertFalse(answer_is_supported('Wrong citation [TICKET:999]', collected, called))

    def test_chat_bridge_uses_new_workflow_and_preserves_citations(self):
        api = API()
        def generate(question, tools):
            self.assertEqual(len(tools), 6)
            report = tools[-1](16)
            self.assertEqual(report['status'], 'DRAFT_ONLY')
            return 'WorkHub triage: check logs [TICKET:16] [KB:runbook-7]'
        with patch('chat_server.search_kb', kb):
            result = answer_chat('Triage Ticket 16', 'Tom', api, generate=generate)
        self.assertEqual(result['tools'], ['triage_ticket'])
        self.assertEqual(result['citations'], ['[KB:runbook-7]', '[TICKET:16]'])
        self.assertEqual(api.calls[0], ('/api/me', 'Tom'))

    def test_chat_bridge_cannot_hide_403_in_final_answer(self):
        api = API(deny=True)
        def generate(question, tools):
            denied = tools[-1](16)
            self.assertEqual(denied['http_status'], 403)
            return 'Everything is fine [KB:runbook-7]'
        with patch('chat_server.search_kb', kb):
            with self.assertRaises(ToolError) as cm:
                answer_chat('Triage Ticket 16', 'Tom', api, generate=generate)
        self.assertEqual(cm.exception.status, 403)
        self.assertEqual(api.calls, [('/api/me', 'Tom'), ('/tickets/16', 'Tom')])

    def test_gemini_tool_error_returns_no_evidence(self):
        agent = EvidenceAgent(API(deny=True), kb)
        collected, called = [], []
        tools = registered_tools(agent, 'Alice', 'secret', collected, called, include_triage=True)
        denial = tools[-1](16)
        self.assertEqual(denial['http_status'], 403)
        self.assertEqual(denial['evidence'], [])
        self.assertEqual(collected, [])


if __name__ == '__main__':
    unittest.main()
