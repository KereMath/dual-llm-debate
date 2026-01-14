"""
Test Gemini 2.5 Pro with system instruction
"""

from google import genai
from google.genai import types
from src.config import config

client = genai.Client(api_key=config.GOOGLE_API_KEY)

print("=" * 60)
print("GEMINI 2.5 PRO WITH SYSTEM INSTRUCTION")
print("=" * 60)

try:
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents="Explain quantum computing in one sentence.",
        config=types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=8192,
            system_instruction="You are a helpful assistant. Be concise."
        )
    )

    print(f"\nResponse:")
    print(f"  - text: {response.text}")
    print(f"  - finish_reason: {response.candidates[0].finish_reason if response.candidates else 'N/A'}")

    if response.text:
        print(f"\n[OK] Gemini 2.5 Pro works with system instruction!")
        print(f"Answer: {response.text}")
    else:
        print(f"\n[ERROR] No text in response")
        if response.candidates and response.candidates[0].content:
            print(f"Parts: {response.candidates[0].content.parts}")

    if response.usage_metadata:
        print(f"\nToken usage:")
        print(f"  - thoughts: {response.usage_metadata.thoughts_token_count}")
        print(f"  - prompt: {response.usage_metadata.prompt_token_count}")
        print(f"  - output: {response.usage_metadata.candidates_token_count}")
        print(f"  - total: {response.usage_metadata.total_token_count}")

    print("\n" + "=" * 60)

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
