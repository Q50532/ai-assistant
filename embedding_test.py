
from sentence_transformers import SentenceTransformer, util
from ingest import document_path, load_document, split_document

# Load embedding model
model = SentenceTransformer(
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# Load and split WorkHub README
text = load_document(document_path)
chunks = split_document(text)

# Generate document embeddings
chunk_vectors = model.encode(chunks)

# User question
question = "How does WorkHub protect user accounts?"
question_vector = model.encode(question)

# Calculate similarity
scores = util.cos_sim(question_vector, chunk_vectors)[0]

# Find the most relevant chunk
best_index = scores.argmax().item()

print("Total chunks:", len(chunks))
print("Question:", question)
print("Similarity:", scores[best_index].item())

print("\nMost relevant chunk:")
print(chunks[best_index])
