"""
Test Gemini 2.5 Pro thinking response structure
"""

from google import genai
from google.genai import types
from src.config import config
import json

client = genai.Client(api_key=config.GOOGLE_API_KEY)

print("=" * 60)
print("GEMINI 2.5 PRO THINKING TEST")
print("=" * 60)

try:
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents="What is 2+2? Be very brief.",
        config=types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=8192  # Maximum available
        )
    )

    print(f"\nFull response structure:")
    print(f"  - text: {response.text}")
    print(f"  - candidates count: {len(response.candidates) if response.candidates else 0}")

    if response.candidates:
        for i, candidate in enumerate(response.candidates):
            print(f"\n  Candidate {i}:")
            print(f"    - finish_reason: {candidate.finish_reason}")
            print(f"    - content.role: {candidate.content.role if candidate.content else None}")
            print(f"    - content.parts: {candidate.content.parts if candidate.content else None}")

            # Try to get parts
            if candidate.content and hasattr(candidate.content, 'parts'):
                if candidate.content.parts:
                    for j, part in enumerate(candidate.content.parts):
                        print(f"    - part {j}: {part}")
                        if hasattr(part, 'text'):
                            print(f"      text: {part.text}")
                        if hasattr(part, 'thought'):
                            print(f"      thought: {part.thought}")

    print(f"\n  - usage_metadata:")
    if response.usage_metadata:
        print(f"    thoughts_token_count: {response.usage_metadata.thoughts_token_count}")
        print(f"    prompt_token_count: {response.usage_metadata.prompt_token_count}")
        print(f"    candidates_token_count: {response.usage_metadata.candidates_token_count}")
        print(f"    total_token_count: {response.usage_metadata.total_token_count}")

    print("\n" + "=" * 60)

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
