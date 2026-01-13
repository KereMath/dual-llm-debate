"""
Simple test script to verify basic functionality
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src import run_research, setup_logging
from src.config import config

def test_offline_mode():
    """Test V1 (offline) mode with simple question"""

    print("="*60)
    print("TEST: Offline Mode (V1)")
    print("="*60)

    # Setup logging
    setup_logging()

    # Validate API keys
    missing = config.validate_api_keys(mode="offline")
    if missing:
        print(f"❌ Missing API keys: {missing}")
        print("Please configure .env file")
        return False

    try:
        # Simple test question
        final_state = run_research(
            topic="What is machine learning?",
            research_mode="offline",
            max_rounds=1,  # Quick test
            convergence_threshold=0.85  # Lower threshold
        )

        # Check results
        print("\n" + "="*60)
        print("RESULTS:")
        print("="*60)
        print(f"✅ Gemini draft: {len(final_state.gemini_draft)} chars")
        print(f"✅ Claude draft: {len(final_state.claude_draft)} chars")
        print(f"✅ Consensus report: {len(final_state.consensus_report or '')} chars")
        print(f"✅ PDF path: {final_state.pdf_path}")
        print(f"✅ Similarity: {final_state.similarity_score:.1%}")
        print(f"✅ Duration: {final_state.get_duration():.1f}s")

        if final_state.errors:
            print(f"\n⚠️  Errors encountered:")
            for error in final_state.errors:
                print(f"   - {error}")

        print("\n✅ TEST PASSED")
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_offline_mode()
    sys.exit(0 if success else 1)
