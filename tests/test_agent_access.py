import unittest
from agent_access import allowed_indices


class TestAgentSourceAccess(unittest.TestCase):
    def test_filters_unseen_tickets(self):
        sources = ["README Chunk #1", "Ticket #1", "Ticket #2", "Ticket #3"]
        self.assertEqual(allowed_indices(sources, {1, 3}), [0, 1, 3])

    def test_denies_unknown_source_type(self):
        self.assertEqual(allowed_indices(["Secret File", "Ticket #4", "README Chunk #2"], set()), [2])

    def test_exact_source_match(self):
        self.assertEqual(allowed_indices(["Ticket #1 hidden", "Ticket #01", "README Chunk #3"], {1}), [1, 2])


if __name__ == "__main__":
    unittest.main()
