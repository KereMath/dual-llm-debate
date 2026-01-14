"""
List available Gemini models using new google.genai package
"""

from google import genai
from src.config import config

client = genai.Client(api_key=config.GOOGLE_API_KEY)

print("=" * 60)
print("LISTING AVAILABLE GEMINI MODELS (New API)")
print("=" * 60)

try:
    models = client.models.list()

    print("\nModels that support 'generateContent':\n")
    for model in models:
        if hasattr(model, 'supported_generation_methods'):
            if 'generateContent' in model.supported_generation_methods:
                print(f"  - {model.name}")
        else:
            # If no methods listed, show all models
            print(f"  - {model.name}")

except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 60)
