"""Optional LOCAL export, not used by shared RAG index.

All data is WorkHub-authorized for the logged-in human; still confidential.
Use agent.py for normal retrieval. A shared KB never indexes these exports.
"""
import sys
if __name__ == '__main__' and '--local-export' not in sys.argv:
    raise SystemExit('This command exports private Ticket data; rerun with --local-export to opt in. Never publish exports.')

if __name__ == "__main__":
    import requests
    import json
    from getpass import getpass

    base_url = "http://localhost:8080"

    # Create an HTTP session
    session = requests.Session()

    # Get CSRF token
    csrf_response = session.get(f"{base_url}/csrf")
    csrf_response.raise_for_status()
    csrf = csrf_response.json()

    # Login to WorkHub
    username = input("Username: ")
    password = getpass("Password: ")

    session.post(
        f"{base_url}/login",
        data={
            "username": username,
            "password": password,
            "_csrf": csrf["token"]
        }
    )

    # Verify login
    user_response = session.get(f"{base_url}/api/me")
    user_response.raise_for_status()
    user = user_response.json()

    print("Logged in as:", user["username"])

    # Fetch all tickets
    page = 1
    all_tickets = []

    while True:
        response = session.get(
            f"{base_url}/tickets",
            params={"page": page, "size": 2}
        )

        response.raise_for_status()
        result = response.json()

        all_tickets.extend(result["data"])

        print("Fetched page:", page)

        if page >= result["totalPages"]:
            break

        page += 1

    print("Total fetched:", len(all_tickets))

    for ticket in all_tickets:
        print(ticket["id"], ticket["title"], ticket["status"])

    print("Ticket IDs:", [ticket["id"] for ticket in all_tickets])

    ticket_records = []

    for ticket in all_tickets:
        ticket_id = ticket["id"]

        ticket_response = session.get(
            f"{base_url}/tickets/{ticket_id}"
        )

        comments_response = session.get(
            f"{base_url}/tickets/{ticket_id}/comments"
        )

        logs_response = session.get(
            f"{base_url}/tickets/{ticket_id}/logs"
        )

        ticket_response.raise_for_status()
        comments_response.raise_for_status()
        logs_response.raise_for_status()

        record = {
            "ticket": ticket_response.json(),
            "comments": comments_response.json(),
            "logs": logs_response.json()
        }

        ticket_records.append(record)

        print(
            f"Ticket #{ticket_id}: "
            f"{len(record['comments'])} comments, "
            f"{len(record['logs'])} logs"
        )

    with open("tickets_export.json", "w", encoding="utf-8") as file:
        json.dump(ticket_records, file, ensure_ascii=False, indent=2)

    print("Exported records:", len(ticket_records))