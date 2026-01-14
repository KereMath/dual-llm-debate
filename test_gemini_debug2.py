"""
Debug test for Gemini API - check candidates
"""

from google import genai
from google.genai import types
from src.config import config

client = genai.Client(api_key=config.GOOGLE_API_KEY)

print("=" * 60)
print("GEMINI API DEBUG TEST - CANDIDATES")
print(f"Model: {config.GEMINI_MODEL}")
print("=" * 60)

try:
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents="Explain quantum computing in one sentence.",
        config=types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=100,
            system_instruction="You are a helpful assistant. Be concise."
        )
    )

    print(f"\nCandidates: {response.candidates}")
    print(f"\nPrompt feedback: {response.prompt_feedback}")
    print(f"\nUsage metadata: {response.usage_metadata}")

    if response.candidates:
        candidate = response.candidates[0]
        print(f"\nCandidate content: {candidate.content}")
        if hasattr(candidate.content, 'parts'):
            print(f"Parts: {candidate.content.parts}")
            if candidate.content.parts:
                print(f"First part text: {candidate.content.parts[0].text}")

    print("\n" + "=" * 60)

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
