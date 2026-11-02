"""KB-only command-line retrieval; use agent.py for permission-aware Tickets."""
from kb_store import search_kb

if __name__ == '__main__':
    question = input('Question: ').strip()
    for row in search_kb(question, 3):
        print(f"\nSource: [KB:{row['id']}]\nSimilarity: {row['score']}\n{row['text']}\n" + '-' * 40)
