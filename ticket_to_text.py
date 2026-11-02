import json


def ticket_to_text(record):
    ticket = record["ticket"]
    comments = record["comments"]
    logs = record["logs"]

    lines = [
        f"Ticket ID: {ticket['id']}",
        f"Title: {ticket['title']}",
        f"Description: {ticket['description']}",
        f"Category: {ticket['category']}",
        f"Priority: {ticket['priority']}",
        f"Status: {ticket['status']}",
        "",
        "Comments:"
    ]

    solution = "None"

    for comment in comments:
        lines.append(
            f"- Comment #{comment['id']}: {comment['content']}"
        )

        if comment["resolution"]:
            solution = comment["content"]

    lines.append("")
    lines.append(f"Marked Resolution: {solution}")
    lines.append(
        f"Ticket Resolution Field: {ticket['resolution'] or 'None'}"
    )

    lines.append("")
    lines.append("Status History:")

    for log in logs:
        lines.append(
            f"- {log['oldStatus']} -> {log['newStatus']}"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if "--local-export" not in sys.argv:
        raise SystemExit("Use --local-export; never put Ticket exports in the shared knowledge index")

    # Load all exported tickets
    with open("tickets_export.json", "r", encoding="utf-8") as file:
        records = json.load(file)

    documents = []

    for record in records:
        document = {
            "ticketId": record["ticket"]["id"],
            "text": ticket_to_text(record)
        }

        documents.append(document)

    # Save documents for RAG
    with open("ticket_documents.json", "w", encoding="utf-8") as file:
        json.dump(documents, file, ensure_ascii=False, indent=2)

    print("Documents created:", len(documents))

    for document in documents:
        print("Ticket:", document["ticketId"])