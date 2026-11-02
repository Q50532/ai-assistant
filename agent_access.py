"""Source allowlist used before retrieval and before passing context to an LLM.

The existing offline index is a local snapshot, not a multi-tenant data store.
Use this filtering only for local demos; production should enforce ACL at index/storage level.
"""
import re

TICKET_SOURCE = re.compile(r"^Ticket #(\d+)$")
README_SOURCE = re.compile(r"^README Chunk #\d+$")


def allowed_indices(sources, visible_ticket_ids):
    visible = {int(ticket_id) for ticket_id in visible_ticket_ids}
    allowed = []
    for index, source in enumerate(sources):
        if README_SOURCE.fullmatch(source):
            allowed.append(index)
            continue
        match = TICKET_SOURCE.fullmatch(source)
        if match is not None and int(match.group(1)) in visible:
            allowed.append(index)
    return allowed
