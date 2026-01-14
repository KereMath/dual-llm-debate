"""
Test Gemini Pro with proper response extraction
"""

from google import genai
from google.genai import types
from src.config import config

client = genai.Client(api_key=config.GOOGLE_API_KEY)

print("=" * 60)
print("GEMINI PRO TEST")
print(f"Model: {config.GEMINI_MODEL}")
print("=" * 60)

try:
    # Use higher token limit for thinking models
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents="Explain quantum computing in one sentence.",
        config=types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=1000,  # Higher limit for thinking tokens
            system_instruction="You are a helpful assistant. Be concise."
        )
    )

    # Extract text properly
    text = None
    if response.text:
        text = response.text
    elif response.candidates and len(response.candidates) > 0:
        candidate = response.candidates[0]
        if candidate.content and candidate.content.parts:
            text = candidate.content.parts[0].text

    if text:
        print(f"\n[OK] Gemini Pro works!")
        print(f"Response: {text}")
        print("\n" + "=" * 60)
        print("SUCCESS - Gemini Pro is working!")
        print("=" * 60)
    else:
        print(f"\n[ERROR] No text in response")
        print(f"Candidates: {response.candidates}")
        print(f"Prompt feedback: {response.prompt_feedback}")

except Exception as e:
    print(f"\n[ERROR] Gemini Pro failed: {e}")
    import traceback
    traceback.print_exc()
    print("=" * 60)
