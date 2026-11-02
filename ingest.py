
from pathlib import Path
import os

# Support the original Internship/java/workhub layout and a two-ZIP sibling layout.
root = Path(__file__).resolve().parent
candidates = [
    root.parent / "java" / "workhub" / "README.md",
    root.parent / "workhub" / "README.md",
]
configured = os.getenv("WORKHUB_README_PATH")
document_path = Path(configured) if configured else next(
    (candidate for candidate in candidates if candidate.is_file()),
    candidates[0],
)


def load_document(path):
    return path.read_text(encoding="utf-8")


def split_document(text):
    chunks = []
    current_lines = []
    parent_title = ""

    for line in text.splitlines():

        if line.startswith("## "):
            if current_lines:
                chunks.append("\n".join(current_lines).strip())

            parent_title = line
            current_lines = [line]

        elif line.startswith("### "):
            current_text = "\n".join(current_lines).strip()

            if current_text and current_text != parent_title:
                chunks.append(current_text)

            current_lines = [parent_title, line]

        else:
            current_lines.append(line)

    if current_lines:
        chunks.append("\n".join(current_lines).strip())

    return chunks


def main():
    if not document_path.is_file():
        print("Document not found:", document_path)
        return

    text = load_document(document_path)
    chunks = split_document(text)

    print("Document:", document_path.name)
    print("Total characters:", len(text))
    print("Total chunks:", len(chunks))

    for i, chunk in enumerate(chunks, start=1):
        headings = [
            line for line in chunk.splitlines()
            if line.startswith("#")
        ]

        title = " > ".join(headings)
        print(f"Chunk {i}: {title} ({len(chunk)} characters)")


if __name__ == "__main__":
    main()
