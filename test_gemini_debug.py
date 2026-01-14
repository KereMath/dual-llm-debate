"""
Debug test for Gemini API
"""

from google import genai
from google.genai import types
from src.config import config

client = genai.Client(api_key=config.GOOGLE_API_KEY)

print("=" * 60)
print("GEMINI API DEBUG TEST")
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

    print(f"\nResponse object type: {type(response)}")
    print(f"Response attributes: {dir(response)}")

    if hasattr(response, 'text'):
        print(f"\nResponse.text: {response.text}")
    elif hasattr(response, 'candidates'):
        print(f"\nCandidates: {response.candidates}")
        if response.candidates:
            print(f"First candidate: {response.candidates[0]}")
    else:
        print(f"\nFull response: {response}")

    print("\n" + "=" * 60)
    print("DEBUG TEST COMPLETE")
    print("=" * 60)

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    print("=" * 60)
