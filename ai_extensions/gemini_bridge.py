"""Callable wrappers for an existing Gemini automatic-function-calling agent.

The user's existing agent.py owns the model client and SDK version; this file
only supplies functions and never gives a password to the model context.
"""
from __future__ import annotations
from .core import EvidenceAgent


def bind_read_only_tools(agent: EvidenceAgent, username: str, password: str):
    """Return callable list suitable for model-side function tool registrations.

    Only tool function signatures/docstrings should be exposed to the model.
    Auth credentials are captured in the Python closure and not serialized as tool
    arguments, returned to the model, or written to the audit trail.
    """
    def search_knowledge(query: str) -> dict:
        """Search approved documentation and return grounded knowledge citations."""
        return agent.run_tool('search_knowledge', {'query': query}, username, password)

    def get_ticket(ticket_id: int) -> dict:
        """Read one WorkHub Ticket only if the requesting user can access it."""
        return agent.run_tool('get_ticket', {'ticket_id': ticket_id}, username, password)

    def similar_tickets(query: str) -> dict:
        """Find similar Tickets in the current user's authorized list only."""
        return agent.run_tool('similar_tickets', {'query': query}, username, password)

    def suggest_resolution(query: str) -> dict:
        """Gather authorized evidence for a human-reviewed resolution draft."""
        return agent.run_tool('suggest_resolution', {'query': query}, username, password)

    def suggest_priority(description: str) -> dict:
        """Propose a draft Ticket priority; never change the Ticket automatically."""
        return agent.run_tool('suggest_priority', {'description': description}, username, password)

    return [search_knowledge, get_ticket, similar_tickets, suggest_resolution, suggest_priority]
