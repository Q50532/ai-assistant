import tempfile
import unittest
from pathlib import Path
from ai_extensions.core import EvidenceAgent, Evidence, CitationGate, AuditTrail, ToolError


class FakeWorkHub:
    def get_json(self, path, username, password):
        if username == 'Alice' and path == '/tickets/16':
            raise ToolError(403, 'Ticket access denied')
        if path == '/tickets/16':
            return {'id':16,'title':'Private BUG','description':'production down', 'status':'OPEN'}
        if path.startswith('/tickets?'):
            return {'data':[{'id':17,'title':'Service unavailable'},
                               {'id':18,'title':'Normal login question'}]}
        raise AssertionError(path)


class Tests(unittest.TestCase):
    def setUp(self):
        self.agent = EvidenceAgent(FakeWorkHub(), lambda q,k:[{'id':'doc-7','text':'Reset service', 'source_type':'KB', 'score':0.9}])

    def test_workhub_is_final_permission_authority(self):
        with self.assertRaises(ToolError) as e:
            self.agent.run_tool('get_ticket', {'ticket_id':16}, 'Alice','secret')
        self.assertEqual(e.exception.status, 403)
        ticket = self.agent.run_tool('get_ticket', {'ticket_id':16}, 'Tom','secret')
        self.assertEqual(ticket['evidence'][0]['citation'], '[TICKET:16]')

    def test_tool_allowlist_and_no_autowrites(self):
        with self.assertRaises(ToolError):
            self.agent.run_tool('delete_ticket', {'ticket_id':16}, 'Tom','secret')
        p = self.agent.suggest_priority('production down')
        self.assertEqual(p['suggested_priority'], 'URGENT')
        self.assertFalse(p['automatic_update'])

    def test_citations_accept_only_known_sources(self):
        ev=[Evidence('KB','doc-7','sample')]
        self.assertTrue(CitationGate.verify('Document says X [KB:doc-7]', ev))
        self.assertFalse(CitationGate.verify('X [KB:invented]', ev))
        self.assertFalse(CitationGate.verify('X', ev))

    def test_audit_excludes_secret(self):
        with tempfile.TemporaryDirectory() as temp:
            log=Path(temp)/'audit.jsonl'
            ag=EvidenceAgent(FakeWorkHub(), lambda q,k:[], AuditTrail(log))
            ag.run_tool('suggest_priority',{'description':'minor'},'Alice','SUPER_SECRET')
            data=log.read_text()
            self.assertNotIn('SUPER_SECRET',data)
            self.assertNotIn('Alice',data)
            self.assertIn('suggest_priority',data)

    def test_joint_index_private_ticket_chunks_are_discarded(self):
        agent = EvidenceAgent(FakeWorkHub(), lambda q,k:[
            {'id':'ticket-16','text':'Private internal details','source_type':'TICKET'},
            {'id':'readme-7','text':'Safe guide','source_type':'KB'}])
        hits=agent.search_knowledge('login')['evidence']
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['citation'], '[KB:readme-7]')

    def test_similar_tickets_uses_authorized_list(self):
        result=self.agent.run_tool('similar_tickets',{'query':'service unavailable'},'Alice','secret')
        self.assertTrue(result['evidence'])
        self.assertTrue(all(row['citation']!='[TICKET:16]' for row in result['evidence']))

if __name__=='__main__': unittest.main()
