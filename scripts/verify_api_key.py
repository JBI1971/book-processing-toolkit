#!/usr/bin/env python3
"""
API Key Verification Script

Verifies that the OpenAI API key is correctly set and working.
This should be run before executing the batch processing pipeline.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.load_env_creds import load_env_credentials, get_openai_api_key, verify_openai_key


def main():
    print("=" * 60)
    print("OpenAI API Key Verification")
    print("=" * 60)
    print()

    try:
        # Step 1: Load credentials from env_creds.yml
        print("Step 1: Loading credentials from env_creds.yml...")
        creds = load_env_credentials(override=True)  # Force override to use file version
        print(f"  ✓ Loaded {len(creds)} credentials")
        print()

        # Step 2: Get OpenAI API key
        print("Step 2: Getting OpenAI API key...")
        api_key = get_openai_api_key()
        print(f"  ✓ Key found: {api_key[:20]}...{api_key[-10:]}")
        print(f"  ✓ Key length: {len(api_key)} characters")
        print()

        # Step 3: Verify API key with test call
        print("Step 3: Verifying API key with test call...")
        if verify_openai_key(api_key):
            print("  ✓ API key verified successfully!")
            print()
            print("=" * 60)
            print("✓ ALL CHECKS PASSED")
            print("=" * 60)
            print()
            print("You can now run the batch processing pipeline.")
            return 0
        else:
            print("  ✗ API key verification failed!")
            print()
            print("=" * 60)
            print("✗ VERIFICATION FAILED")
            print("=" * 60)
            print()
            print("Please check your API key in env_creds.yml")
            return 1

    except Exception as e:
        print(f"  ✗ Error: {e}")
        print()
        print("=" * 60)
        print("✗ VERIFICATION FAILED")
        print("=" * 60)
        print()
        print("Please check:")
        print("  1. env_creds.yml exists in project root")
        print("  2. OPENAI_API_KEY is set in env_creds.yml")
        print("  3. API key is valid and has correct permissions")
        return 1


if __name__ == "__main__":
    sys.exit(main())
