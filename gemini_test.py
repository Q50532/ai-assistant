from google import genai

# Create Gemini client
client = genai.Client()

# Send a question to Gemini
response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents="Explain what Redis is in one sentence."
)

print(response.text)