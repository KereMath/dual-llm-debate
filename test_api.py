"""
Quick API test for Claude and Gemini
"""

from src.api_clients import call_claude_api, call_gemini_api

print("="*60)
print("API CONNECTION TEST")
print("="*60)

# Test Claude
print("\n[1/2] Testing Claude API...")
try:
    response = call_claude_api(
        prompt="Say 'Hello from Claude!' in one sentence.",
        system_prompt="You are a helpful assistant.",
        temperature=0.5,
        max_tokens=50
    )
    print(f"[OK] Claude response: {response[:100]}...")
except Exception as e:
    print(f"[ERROR] Claude failed: {e}")

# Test Gemini
print("\n[2/2] Testing Gemini API...")
try:
    response = call_gemini_api(
        prompt="Say 'Hello from Gemini!' in one sentence.",
        system_prompt="You are a helpful assistant.",
        temperature=0.5,
        max_tokens=8192  # High limit for Gemini 2.5 Pro
    )
    print(f"[OK] Gemini response: {response[:100]}...")
except Exception as e:
    print(f"[ERROR] Gemini failed: {e}")

print("\n" + "="*60)
print("API TEST COMPLETE")
print("="*60)
