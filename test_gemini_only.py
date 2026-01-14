"""
Test only Gemini API (Claude has no credit)
"""

from src.api_clients import call_gemini_api

print("="*60)
print("GEMINI API TEST")
print("="*60)

try:
    response = call_gemini_api(
        prompt="Explain quantum computing in one sentence.",
        system_prompt="You are a helpful assistant. Be concise.",
        temperature=0.5,
        max_tokens=8192  # High limit for Gemini 2.5 Pro thinking tokens
    )
    print(f"\n[OK] Gemini works!")
    print(f"Response: {response}")
    print("\n" + "="*60)
    print("SUCCESS - Gemini API is working!")
    print("="*60)
except Exception as e:
    print(f"\n[ERROR] Gemini failed: {e}")
    print("="*60)
